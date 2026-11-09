"""Evidence-first video checks. Unverified dimensions never pass the gate."""
import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time

import requests

WEIGHTS = {'mechanical': 25, 'visual': 20, 'continuity': 15, 'audio': 15, 'content': 15, 'technical': 10}
MINIMUM = {'mechanical': 80, 'visual': 75, 'continuity': 80, 'audio': 75, 'technical': 90}
PROFILES = ('formal', 'local-silent', 'local-av')


def run(command):
    return subprocess.run(command, capture_output=True, text=True, check=False)


def gate(scores, issues):
    if any(i['severity'] == 'P0' for i in issues):
        return 'FAIL', None
    if any(not isinstance(scores.get(k), (int, float)) or isinstance(scores.get(k), bool)
           or not math.isfinite(scores[k]) or not 0 <= scores[k] <= 100 for k in WEIGHTS):
        return ('REWORK' if any(i['severity'] == 'P1' for i in issues) else 'NEEDS_REVIEW'), None
    total = sum(scores[k] * v for k, v in WEIGHTS.items()) / 100
    if any(i['severity'] == 'P1' for i in issues) or any(scores[k] < v for k, v in MINIMUM.items()) or total < 90:
        return 'REWORK', round(total, 2)
    return 'PASS', round(total, 2)


def audio_score(report, source_hash):
    from .audio_qa import WEIGHTS as AUDIO_WEIGHTS
    if report.get('audio_sha256') != source_hash:
        raise ValueError('Audio QA report must inspect this exact final video')
    scores = report.get('scores', {})
    if report.get('status') != 'PASS' or any(i.get('severity') in ('P0', 'P1') for i in report.get('issues', [])):
        return None
    if any(not isinstance(scores.get(k), (int, float)) or isinstance(scores[k], bool) or not 0 <= scores[k] <= 100 for k in AUDIO_WEIGHTS):
        return None
    calculated = round(sum(scores[k] * weight for k, weight in AUDIO_WEIGHTS.items()) / 100, 2)
    return calculated if report.get('total') == calculated else None


def inspect(video, output, visual=False, audio_report=None, technical_evidence=None, profile='formal'):
    if profile not in PROFILES:
        raise ValueError('Unknown video QA profile')
    video = video.resolve()
    shared = None
    execute = run
    if technical_evidence is not None:
        from .technical_evidence import load, evidence_runner
        shared = load(technical_evidence, video, ('probe', 'decode', 'video_scan', 'frames'), partial=True)
        execute = evidence_runner(shared)

    output.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256(video.read_bytes()).hexdigest()
    probe = execute(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video)])
    issues = []
    def issue(category, severity, start, end, description, evidence=None):
        issues.append({'issue_id': f'I{len(issues)+1:04}', 'shot_id': None, 'start': start, 'end': end,
                       'category': category, 'severity': severity, 'description': description,
                       'evidence': evidence, 'reference': 'ffmpeg/ffprobe', 'confidence': 1.0,
                       'repair_agent': 'Editor', 'status': 'open'})
    if probe.returncode:
        issue('probe', 'P0', 0, 0, 'ffprobe failed')
        data = {'streams': [], 'format': {}}
    else:
        data = json.loads(probe.stdout)
    streams = data.get('streams', [])
    v = next((s for s in streams if s.get('codec_type') == 'video'), {})
    a = next((s for s in streams if s.get('codec_type') == 'audio'), {})
    duration = float(data.get('format', {}).get('duration', 0))
    if not v:
        issue('streams', 'P0', 0, duration, 'Missing video stream')
    if not a and profile != 'local-silent':
        issue('streams', 'P0', 0, duration, 'Missing required audio stream')
    # Duration is content-led (user instruction 2026-11-09), not a padding target.
    if not math.isfinite(duration) or duration <= 0:
        issue('duration', 'P0', 0, 0, 'Missing or invalid media duration')
    if any(actual < required for actual, required in zip(sorted([v.get('width', 0), v.get('height', 0)]), [1080, 1920])):
        issue('resolution', 'P1', 0, duration, 'Resolution below 1080p')
    if v.get('codec_name') != 'h264' or (a and a.get('codec_name') != 'aac'):
        issue('codec', 'P1', 0, duration, 'Expected H.264 and AAC')
    decode = execute(['ffmpeg', '-v', 'error', '-i', str(video), '-f', 'null', '-'])
    if decode.returncode:
        issue('decode', 'P0', 0, duration, 'Full decode failed')
    # Long intervals are candidates: intended pauses and fades still require review.
    scan_command = ['ffmpeg', '-hide_banner', '-i', str(video), '-vf', 'blackdetect=d=1:pix_th=0.05,freezedetect=n=-60dB:d=2']
    if a:
        scan_command += ['-af', 'silencedetect=n=-50dB:d=2']
    scan = execute(scan_command + ['-f', 'null', '-'])
    if scan.returncode:
        issue('scan', 'P1', 0, duration, 'Technical scan failed')
    (output / 'technical.log').write_text(scan.stderr)
    patterns = [('black', r'black_start:([\d.]+) black_end:([\d.]+)'),
                ('freeze', r'freeze_start: ([\d.]+).*?freeze_end: ([\d.]+)'),
                ('silence', r'silence_start: ([\d.]+).*?silence_end: ([\d.]+)')]
    for category, pattern in patterns:
        for match in re.finditer(pattern, scan.stderr, re.S):
            start, end = map(float, match.groups())
            issue(category, 'P2', start, end, 'Candidate interval; intent requires review')
    frames = []
    if shared is not None and 'frames' in shared['_validated_checks']:
        frames = shared['checks']['frames']['result']['frames']
        from .technical_evidence import digest as frame_digest
        if any(not Path(f['path']).is_file() or frame_digest(f['path']) != f['sha256'] for f in frames):
            raise ValueError('Missing or stale evidence frames')
        shared.setdefault('_reused_checks', []).append('frames')
    else:
        try:
            num, den = map(float, v.get('r_frame_rate', '0/1').split('/'))
            last_frame = max(0, float(v.get('duration', duration)) - den / num) if num > 0 and den > 0 else duration
        except (ValueError, TypeError, ZeroDivisionError):
            last_frame = duration
        for index, stamp in enumerate([min(duration * x, last_frame) for x in (0.05, 0.25, 0.5, 0.75, 0.95)] if duration else []):
            path = output / f'frame-{index:02}.jpg'
            result = execute(['ffmpeg', '-v', 'error', '-ss', str(stamp), '-i', str(video), '-frames:v', '1', str(path)])
            if result.returncode == 0 and path.exists():
                frames.append({'time': stamp, 'path': str(path)})
            else:
                issue('frames', 'P1', stamp, stamp, 'Requested sample frame extraction failed')
    vision = {'status': 'not_run'}
    if visual:
        endpoint = os.environ.get('VISION_ENDPOINT')
        if not endpoint or not frames:
            vision = {'status': 'unavailable'}
        else:
            content = [{'type': 'text', 'text': 'Describe only visible evidence in these sampled frames of a mechanical animation. Note uncertainty. Do not infer unseen motion or mechanical correctness.'}]
            for frame in frames:
                content.append({'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + base64.b64encode(Path(frame['path']).read_bytes()).decode()}})
            try:
                key = os.environ.get('VISION_API_KEY')
                response = requests.post(endpoint, headers={'Authorization': f'Bearer {key}'} if key else {}, json={'model': os.environ.get('VISION_MODEL') or 'gpt-6-luna', 'messages': [{'role': 'user', 'content': content}]}, timeout=120)
                response.raise_for_status()
                vision = {'status': 'responded', 'model': os.environ.get('VISION_MODEL') or 'gpt-6-luna', 'response': response.json()['choices'][0]['message']['content']}
            except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
                vision = {'status': 'failed', 'error': type(exc).__name__}
    scores = dict.fromkeys(WEIGHTS)
    audio_evidence = None
    if audio_report is not None:
        audio_evidence = json.loads(audio_report.read_text())
        scores['audio'] = audio_score(audio_evidence, digest)
        for finding in audio_evidence.get('issues', []):
            if finding.get('severity') in ('P0', 'P1'):
                issues.append(finding)
    # Technical is only scored when all required technical dimensions are measured.
    status, total = gate(scores, issues)
    report = {'video': str(video), 'sha256': digest, 'duration': duration, 'streams': streams,
              'profile': profile, 'formal_acceptance': False,
              'review_kind': 'technical_scan_and_sampled_stills',
              'blocking_gaps': ['independent continuous motion review', 'actual listening', 'timecoded comprehension evidence'],
              'scope': 'formal review' if profile == 'formal' else 'local proof only; not episode acceptance',
              'technical_reused_checks': shared.get('_reused_checks', []) if shared else [],
              'technical_cache_mismatches': shared.get('_mismatches', []) if shared else [],
              'technical_evidence': str(technical_evidence) if technical_evidence else None,
              'technical_origin': shared.get('producer') if shared else 'local QA execution',
              'decode_passed': decode.returncode == 0, 'scan_passed': scan.returncode == 0,
              'frames': frames, 'vision': vision, 'issues': issues, 'scores': scores,
              'audio_qa_report': str(audio_report) if audio_report else None,
              'total': total, 'status': status, 'created': time.time()}
    (output / 'qa-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('video', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--visual', action='store_true')
    p.add_argument('--audio-report', type=Path, help='Audio QA report for this exact video file')
    p.add_argument('--technical-evidence', type=Path)
    p.add_argument('--profile', choices=PROFILES, default='formal')
    args = p.parse_args()
    report = inspect(args.video, args.output, args.visual, args.audio_report, args.technical_evidence, args.profile)
    print(json.dumps({'status': report['status'], 'issues': len(report['issues']), 'vision': report['vision']['status']}, ensure_ascii=False))
    return {'PASS': 0, 'REWORK': 2, 'NEEDS_REVIEW': 3, 'FAIL': 4}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
