"""One event clock from measured speech; no paragraph-proportion estimates.

Alignment is supplied by an actual aligner/reviewer and hash bound here. This
module validates associations, not whether words were heard correctly.
"""
import json
import math
from pathlib import Path
from .scene_fidelity import file_ref


def build(events, measurement, audio, alignment_evidence):
    audio_ref, evidence_ref = file_ref(audio), file_ref(alignment_evidence)
    if measurement.get('audio') != audio_ref or measurement.get('evidence') != evidence_ref:
        raise ValueError('stale measured audio/alignment evidence')
    if measurement.get('method') not in ('forced_alignment', 'independent_listening_alignment'):
        raise ValueError('measured speech alignment required')
    duration = measurement.get('duration')
    numeric = lambda x: type(x) in (int, float) and math.isfinite(x)
    if not numeric(duration) or duration <= 0:
        raise ValueError('invalid measured duration')
    spans = measurement.get('spans', [])
    by_id = {s['event_id']: s for s in spans}
    ids = [e['id'] for e in events]
    if not ids or len(ids) != len(set(ids)) or len(by_id) != len(spans) or set(by_id) != set(ids):
        raise ValueError('missing/duplicate measured action event')
    timeline = []
    end = 0
    for event in events:
        span = by_id[event['id']]
        start, stop = span['start'], span['end']
        if not all(numeric(x) for x in (start, stop)) or not 0 <= end <= start < stop <= duration:
            raise ValueError('invalid/overlapping measured speech interval')
        if not event.get('phrase') or span.get('text') != event['phrase']:
            raise ValueError('key narration phrase does not match measured words')
        caption = event.get('caption')
        if not isinstance(caption, str) or not 0 < len(caption) <= 20 or '\n' in caption:
            raise ValueError('caption must be one line at most 20 characters')
        if not event.get('requirement') or not event.get('animation') or not isinstance(event.get('foley'), list):
            raise ValueError('event needs original requirement, animation and explicit foley list')
        timeline.append(dict(event, start=start, end=stop))
        end = stop
    return dict(schema_version=1, duration=duration, audio=audio_ref,
                alignment_evidence=evidence_ref, measurement=measurement, events=timeline,
                captions=[dict(event_id=e['id'], text=e['caption'], start=e['start'], end=e['end']) for e in timeline],
                scope='Measured event associations; perceptual review remains separate.')


def verify(timeline):
    try:
        events = [{k:v for k,v in e.items() if k not in ('start','end')} for e in timeline['events']]
        return timeline == build(events, timeline['measurement'], timeline['audio']['path'], timeline['alignment_evidence']['path'])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def gate_errors(checks, base):
    try:
        ref = checks['assets']['event_timeline']
        path = Path(ref['path'])
        path = path if path.is_absolute() else Path(base) / path
        if file_ref(path)['sha256'] != ref['sha256'] or not verify(json.loads(path.read_text())):
            raise ValueError('stale event timeline')
        timeline = json.loads(path.read_text())
        contract_ref = checks['assets']['content_contract']
        contract_path = Path(contract_ref['path'])
        contract = json.loads((contract_path if contract_path.is_absolute() else Path(base)/contract_path).read_text())
        if {e['requirement'] for e in timeline['events']} != {r['id'] for r in contract['requirements']}:
            raise ValueError('event timeline omits original requirements')
        if checks['assets'].get('narration_audio') != timeline['audio']:
            raise ValueError('timeline audio not bound to production assets')
        def read_asset(name):
            ref = checks['assets'][name]
            path = Path(ref['path'])
            path = path if path.is_absolute() else Path(base)/path
            if file_ref(path)['sha256'] != ref['sha256']:
                raise ValueError('stale event consumer: ' + name)
            return json.loads(path.read_text())
        caption_clock = read_asset('timeline')
        if caption_clock.get('captions') != timeline['captions'] or caption_clock.get('duration') != timeline['duration']:
            raise ValueError('subtitle clock differs from measured events')
        for name, field in [('motion','animation'), ('foley_timeline','foley')]:
            expected = [dict(event_id=e['id'], start=e['start'], end=e['end'], binding=e[field]) for e in timeline['events']]
            if read_asset(name).get('event_bindings') != expected:
                raise ValueError(name + ' does not consume measured action events')
        return []
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return ['measured event timeline missing/stale: ' + str(exc)]
