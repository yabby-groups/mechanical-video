"""Evidence-limited audio appeal review; no emotion is inferred from text."""
import argparse
import json
import math
from pathlib import Path

from .audio_qa import digest, run, silence_intervals

WEIGHTS = {'opening': 20, 'emotion': 25, 'pace': 20, 'audiovisual': 15,
           'naturalness': 15, 'ending': 5}


def appeal_gate(dimensions):
    for key in WEIGHTS:
        item = dimensions.get(key, {})
        value = item.get('score')
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not 0 <= value <= 100
                or not item.get('evidence') or not item.get('rationale')):
            return 'NEEDS_REVIEW', None
    total = round(sum(dimensions[k]['score'] * weight for k, weight in WEIGHTS.items()) / 100, 2)
    return ('PASS' if total >= 85 else 'REWORK'), total


def delivery_gate(technical, appeal):
    if not technical.get('audio_sha256') or technical['audio_sha256'] != appeal.get('audio_sha256'):
        raise ValueError('Audio reports must refer to the same actual asset')
    if technical.get('status') == 'FAIL':
        return 'FAIL'
    if technical.get('status') == 'REWORK':
        return 'REWORK_TECHNICAL'
    if technical.get('status') != 'PASS' or technical.get('total') is None or technical['total'] < 90:
        return 'NEEDS_REVIEW'
    if appeal.get('status') == 'REWORK':
        return 'REWORK_APPEAL'
    if appeal.get('status') != 'PASS' or appeal.get('total') is None or appeal['total'] < 85:
        return 'NEEDS_REVIEW'
    return 'PASS'


def inspect(audio, output, timeline=None, technical_report=None):
    audio, output = audio.resolve(), output.resolve()
    if not audio.is_file():
        raise FileNotFoundError(audio)
    output.mkdir(parents=True, exist_ok=False)
    probe = run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(audio)])
    if probe.returncode:
        raise ValueError('ffprobe failed')
    meta = json.loads(probe.stdout)
    duration = float(meta.get('format', {}).get('duration') or 0)
    if duration <= 0 or not any(s.get('codec_type') == 'audio' for s in meta.get('streams', [])):
        raise ValueError('Missing or empty audio stream')
    decode = run(['ffmpeg', '-v', 'error', '-i', str(audio), '-map', '0:a:0', '-f', 'null', '-'])
    scan = run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(audio), '-map', '0:a:0',
                '-af', 'silencedetect=n=-50dB:d=1', '-f', 'null', '-'])
    log = output / 'silence.log'
    log.write_text(scan.stderr)
    intervals = silence_intervals(scan.stderr, duration) if scan.returncode == 0 else []
    events = []
    if timeline:
        timeline = timeline.resolve()
        data = json.loads(timeline.read_text())
        for idx, event in enumerate(data.get('events', [])):
            events.append({'segment_id': f'{idx:03d}', 'start': event.get('start'),
                           'end': event.get('end'), 'text': event.get('text'),
                           'timing_scope': 'provided placement, not forced alignment',
                           'scores': dict.fromkeys(WEIGHTS)})
    dimensions = {k: {'score': None, 'evidence': [], 'rationale': None} for k in WEIGHTS}
    status, total = appeal_gate(dimensions)
    if decode.returncode or scan.returncode:
        status = 'FAIL'
    report = {'source': str(audio), 'audio_sha256': digest(audio), 'duration': duration,
              'timeline': str(timeline) if timeline else None,
              'timeline_sha256': digest(timeline) if timeline else None,
              'decode_passed': decode.returncode == 0, 'scan_passed': scan.returncode == 0,
              'silence_candidates': [{'start': a, 'end': b, 'evidence': str(log),
                                      'interpretation': 'unverified; may be intentional'} for a, b in intervals],
              'segments': events, 'dimensions': dimensions, 'weights': WEIGHTS,
              'total': total, 'status': status,
              'unverified': ['emotion', 'naturalness', 'audio_visual_match', 'caption_alignment', 'sound_design'],
              'scope': 'FFmpeg signal timing only; no audio-understanding model or listening review'}
    if technical_report:
        technical = json.loads(technical_report.read_text())
        report['technical_report'] = str(technical_report.resolve())
        report['technical_total'] = technical.get('total')
        report['delivery_status'] = delivery_gate(technical, report)
    (output / 'audio-appeal-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audio', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeline', type=Path)
    parser.add_argument('--technical-report', type=Path)
    args = parser.parse_args()
    report = inspect(args.audio, args.output, args.timeline, args.technical_report)
    print(json.dumps({'status': report['status'], 'total': report['total'],
                      'delivery_status': report.get('delivery_status')}))
    return {'PASS': 0, 'REWORK': 2, 'NEEDS_REVIEW': 3, 'FAIL': 4}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
