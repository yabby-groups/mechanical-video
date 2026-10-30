"""Create a narration-direction draft from an existing measured timeline."""
import argparse
import json
from pathlib import Path

from .audio_qa import TERMS, digest


def create(timeline, output):
    timeline = timeline.resolve()
    data = json.loads(timeline.read_text())
    events = data.get('events', [])
    if not events or not data.get('model') or not data.get('voice'):
        raise ValueError('A measured timeline with events, model and voice is required')
    segments = []
    for index, event in enumerate(events):
        text = event['text']
        segments.append({'segment_id': f'{index:03}', 'text': text,
                         'start': event['start'], 'end': event['end'],
                         'emotion_intent': 'curious and concise' if index == 0 else 'clear, natural documentary',
                         'key_terms': [term for term in TERMS if term in text],
                         'emphasis': None, 'sync_point': None,
                         'status': 'draft_requires_director_and_picture_review'})
    report = {'timeline': str(timeline), 'timeline_sha256': digest(timeline),
              'model': data['model'], 'voice': data['voice'],
              'tts_controls': 'model and voice only; no emotion parameter asserted', 'segments': segments}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('timeline', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = create(args.timeline, args.output)
    print(json.dumps({'segments': len(report['segments']), 'voice': report['voice']}))


if __name__ == '__main__':
    main()
