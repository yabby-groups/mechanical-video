"""Read-only, fail-closed association gate, not a geometry or perceptual judge."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

STAGES = {
    'narration': ('source_action',),
    'full-render': ('source_action', 'unfold', 'reassembly', 'attachments', 'clearance',
                    'neighbors', 'overlays', 'foley', 'style', 'local_encode', 'storage'),
    'delivery': ('final_encode',),
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def evaluate(record, base, stage, now=None, require_version=1):
    """Validate production_checks v1 (historical) or v2, without writes."""
    now = time.time() if now is None else now
    errors, gaps = [], []
    p = record.get('production_checks')
    if not isinstance(p, dict) or type(p.get('schema_version')) is not int or p.get('schema_version') not in (1, 2):
        return {'status': 'BLOCKED', 'reasons': ['missing production_checks v1'], 'gaps': []}
    if p['schema_version'] < require_version:
        return {'status': 'BLOCKED', 'reasons': [f'production_checks v{require_version} required for new production'], 'gaps': []}
    assets = p.get('assets', {})
    if not isinstance(assets, dict) or not assets:
        errors.append('missing asset fingerprints')
        assets = {}
    def linked(ref):
        if not isinstance(ref, dict):
            return False
        try:
            path = Path(ref['path'])
            path = path if path.is_absolute() else base / path
            return path.is_file() and sha(path) == ref['sha256']
        except (OSError, KeyError, TypeError):
            return False
    if any(not linked(ref) for ref in assets.values()):
        errors.append('missing or stale asset')
    fingerprints = {key: ref.get('sha256') for key, ref in assets.items() if isinstance(ref, dict)}
    if record.get('hold') or record.get('editorial_hold') or p.get('holds'):
        errors.append('active hold')
    if p.get('critical_mechanical_uncertainty') is not False:
        errors.append('critical mechanical certainty not established')
    # Legacy records are not silently superseded by the new block.
    issues = list(p.get('issues', []))
    for key in ('issues', 'open_issues'):
        legacy = record.get(key, [])
        if isinstance(legacy, list):
            issues.extend(i for i in legacy if isinstance(i, dict))
    for issue in issues:
        closed = issue.get('status') in ('closed', 'resolved', 'verified')
        if issue.get('severity') in ('P0', 'P1') and not closed:
            errors.append('open blocking issue: ' + str(issue.get('issue_id', 'unknown')))
        attempts = issue.get('repair_attempts')
        if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 0:
            errors.append('missing repair count')
        elif not closed and (attempts >= 3 or issue.get('rounds_without_improvement', 0) >= 2):
            errors.append('repair strategy exhausted')
    checks = p.get('checks', [])
    if not isinstance(checks, list):
        raise ValueError('checks must be a list')
    actions = p.get('actions', {})
    if not isinstance(actions, dict):
        raise ValueError('actions must map action IDs to required intervals')
    if stage != 'delivery' and not actions:
        errors.append('missing action inventory')
    required = [(kind, action) for kind in STAGES[stage] for action in
                (actions if kind in ('source_action', 'unfold', 'reassembly', 'attachments', 'clearance', 'neighbors', 'overlays', 'foley') else [None])]
    if p['schema_version'] == 2 and stage in ('full-render', 'delivery'):
        required.append(('baseline_fidelity', None))
    for kind, action in required:
        candidates = [c for c in checks if c.get('kind') == kind and c.get('action') == action]
        valid = False
        for c in candidates:
            interval = actions[action] if action is not None else p.get('required_interval')
            coverage = c.get('coverage')
            numeric = lambda v: isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v)
            if not (isinstance(interval, list) and isinstance(coverage, list) and len(interval) == len(coverage) == 2
                    and all(numeric(v) for v in interval + coverage)
                    and 0 <= coverage[0] <= interval[0] <= interval[1] <= coverage[1]):
                continue
            if c.get('status') != 'PASS' or c.get('asset_fingerprints') != fingerprints:
                continue
            if not c.get('method') or not c.get('scope') or not c.get('reviewer'):
                continue
            if not c.get('producer') or c['reviewer'] == c['producer']:
                continue
            refs = c.get('evidence', [])
            if not refs or not all(linked(ref) for ref in refs):
                continue
            if kind == 'baseline_fidelity':
                from . import scene_fidelity
                try:
                    def read_asset(name):
                        path = Path(assets[name]['path'])
                        return json.loads((path if path.is_absolute() else base / path).read_text())
                    baseline = read_asset('baseline_inventory')
                    current = read_asset('scene_inventory')
                    result = scene_fidelity.compare(baseline, current, read_asset('scene_policy'))
                    # Bind evaluated inventory to the actual frozen source inputs.
                    if (result['status'] != 'PASS'
                            or baseline['source']['sha256'] != fingerprints['baseline_scene']
                            or current['source']['sha256'] != fingerprints['baseline_scene']
                            or current['renderer']['sha256'] != fingerprints['renderer']
                            or current['implementation_sha256'] != sha(scene_fidelity.__file__)):
                        continue
                    reports = []
                    for ref in refs:
                        path = Path(ref['path'])
                        if path.suffix.lower() == '.json':
                            reports.append(json.loads((path if path.is_absolute() else base / path).read_text()))
                    views = {'whole_machine', 'bottom', 'routing', 'mechanism'}
                    if (result not in reports or not views.issubset(set(c.get('reviewed_views', [])))
                            or not any(Path(r['path']).suffix.lower() in ('.png', '.jpg', '.jpeg') for r in refs)):
                        continue
                except (OSError, ValueError, KeyError, TypeError, AttributeError):
                    continue
            if kind in ('local_encode', 'final_encode'):
                # Require media plus an associated deterministic probe/decode report,
                # not a still image renamed as an encoding approval.
                media_refs = [ref for ref in refs if Path(ref['path']).suffix.lower() in ('.mp4', '.mov', '.mkv')]
                encoded = False
                for ref in refs:
                    path = Path(ref['path'])
                    if path.suffix.lower() != '.json':
                        continue
                    try:
                        data = json.loads((path if path.is_absolute() else base / path).read_text())
                        if data.get('identity', {}).get('media_sha256') not in [m['sha256'] for m in media_refs]:
                            continue
                        results = data.get('checks', {})
                        passed = True
                        for name in ('probe', 'decode'):
                            entry = results.get(name, {})
                            result = entry.get('result', {})
                            result_sha = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                            if entry.get('status') != 'PASS' or result.get('returncode') != 0 or entry.get('result_sha256') != result_sha:
                                passed = False
                        encoded = encoded or passed
                    except (OSError, ValueError, TypeError, AttributeError):
                        continue
                if not encoded:
                    continue
            if kind == 'source_action' and not (c.get('source_parts') and c.get('representation') in ('real', 'teaching', 'mixed') and c.get('explanation_roles')):
                continue
            if kind == 'storage':
                created = c.get('created_at')
                if not numeric(created) or not 0 <= now - created <= 900:
                    continue
                try:
                    ref = refs[0]
                    path = Path(ref['path'])
                    budget = json.loads((path if path.is_absolute() else base / path).read_text())
                    if budget['status'] != 'PASS' or budget['available_free_bytes'] < budget['required_free_bytes']:
                        continue
                except (OSError, KeyError, ValueError, TypeError):
                    continue
            valid = True
            break
        if not valid:
            errors.append('missing/stale check: ' + kind + (':' + str(action) if action else ''))
    gaps = p.get('capability_gaps', [])
    formal = p.get('delivery_mode') == 'formal'
    if stage == 'delivery':
        if p.get('delivery_mode') not in ('review', 'formal'):
            errors.append('delivery_mode must be review or formal')
        if formal:
            reviews = p.get('acceptance', {})
            for name, threshold in (('overall', 90), ('technical', 90), ('audience', 85), ('audio_technical', 90), ('audio_appeal', 85)):
                r = reviews.get(name, {})
                score = r.get('score')
                if (not isinstance(score, (int, float)) or isinstance(score, bool) or not threshold <= score <= 100
                        or r.get('status') != 'PASS' or r.get('asset_fingerprints') != fingerprints
                        or not r.get('producer') or not r.get('reviewer') or r['producer'] == r['reviewer']
                        or not r.get('evidence') or not all(linked(ref) for ref in r['evidence'])):
                    errors.append('missing independent acceptance: ' + name)
                if r.get('profile', 'formal') != 'formal':
                    errors.append('local profile cannot provide formal acceptance: ' + name)
                for ref in r.get('evidence', []):
                    try:
                        path = Path(ref['path'])
                        if path.suffix.lower() == '.json':
                            data = json.loads((path if path.is_absolute() else base / path).read_text())
                            if isinstance(data, dict) and data.get('profile', 'formal') != 'formal':
                                errors.append('local profile cannot provide formal acceptance: ' + name)
                    except (OSError, ValueError, TypeError, KeyError):
                        continue
            if gaps or p.get('all_established_gates_passed') is not True:
                errors.append('formal acceptance gates incomplete')
    return {'schema_version': p['schema_version'], 'stage': stage,
            'status': 'BLOCKED' if errors else ('REVIEW_DELIVERY' if stage == 'delivery' and not formal else 'READY'),
            'reasons': errors, 'gaps': gaps,
            'scope': 'Record integrity and associations only; no collision, playback or listening verdict.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--stage', choices=STAGES, required=True)
    parser.add_argument('--require-version', type=int, choices=(1, 2), default=1,
                        help='Use 2 for new production; default preserves historical read-only evaluation')
    args = parser.parse_args(argv)
    try:
        record = json.loads(args.record.read_text())
        if not isinstance(record, dict):
            raise ValueError('record must be an object')
        report = evaluate(record, args.record.resolve().parent, args.stage, require_version=args.require_version)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        print(json.dumps({'status': 'INPUT_ERROR', 'reasons': ['Invalid record or unreadable input']}))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['status'] == 'BLOCKED' else 0


if __name__ == '__main__':
    raise SystemExit(main())
