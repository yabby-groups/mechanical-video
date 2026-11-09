"""Sample actual video frames for an evidence-limited audience review."""
import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

import requests


WEIGHTS = {'opening': 25, 'interest': 20, 'visual_memorability': 20,
           'knowledge': 15, 'discussion': 15, 'ending': 5}


def gate(dimensions, coverage):
    """Require explicit evidence for all dimensions and all relevant media."""
    if not all(coverage.get(k) is True for k in ('video', 'audio', 'captions', 'continuity')):
        return 'NEEDS_REVIEW', None
    for key in WEIGHTS:
        entry = dimensions.get(key, {})
        score = entry.get('score')
        if (not isinstance(score, (int, float)) or isinstance(score, bool)
                or not math.isfinite(score) or not 0 <= score <= 100
                or not entry.get('evidence') or not entry.get('rationale')):
            return 'NEEDS_REVIEW', None
    total = round(sum(dimensions[k]['score'] * weight for k, weight in WEIGHTS.items()) / 100, 2)
    return ('PASS' if total >= 85 else 'REWORK'), total


def delivery_gate(technical, audience):
    """Require same-version scores AND independent continuous AV evidence."""
    from .perceptual_review import validate
    from .video_qa import gate as video_gate
    if not technical.get('sha256') or technical['sha256'] != audience.get('video_sha256'):
        raise ValueError('Technical and audience reports must describe the same video')
    if technical.get('status') == 'FAIL':
        return 'FAIL'
    if technical.get('status') == 'REWORK':
        return 'REWORK_TECHNICAL'
    if audience.get('status') == 'REWORK':
        return 'REWORK_AUDIENCE'
    for report, failed in ((technical, 'REWORK_TECHNICAL'), (audience, 'REWORK_AUDIENCE')):
        evidence = validate(report.get('perceptual_review'), technical['sha256'],
                            report.get('duration'), report.get('producer_ids', []))
        if evidence['status'] == 'REWORK':
            return failed
        if evidence['status'] != 'COMPLETE':
            return 'NEEDS_REVIEW'
    technical_status, technical_total = video_gate(technical.get('scores', {}), technical.get('issues', []))
    audience_status, audience_total = gate(audience.get('dimensions', {}), audience.get('coverage', {}))
    if technical_status == 'FAIL':
        return 'FAIL'
    if technical_status == 'REWORK':
        return 'REWORK_TECHNICAL'
    if audience_status == 'REWORK':
        return 'REWORK_AUDIENCE'
    if (technical.get('status') != 'PASS' or technical_status != 'PASS' or
            technical.get('total') != technical_total or audience.get('status') != 'PASS' or
            audience_status != 'PASS' or audience.get('total') != audience_total):
        return 'NEEDS_REVIEW'
    return 'PASS'


def digest(path):
    hasher = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def shot_at(shots, stamp):
    for index, shot in enumerate(shots):
        if float(shot.get('start', -1)) <= stamp < float(shot.get('end', -1)):
            return shot.get('shot_id') or f'shot-{index:03d}'
    return None


def sample_times(duration):
    # Opening needs denser coverage; stills cannot establish motion or sound.
    times = [0, 1, 3, 5, 10, 15]
    times.extend(duration * fraction for fraction in (.25, .4, .55, .7, .8, .9))
    return sorted({round(t, 3) for t in times if 0 <= t < duration})


def _run(args):
    return subprocess.run(args, capture_output=True, text=True, check=False)


def inspect(video, output, timeline=None, visual=False):
    video, output = video.resolve(), output.resolve()
    if not video.is_file():
        raise FileNotFoundError(video)
    output.mkdir(parents=True, exist_ok=False)
    probe = _run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(video)])
    if probe.returncode:
        raise ValueError('ffprobe could not read video')
    metadata = json.loads(probe.stdout)
    if not any(s.get('codec_type') == 'video' for s in metadata.get('streams', [])):
        raise ValueError('Video stream is missing')
    duration = float(metadata.get('format', {}).get('duration', 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Video duration is invalid')
    shots = []
    timeline_hash = None
    if timeline is not None:
        timeline = timeline.resolve()
        shots = json.loads(timeline.read_text()).get('shots', [])
        timeline_hash = digest(timeline)
    frames = []
    for i, stamp in enumerate(sample_times(duration)):
        path = output / f'frame-{i:02d}.jpg'
        result = _run(['ffmpeg', '-v', 'error', '-ss', str(stamp), '-i', str(video),
                       '-frames:v', '1', '-vf', 'scale=720:-2', str(path)])
        if result.returncode or not path.is_file():
            raise RuntimeError(f'Frame extraction failed at {stamp} seconds')
        frames.append({'id': i, 'time': stamp, 'shot_id': shot_at(shots, stamp), 'path': str(path)})
    vision = {'status': 'not_requested'}
    issues = []
    if visual:
        endpoint = os.environ.get('VISION_ENDPOINT')
        if not endpoint:
            vision = {'status': 'unavailable'}
        else:
            content = [{'type': 'text', 'text': (
                'These images are ordered sampled frames from one mechanical video. '
                'Describe only what is directly visible, especially the opening and whether the subject is recognizable. '
                'Do not infer sound, motion, audience metrics, unseen frames, or mechanical correctness. '
                'Return JSON with observations and issues. Each issue must contain frame_id, description, '
                'suggestion, priority (P1/P2/P3), and observation (a concrete visible observation). '
                'Use empty issues if evidence is insufficient. Frame IDs and times follow each image.') }]
            for frame in frames:
                content.append({'type': 'text', 'text': f"Frame {frame['id']} at {frame['time']} seconds"})
                content.append({'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' +
                                base64.b64encode(Path(frame['path']).read_bytes()).decode()}})
            try:
                key = os.environ.get('VISION_API_KEY')
                response = requests.post(endpoint, headers={'Authorization': f'Bearer {key}'} if key else {},
                    json={'model': os.environ.get('VISION_MODEL') or 'gpt-6-luna',
                          'messages': [{'role': 'user', 'content': content}]}, timeout=120)
                response.raise_for_status()
                result = response.json()['choices'][0]['message']['content']
                vision = {'status': 'responded', 'model': os.environ.get('VISION_MODEL') or 'gpt-6-luna',
                          'response': result}
                raw = result.strip()
                if raw.startswith('```'):
                    raw = raw.split('\n', 1)[1].rsplit('```', 1)[0]
                try:
                    parsed = json.loads(raw)
                    for item in parsed.get('issues', []):
                        if 'observation' not in item and isinstance(item.get('concrete_visible_observation'), str):
                            item['observation'] = item['concrete_visible_observation']
                        frame_id = item.get('frame_id')
                        if not isinstance(frame_id, int) or isinstance(frame_id, bool) or not 0 <= frame_id < len(frames):
                            continue
                        if not all(isinstance(item.get(k), str) and item[k].strip() for k in ('description', 'suggestion', 'observation')):
                            continue
                        if item.get('priority') not in ('P1', 'P2', 'P3'):
                            continue
                        frame = frames[frame_id]
                        issues.append({'issue_id': f'AUD{len(issues)+1:03}', 'shot_id': frame['shot_id'],
                                       'time': frame['time'], 'evidence': frame['path'],
                                       'observation': item['observation'], 'description': item['description'],
                                       'suggestion': item['suggestion'], 'priority': item['priority'],
                                       'status': 'candidate_needs_review'})
                except (ValueError, TypeError, AttributeError):
                    vision['structured_findings'] = 'invalid_or_missing'
            except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
                vision = {'status': 'failed', 'error': type(exc).__name__}
    dimensions = {name: {'score': None, 'evidence': [], 'rationale': None} for name in WEIGHTS}
    coverage = {'video': False, 'audio': False, 'captions': False, 'continuity': False}
    status, total = gate(dimensions, coverage)
    report = {'video': str(video), 'video_sha256': digest(video), 'duration': duration,
              'timeline': str(timeline) if timeline else None, 'timeline_sha256': timeline_hash,
              'frames': frames, 'vision': vision, 'issues': issues,
              'review_kind': 'sampled_stills_only', 'formal_acceptance': False,
              'blocking_gaps': ['independent full-length AV review', 'timecoded comprehension evidence'],
              'coverage': coverage, 'dimensions': dimensions, 'weights': WEIGHTS,
              'total': total, 'status': status,
              'scope': 'Sampled stills only; no audio, subtitle timing, continuous motion or audience metrics were analyzed.'}
    (output / 'audience-qa-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--timeline', type=Path)
    parser.add_argument('--visual', action='store_true')
    parser.add_argument('--technical-report', type=Path)
    args = parser.parse_args()
    report = inspect(args.video, args.output, args.timeline, args.visual)
    if args.technical_report:
        technical = json.loads(args.technical_report.read_text())
        report['technical_report'] = str(args.technical_report.resolve())
        report['technical_total'] = technical.get('total')
        report['delivery_status'] = delivery_gate(technical, report)
        (args.output / 'audience-qa-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({'status': report['status'], 'issues': len(report['issues']),
                      'visual': report['vision']['status']}, ensure_ascii=False))
    return {'PASS': 0, 'REWORK': 2, 'NEEDS_REVIEW': 3}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
