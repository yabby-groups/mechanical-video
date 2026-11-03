"""Read-only ready-input and exclusive-output check; not an agent scheduler."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

PHASES = ('research', 'creative', 'script', 'visual', 'audio', 'editing', 'qa')


def phase_event(phase, event, thread_id):
    if phase not in PHASES or event not in ('start', 'end') or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,150}', thread_id):
        raise ValueError('Invalid phase event')
    return {'type': 'phase_' + event, 'phase': phase, 'thread_id': thread_id,
            'timestamp': datetime.now(timezone.utc).isoformat()}


def _path(value, base):
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def _linked(ref, base):
    try:
        with _path(ref['path'], base).open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest() == ref['sha256']
    except (KeyError, TypeError, OSError):
        return False


def _signature(task, base):
    return hashlib.sha256(json.dumps({k: task[k] for k in ('role', 'goal', 'scope', 'checks', 'capabilities')}
                                    | {'inputs': {name: {'path': str(_path(ref['path'], base)), 'sha256': ref['sha256']}
                                                  for name, ref in task['inputs'].items()}},
                                    sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def evaluate(record, base, handoff_id):
    base = Path(base).resolve()
    tasks = record['production_handoffs']
    task = tasks[handoff_id]
    errors, ready, deferred = [], [], []
    for key in ('owner', 'role', 'goal', 'scope'):
        if not isinstance(task.get(key), str) or not task[key].strip():
            errors.append('missing ' + key)
    if task.get('role') in ('video_qa', 'audio_qa', 'audio_appeal_qa', 'audience_qa'):
        if not task.get('producer') or task.get('producer') == task.get('owner'):
            errors.append('independent reviewer required')
    if not {'completed', 'failed', 'stage_changed'}.issubset(set(task.get('completion_events', []))):
        errors.append('missing completion/exception notifications')
    inputs = task.get('inputs', {})
    if not inputs or not all(_linked(ref, base) for ref in inputs.values()):
        errors.append('missing or stale ready inputs')
    checks, capabilities = task.get('checks', {}), task.get('capabilities', {})
    if not checks:
        errors.append('missing check inventory')
    for check, capability in checks.items():
        available = capabilities.get(capability, {})
        if available.get('available') is True and available.get('method'):
            ready.append(check)
        else:
            deferred.append(check)
            if not available.get('question') or not available.get('next_reviewer'):
                errors.append('missing capability handoff: ' + capability)
    outputs = [_path(p, base) for p in task.get('outputs', [])]
    if not outputs or len(outputs) != len(set(outputs)):
        errors.append('missing or duplicate exclusive outputs')
    input_paths = [_path(ref['path'], base) for ref in inputs.values()]
    overlaps = lambda a, b: a == b or a in b.parents or b in a.parents
    if any(overlaps(a, b) for i, a in enumerate(outputs) for b in outputs[i + 1:]):
        errors.append('overlapping output paths in one task')
    for output in outputs:
        if base not in output.parents or any(overlaps(output, p) for p in input_paths):
            errors.append('output overlaps inputs or escapes episode directory')
        for other_id, other in tasks.items():
            if other_id != handoff_id and other.get('state') in ('ready', 'running'):
                if any(overlaps(output, _path(p, base)) for p in other.get('outputs', [])):
                    errors.append('output already owned by ' + other_id)
    signature = _signature(task, base)
    reuse = None
    for other_id, other in tasks.items():
        if other_id == handoff_id or other.get('state') not in ('running', 'completed'):
            continue
        if _signature(other, base) == signature:
            if other['state'] == 'running':
                reuse = other_id
            elif other.get('results') and all(_linked(ref, base) for ref in other['results']):
                reuse = other_id
            else:
                errors.append('matching prior result is stale: ' + other_id)
    if task.get('state') not in ('pending', 'ready'):
        errors.append('task already started or completed; do not redispatch')
    if not reuse and any(p.exists() and (not p.is_dir() or any(p.iterdir())) for p in outputs):
        errors.append('output already contains artifacts; use a new version')
    return {'schema_version': 1, 'handoff_id': handoff_id, 'input_signature': signature,
            'status': 'BLOCKED' if errors else ('REUSE' if reuse else ('READY' if ready else 'CAPABILITY_GAP')),
            'reasons': sorted(set(errors)), 'ready_checks': ready, 'deferred_checks': deferred,
            'reuse_handoff': reuse,
            'scope': 'Input readiness and declared ownership only; does not dispatch, authorize or accept media.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('check')
    check.add_argument('--record', type=Path, required=True)
    check.add_argument('--handoff-id', required=True)
    phase = sub.add_parser('phase')
    phase.add_argument('--phase', choices=PHASES, required=True)
    phase.add_argument('--event', choices=('start', 'end'), required=True)
    phase.add_argument('--thread-id', required=True)
    args = parser.parse_args(argv)
    try:
        result = (phase_event(args.phase, args.event, args.thread_id) if args.command == 'phase' else
                  evaluate(json.loads(args.record.read_text()), args.record.resolve().parent, args.handoff_id))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print(json.dumps({'status': 'INPUT_ERROR', 'reasons': ['Invalid handoff inputs']}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get('status') in ('BLOCKED', 'CAPABILITY_GAP') else 0


if __name__ == '__main__':
    raise SystemExit(main())
