"""Independent, evidence-first checks of actual narration or final mixed audio."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WEIGHTS = {'accuracy': 30, 'clarity': 20, 'pace_naturalness': 15,
           'subtitle_sync': 15, 'voice_consistency': 10, 'visual_match': 10}
TERMS = tuple(json.loads((ROOT / 'docs/mechanical-terms.json').read_text())['terms'])


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def run(command, timeout=300):
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)


def silence_intervals(log, duration):
    starts = list(re.finditer(r'silence_start:\s*([\d.]+)', log))
    ends = list(re.finditer(r'silence_end:\s*([\d.]+)', log))
    intervals = []
    for i, start in enumerate(starts):
        boundary = starts[i + 1].start() if i + 1 < len(starts) else len(log)
        end = next((m for m in ends if start.end() < m.start() < boundary), None)
        intervals.append((float(start.group(1)), float(end.group(1)) if end else duration))
    return intervals


def inspect(audio, script, output, use_asr=False, technical_evidence=None):
    audio, script, output = audio.resolve(), script.resolve(), output.resolve()
    shared = None
    execute = run
    if technical_evidence is not None:
        from .technical_evidence import load, evidence_runner
        shared = load(technical_evidence, audio, ('probe', 'audio_decode', 'audio_measure'))
        execute = evidence_runner(shared)
        if shared['identity']['dependencies'].get('script') != digest(script):
            raise ValueError('Technical evidence script mismatch')

    if not audio.is_file() or not script.is_file():
        raise FileNotFoundError('Audio and script must exist')
    output.mkdir(parents=True, exist_ok=False)
    issues = []

    def issue(category, severity, description, start=None, end=None, expected=None, actual=None, evidence=None):
        issues.append({'issue_id': f'A{len(issues) + 1:04}', 'category': category,
                       'severity': severity, 'description': description, 'start': start, 'end': end,
                       'expected_text': expected, 'actual_transcript': actual, 'evidence': evidence,
                       'shot_id': None, 'status': 'open', 'repair_agent': 'Audio Production'})

    probe = execute(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(audio)])
    if probe.returncode:
        data = {'streams': [], 'format': {}}
        issue('probe', 'P0', 'Audio probe failed', evidence='ffprobe')
    else:
        data = json.loads(probe.stdout)
    streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'audio']
    duration = float(data.get('format', {}).get('duration') or 0)
    if not streams:
        issue('audio_stream', 'P0', 'No audio stream', evidence='ffprobe')
    decode = execute(['ffmpeg', '-v', 'error', '-i', str(audio), '-map', '0:a:0', '-f', 'null', '-'])
    if decode.returncode:
        issue('decode', 'P0', 'Full audio decode failed', evidence='ffmpeg')
    scan = execute(['ffmpeg', '-hide_banner', '-nostats', '-i', str(audio), '-map', '0:a:0',
                '-af', 'silencedetect=n=-50dB:d=1,volumedetect', '-f', 'null', '-'])
    log_path = output / 'ffmpeg-audio.log'
    log_path.write_text(scan.stderr)
    silence = silence_intervals(scan.stderr, duration)
    for start, end in silence:
        issue('silence_candidate', 'P2', 'Silence interval requires context review', start, end,
              evidence=str(log_path))
    peak = re.search(r'max_volume:\s*(-?\d+(?:\.\d+)?|-inf)\s*dB', scan.stderr)
    mean = re.search(r'mean_volume:\s*(-?\d+(?:\.\d+)?|-inf)\s*dB', scan.stderr)
    peak_db = float(peak.group(1)) if peak and peak.group(1) != '-inf' else None
    mean_db = float(mean.group(1)) if mean and mean.group(1) != '-inf' else None
    if peak_db is not None and peak_db >= -0.1:
        issue('peak_candidate', 'P2', 'Near full-scale peak; clipping requires waveform inspection',
              evidence=str(log_path))
    if mean_db is not None and mean_db < -35:
        issue('low_volume_candidate', 'P2', 'Low mean level; inspect speech and intended mix',
              evidence=str(log_path))
    if scan.returncode:
        issue('measurement', 'P1', 'Audio analysis failed', evidence=str(log_path))

    asr = {'status': 'not_requested'}
    if use_asr and streams and not decode.returncode:
        mp3 = output / 'asr-input.mp3'
        convert = execute(['ffmpeg', '-v', 'error', '-i', str(audio), '-map', '0:a:0', '-vn',
                       '-c:a', 'libmp3lame', '-b:a', '128k', str(mp3)])
        if convert.returncode:
            asr = {'status': 'conversion_failed'}
        elif not script.read_text().strip():
            asr = {'status': 'empty_script'}
        else:
            result_path = output / 'asr.json'
            try:
                result = execute([sys.executable, str(ROOT / 'scripts/ep02_asr_review.py'),
                              str(mp3), str(script), str(result_path)], timeout=220)
                if result.returncode == 0 and result_path.is_file():
                    asr = json.loads(result_path.read_text())
                    asr['status'] = 'completed'
                    for change in asr['differences']:
                        issue('transcript_difference', 'P1', 'ASR differs from script; confirm by listening',
                              expected=change['expected'], actual=change['actual'], evidence=str(result_path))
                    expected = script.read_text()
                    for term in TERMS:
                        if term in expected and term not in asr['transcript']:
                            issue('terminology_candidate', 'P1', 'Technical term not recognized; confirm by listening',
                                  expected=term, actual=asr['transcript'], evidence=str(result_path))
                else:
                    asr = {'status': 'failed_or_uncertain', 'marker': str(result_path.with_suffix('.submitted')),
                           'error': 'ASR failed; inspect marker before retrying'}
            except subprocess.TimeoutExpired:
                asr = {'status': 'failed_or_uncertain', 'marker': str(result_path.with_suffix('.submitted')),
                       'error': 'ASR timed out; inspect marker before retrying'}

    scores = dict.fromkeys(WEIGHTS)
    status = 'FAIL' if any(i['severity'] == 'P0' for i in issues) else 'NEEDS_REVIEW'
    report = {'source': str(audio), 'audio_sha256': digest(audio), 'script': str(script),
              'script_sha256': digest(script), 'duration': duration, 'streams': streams,
              'checks': {'decode_passed': decode.returncode == 0, 'scan_passed': scan.returncode == 0,
                         'mean_db': mean_db, 'peak_db': peak_db, 'silence_intervals': silence,
                         'forced_alignment': 'unverified', 'speech_naturalness': 'unverified',
                         'subtitle_sync': 'unverified', 'visual_match': 'unverified',
                         'music_masking': 'unverified', 'clipping': 'unverified'},
              'technical_evidence': str(technical_evidence) if technical_evidence else None,
              'technical_origin': shared.get('producer') if shared else 'local QA execution',
              'asr': asr, 'issues': issues, 'scores': scores, 'total': None, 'status': status}
    (output / 'audio-qa-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audio', type=Path)
    parser.add_argument('script', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--asr', action='store_true', help='submit real audio to the configured existing ASR service')
    parser.add_argument('--technical-evidence', type=Path)
    args = parser.parse_args()
    report = inspect(args.audio, args.script, args.output, args.asr, args.technical_evidence)
    print(json.dumps({'status': report['status'], 'issues': len(report['issues']), 'asr': report['asr']['status']}))
    return {'PASS': 0, 'REWORK': 2, 'NEEDS_REVIEW': 3, 'FAIL': 4}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
