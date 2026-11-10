"""Narrow audio-review capability and real-controller completion adapter.

No agent identities, generation commands, publication, or new delivery gates
are manufactured here. The active session supplies actual claim receipts.
"""
import json
from pathlib import Path

from .htm_audio_features import ref, verify, sha
from .htm_audio_model import DIMENSIONS
from .htm_audio_review import qualification

PREFIX = 'htm_audio:'


def validate_capability(name, benchmark):
    if not name.startswith(PREFIX) or name[len(PREFIX):] not in DIMENSIONS:
        raise ValueError('unsupported HTM audio dimension')
    qualified = qualification(benchmark['qualification'], benchmark['model'], benchmark['calibration'])
    if name[len(PREFIX):] not in qualified:
        raise ValueError('HTM dimension has not passed held-out qualification')
    from .htm_audio_model import Engine
    Engine.load(benchmark['model'])
    return True


def validate_report(path, audio=None, script=None):
    result = json.loads(Path(path).read_text())
    if result.get('adapter') != 'htm_audio_review' or result.get('learning') is not False:
        raise ValueError('not a frozen HTM audio review')
    if result.get('status') not in ('PASS', 'REWORK', 'UNQUALIFIED'):
        raise ValueError('invalid HTM review status')
    for key in ('audio', 'script', 'model', 'calibration'):
        verify(result[key])
    from .htm_audio_model import Engine, runtime, runtime_identity
    from .htm_audio_review import load_calibration, validate_predictions
    _, manifest = Engine.load(Path(result['model']['path']).parent)
    cal = load_calibration(result['calibration']['path'], Path(result['model']['path']).parent)
    if runtime_identity(result['runtime']) != runtime_identity(manifest['runtime']):
        raise ValueError('stale report runtime')
    if audio and result['audio'] != ref(audio):
        raise ValueError('HTM audio report belongs to another audio')
    if script and result['script'] != ref(script):
        raise ValueError('HTM audio report belongs to another script')
    if result.get('alignment'):
        verify(result['alignment'])
    for reference in result.get('tracks', {}).values():
        verify(reference)
    coverage = result['coverage']
    if (coverage['samples_consumed'] != coverage['source_samples'] or coverage['source_samples'] <= 0
            or coverage['start'] != 0 or coverage['end'] <= 0):
        raise ValueError('incomplete HTM audio coverage')
    qualified = set()
    if result.get('qualification'):
        verify(result['qualification'])
        qualified = qualification(result['qualification']['path'],
                                  Path(result['model']['path']).parent, result['calibration']['path'])
    if set(result['dimensions']) != set(DIMENSIONS):
        raise ValueError('incomplete HTM dimensions')
    validate_predictions(result, cal)
    for kind, dimension in result['dimensions'].items():
        if dimension['status'] not in ('PASS', 'REWORK', 'UNQUALIFIED'):
            raise ValueError('invalid dimension result')
        if dimension['status'] != 'UNQUALIFIED' and kind not in qualified:
            raise ValueError('unqualified dimension asserted as reviewed')
        if dimension['threshold'] != cal['thresholds'][kind]:
            raise ValueError('report threshold differs from calibration')
        matching = [i for i in result['issues'] if i['kind']==kind]
        if dimension['status'] == 'PASS' and (dimension['candidate_intervals'] or matching):
            raise ValueError('PASS cannot contain defect intervals')
        if dimension['candidate_intervals']:
            if (len(matching) != 1 or matching[0]['status'] != dimension['status']
                    or matching[0]['affected_intervals'] != dimension['candidate_intervals']):
                raise ValueError('inconsistent issue coverage')
        elif dimension['status'] == 'REWORK' or matching:
            raise ValueError('REWORK requires defect intervals and issues')
    if not result['tracks'] and result['dimensions']['masking']['status'] != 'UNQUALIFIED':
        raise ValueError('paired-track masking is unqualified in schema v1')
    if result['text_candidates'] and any(result['dimensions'][k]['status'] != 'UNQUALIFIED'
                                          for k in ('omission', 'repetition', 'mispronunciation')):
        raise ValueError('unresolved recognition differences cannot be accepted')
    if not result.get('alignment') and any(result['dimensions'][k]['status'] != 'UNQUALIFIED'
                                          for k in ('omission', 'repetition', 'mispronunciation', 'pace')):
        raise ValueError('text and pace dimensions require measured alignment')
    states = {v['status'] for v in result['dimensions'].values()}
    expected = 'REWORK' if 'REWORK' in states else ('UNQUALIFIED' if 'UNQUALIFIED' in states else 'PASS')
    if result['status'] != expected:
        raise ValueError('HTM summary does not match dimensions')
    from .htm_audio_review import evaluate
    actual = evaluate(result['audio']['path'], result['script']['path'],
                      Path(result['model']['path']).parent, result['calibration']['path'],
                      alignment=result.get('alignment', {}).get('path') if result.get('alignment') else None,
                      qualified=result.get('qualification', {}).get('path') if result.get('qualification') else None,
                      narration_track=result['tracks'].get('narration', {}).get('path'),
                      mix_track=result['tracks'].get('mix', {}).get('path'),
                      subject_id=result.get('subject_id'))
    if actual != result:
        raise ValueError('review report differs from actual frozen inference')
    return result


def complete_review(record_path, task_id, agent_id, completion_id, report_path, repair_outputs):
    """Convert measured results to existing idempotent, independent repair flow.

    repair_outputs maps issue_id to new-version paths. This records local work;
    it never launches synthesis. Unqualified capabilities become owned internal
    dependencies. Actual assignments must already exist in the canonical ledger.
    """
    from .repair_controller import complete, _is_review
    record = json.loads(Path(record_path).read_text())
    task = record['repair_controller']['tasks'][task_id]
    if not _is_review(task) or task.get('agent_id') != agent_id:
        raise ValueError('requires an actual independently claimed review task')
    report = validate_report(report_path)
    if report.get('subject_id') != str(Path(record_path).resolve()):
        raise ValueError('stable subject_id must be the canonical controller record path')
    base = Path(record_path).resolve().parent
    inputs = {str((base/p).resolve()): v for p, v in task['inputs'].items()}
    if any(inputs.get(report[k]['path']) != report[k]['sha256'] for k in ('audio', 'script')):
        raise ValueError('review inputs do not bind the audio and frozen script')
    required = task['required_checks']
    if any(not name.startswith(PREFIX) for name in required):
        raise ValueError('HTM audio cannot complete visual, subjective, or unrelated checks')
    failures = []
    evidence = {str(Path(report_path).resolve()): sha(report_path)}
    for check in required:
        kind = check[len(PREFIX):]
        dimension = report['dimensions'][kind]
        if dimension['status'] == 'PASS':
            continue
        matched = [i for i in report['issues'] if i['kind']==kind and i['status']=='REWORK']
        if dimension['status'] == 'UNQUALIFIED':
            matched = [{'issue_id': 'HTMA-DEPENDENCY-'+kind, 'owner': 'Director'}]
        for issue in matched:
            key = issue['issue_id']
            if not repair_outputs.get(key):
                raise ValueError('explicit new-version repair output required for '+key)
            failures.append({'issue_id': key, 'owner': issue['owner'],
                             'severity': 'P1', 'required_checks': issue.get('required_checks', [check]),
                             'evidence': evidence, 'repair_outputs': repair_outputs[key],
                             'repair_inputs': {report[k]['path']: report[k]['sha256'] for k in ('audio', 'script')},
                             'repair_capabilities': [],
                             'scope': {k: issue[k] for k in ('start', 'end', 'affected_intervals') if k in issue},
                             'generation_authorized': False})
    return complete(record_path, task_id, agent_id, completion_id, checks=required,
                    verdict='needs-review' if failures else 'pass', failures=failures, evidence=evidence)
