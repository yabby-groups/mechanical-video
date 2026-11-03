"""Content-addressed deterministic evidence; never supplies perceptual scores."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

SCHEMA = 1
# Updating this source invalidates all results, including parsing changes.


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def run(command):
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return {'command': command, 'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}


def versions():
    return {tool: run([tool, '-version'])['stdout'].splitlines()[0] for tool in ('ffprobe', 'ffmpeg')}


def identity(media, dependencies, parameters):
    return {'media_sha256': digest(media), 'dependencies': {name: digest(path) for name, path in sorted(dependencies.items())},
            'tools': versions(), 'implementation': digest(__file__), 'parameters': parameters}


def valid_entry(entry, key):
    return (isinstance(entry, dict) and entry.get('key') == key and entry.get('status') == 'PASS'
            and isinstance(entry.get('result'), dict) and entry['result'].get('returncode') == 0
            and entry.get('result_sha256') == canonical(entry.get('result')))


def collect(media, output, dependencies=None, parameters=None, producer='producer'):
    media, output = Path(media).resolve(), Path(output).resolve()
    dependencies = {k: Path(v).resolve() for k, v in (dependencies or {}).items()}
    parameters = parameters or {}
    fractions = parameters.get('frame_fractions', [0.05, 0.25, 0.5, 0.75, 0.95])
    if not isinstance(fractions, list) or not fractions or any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or not 0 <= v < 1 for v in fractions):
        raise ValueError('Invalid frame fractions')
    ident = identity(media, dependencies, parameters)
    output.mkdir(parents=True, exist_ok=True)
    manifest = output / 'technical-evidence.json'
    try:
        old = json.loads(manifest.read_text())
    except (OSError, ValueError):
        old = {}
    if not isinstance(old, dict) or not isinstance(old.get('checks', {}), dict):
        old = {}
    checks, reused = {}, []
    # Per-item keys keep subtitle/script changes from invalidating full decode.
    def check(name, command=None, compute=None, deps=(), params=()):
        spec = {k: ident[k] for k in ('media_sha256', 'tools', 'implementation')}
        spec['dependencies'] = {k: ident['dependencies'].get(k) for k in deps}
        spec['parameters'] = {k: parameters.get(k) for k in params}
        spec['name'] = name
        key = canonical(spec)
        cached = old.get('checks', {}).get(name)
        if valid_entry(cached, key):
            checks[name] = cached
            reused.append(name)
            return cached['result']
        result = run(command) if command else compute()
        passed = result.get('returncode') == 0
        checks[name] = {'key': key, 'spec': spec, 'status': 'PASS' if passed else 'FAIL',
                        'result': result, 'result_sha256': canonical(result),
                        'coverage': 'entire media' if name not in ('frames', 'subtitles', 'timeline') else name}
        return result
    probe = check('probe', ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(media)])
    check('decode', ['ffmpeg', '-v', 'error', '-i', str(media), '-f', 'null', '-'])
    check('audio_decode', ['ffmpeg', '-v', 'error', '-i', str(media), '-map', '0:a:0', '-f', 'null', '-'])
    check('audio_measure', ['ffmpeg', '-hide_banner', '-nostats', '-i', str(media), '-map', '0:a:0', '-af', 'silencedetect=n=-50dB:d=1,volumedetect', '-f', 'null', '-'])
    check('video_scan', ['ffmpeg', '-hide_banner', '-i', str(media), '-vf', 'blackdetect=d=1:pix_th=0.05,freezedetect=n=-60dB:d=2', '-af', 'silencedetect=n=-50dB:d=2', '-f', 'null', '-'])
    probe_data = {}
    try:
        probe_data = json.loads(probe['stdout'])
        duration = float(probe_data['format']['duration'])
    except (ValueError, KeyError):
        duration = 0
    def frames():
        if duration <= 0 or not any(v.get('codec_type') == 'video' for v in probe_data.get('streams', [])):
            return {'returncode': 1, 'reason': 'missing usable video duration/stream'}
        listing = []
        for i, fraction in enumerate(parameters.get('frame_fractions', [0.05, 0.25, 0.5, 0.75, 0.95])):
            path = output / f'frame-{i:02}.jpg'
            stream = next((v for v in probe_data['streams'] if v.get('codec_type') == 'video'), {})
            num, den = map(float, stream.get('r_frame_rate', '1/1').split('/'))
            last = max(0, float(stream.get('duration', duration)) - den / num) if num else 0
            stamp = min(duration * fraction, last)
            result = run(['ffmpeg', '-y', '-v', 'error', '-ss', str(stamp), '-i', str(media), '-frames:v', '1', str(path)])
            if result['returncode'] or not path.is_file():
                return dict(result, returncode=1)
            listing.append({'time': stamp, 'path': str(path), 'sha256': digest(path), 'command': result['command']})
        contact = output / 'contact-sheet.jpg'
        command = ['ffmpeg', '-y', '-v', 'error', '-i', str(media), '-vf',
                   f'fps=5/{duration},scale=320:-1,tile=5x1', '-frames:v', '1', str(contact)]
        result = run(command)
        if result['returncode'] or not contact.is_file():
            return dict(result, returncode=1)
        return {'returncode': 0, 'frames': listing, 'contact_sheet':
                {'path': str(contact), 'sha256': digest(contact), 'command': command}}
    # Artifacts must still exist, not merely have a surviving manifest entry.
    f = old.get('checks', {}).get('frames', {})
    if not isinstance(f, dict) or not isinstance(f.get('result', {}), dict):
        f = {}
        old.get('checks', {}).pop('frames', None)
    artifacts = f.get('result', {}).get('frames', []) + ([f['result']['contact_sheet']] if f.get('result', {}).get('contact_sheet') else [])
    if any(not isinstance(x, dict) or not isinstance(x.get('path'), str) or not Path(x['path']).is_file() or digest(x['path']) != x.get('sha256') for x in artifacts):
        old.get('checks', {}).pop('frames', None)
    check('frames', compute=frames, params=('frame_fractions',))
    if 'subtitles' in dependencies:
        def subtitles():
            rows = json.loads(dependencies['subtitles'].read_text())
            failures, end = [], 0
            for i, row in enumerate(rows):
                text, start, stop = row['text'], row['start'], row['end']
                if '\n' in text or '\r' in text or len(text) > 20 or not text or not 0 <= end <= start < stop <= duration:
                    failures.append(i)
                end = stop
            return {'returncode': 1 if failures else 0, 'invalid_rows': failures, 'count': len(rows)}
        check('subtitles', compute=subtitles, deps=('subtitles',), params=('subtitle_policy',))
    if 'timeline' in dependencies:
        def timeline():
            data = json.loads(dependencies['timeline'].read_text())
            valid = data.get('media_sha256') == ident['media_sha256'] and data.get('dependencies') == {k: v for k, v in ident['dependencies'].items() if k != 'timeline'}
            return {'returncode': 0 if valid else 1, 'association_only': True}
        check('timeline', compute=timeline, deps=tuple(dependencies))
    report = {'schema_version': SCHEMA, 'identity': ident, 'dependency_paths': {k: str(v) for k, v in dependencies.items()}, 'producer': producer,
              'origin': 'production technical measurements; independent QA must verify provenance and inspect actual media',
              'checks': checks, 'reused': reused, 'perceptual_scores': None}
    manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def load(path, media, required, dependencies=None, parameters=None, partial=False):
    """Reject stale, incomplete, failed or corrupt evidence, never silently accept it."""
    report = json.loads(Path(path).read_text())
    if not isinstance(report, dict) or not isinstance(report.get('checks'), dict):
        raise ValueError('Corrupt technical manifest')
    dependencies = dependencies if dependencies is not None else report.get('dependency_paths', {})
    parameters = parameters if parameters is not None else report.get('identity', {}).get('parameters', {})
    # Missing unrelated dependencies must not discard valid media-only decode evidence.
    ident = identity(Path(media), {}, parameters)
    for name, dependency in dependencies.items():
        try:
            ident['dependencies'][name] = digest(dependency)
        except OSError as exc:
            if partial:
                ident['dependencies'][name] = None
            else:
                raise ValueError('Technical evidence identity mismatch: identity.dependencies.' + name) from exc
    stored = report.get('identity', {})
    if not isinstance(stored, dict):
        raise ValueError('Corrupt technical identity')
    mismatches = [f'identity.{key}' for key in ident if stored.get(key) != ident[key]]
    global_valid = report.get('schema_version') == SCHEMA and bool(report.get('producer'))
    if not global_valid:
        mismatches.append('schema_version/producer')
    if not partial and mismatches:
        raise ValueError('Technical evidence identity mismatch: ' + ', '.join(mismatches))
    validated = []
    for name in required:
        entry = report.get('checks', {}).get(name, {})
        if not isinstance(entry, dict) or not isinstance(entry.get('spec'), dict):
            if partial:
                mismatches.append('checks.' + name + '.entry')
                continue
            raise ValueError('Corrupt technical entry: ' + name)
        spec = entry['spec']
        expected = {k: ident[k] for k in ('media_sha256', 'tools', 'implementation')}
        expected.update(name=name, dependencies={k: ident['dependencies'].get(k) for k in spec.get('dependencies', {})},
                        parameters={k: ident['parameters'].get(k) for k in spec.get('parameters', {})})
        valid = global_valid and spec == expected and valid_entry(entry, canonical(expected))
        if spec != expected:
            mismatches.extend('checks.' + name + '.spec.' + key for key in expected if spec.get(key) != expected[key])
        if valid and name == 'frames':
            result = entry['result']
            artifacts = result.get('frames', []) + ([result['contact_sheet']] if result.get('contact_sheet') else [])
            try:
                valid = bool(result.get('frames') and result.get('contact_sheet')) and all(
                    Path(a['path']).is_file() and digest(a['path']) == a['sha256'] for a in artifacts)
            except (OSError, KeyError, TypeError):
                valid = False
        if valid:
            validated.append(name)
        elif partial:
            mismatches.append('checks.' + name + '.spec/result/artifacts')
        else:
            raise ValueError('Invalid technical evidence: ' + name)
    report['_validated_checks'] = validated
    report['_mismatches'] = mismatches
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('media', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--subtitles', type=Path, help='JSON list of {start,end,text}')
    parser.add_argument('--script', type=Path)
    parser.add_argument('--timeline', type=Path)
    parser.add_argument('--producer', required=True)
    args = parser.parse_args(argv)
    try:
        report = collect(args.media, args.output, {k: getattr(args, k) for k in ('subtitles', 'script', 'timeline') if getattr(args, k)}, producer=args.producer)
    except (OSError, ValueError, KeyError, TypeError):
        print('Invalid technical evidence inputs', file=sys.stderr)
        return 2
    print(json.dumps({'manifest': str(args.output / 'technical-evidence.json'), 'reused': report['reused']}))
    return 0 if all(c['status'] == 'PASS' for c in report['checks'].values()) else 1


def evidence_runner(report):
    """Only exact commands reuse validated results; all other commands still execute."""
    def execute(command, **kwargs):
        for name in report['_validated_checks']:
            entry = report['checks'][name]
            result = entry['result']
            if entry['status'] == 'PASS' and result.get('command') == command:
                report.setdefault('_reused_checks', []).append(name)
                return subprocess.CompletedProcess(command, result['returncode'], result['stdout'], result['stderr'])
        return subprocess.run(command, capture_output=True, text=True, check=False, **kwargs)
    return execute


if __name__ == '__main__':
    raise SystemExit(main())
