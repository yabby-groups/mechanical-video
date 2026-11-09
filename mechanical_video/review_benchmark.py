"""Validate exercised reviewer controls; declarations alone cannot qualify a model.

This validates evidence integrity, not the truth of perceptual observations.
Raw responses and ground truth must be assessed by the benchmark runner.
"""
import hashlib
from pathlib import Path

DEFECTS = {'action_contradiction', 'occlusion', 'speech_desync'}
CONTROLS = {'normal', 'silence'}


def validate_benchmark(report, base):
    """Raise ValueError for failed, incomplete, stale or unexercised benchmarks."""
    if not isinstance(report, dict):
        raise ValueError('malformed sensory benchmark')
    if report.get('schema_version') != 1 or report.get('status') != 'PASS':
        raise ValueError('sensory benchmark must contain passing exercised cases')
    if not all(isinstance(report.get(k), str) and report[k].strip()
               for k in ('adapter', 'model_revision', 'runtime_fingerprint')):
        raise ValueError('sensory benchmark runtime is not fingerprinted')
    cases = report.get('cases')
    if not isinstance(cases, list) or not cases:
        raise ValueError('sensory benchmark cases missing')
    topics, identities = {}, set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError('malformed sensory benchmark case')
        topic, kind, identity = (case.get(k) for k in ('topic', 'kind', 'id'))
        if not all(isinstance(v, str) and v.strip() for v in (topic, kind, identity)):
            raise ValueError('benchmark case identity missing')
        if identity in identities or kind not in DEFECTS | CONTROLS:
            raise ValueError('duplicate or unknown benchmark case')
        identities.add(identity)
        expected = 'defect' if kind in DEFECTS else 'clear'
        if case.get('verdict') != expected or case.get('passed') is not True:
            raise ValueError('review adapter failed benchmark case: ' + identity)
        if not isinstance(case.get('observation'), str) or not case['observation'].strip():
            raise ValueError('benchmark observation missing')
        if case.get('speech_control_passed') is not True:
            raise ValueError('speech isolation control failed')
        coverage = case.get('coverage', {})
        if not isinstance(coverage, dict):
            raise ValueError('malformed benchmark coverage')
        for observed, total in (('frames_consumed', 'source_frames'),
                                ('audio_samples_consumed', 'source_audio_samples')):
            if (type(coverage.get(total)) is not int or coverage[total] <= 0
                    or type(coverage.get(observed)) is not int
                    or coverage[observed] != coverage[total]):
                raise ValueError('incomplete benchmark media coverage')
        for key in ('media', 'raw_response', 'ground_truth'):
            ref = case.get(key, {})
            if not isinstance(ref, dict) or not ref.get('path') or not ref.get('sha256'):
                raise ValueError('benchmark evidence missing: ' + key)
            path = Path(ref['path'])
            path = path if path.is_absolute() else Path(base) / path
            if hashlib.sha256(path.read_bytes()).hexdigest() != ref['sha256']:
                raise ValueError('stale benchmark evidence: ' + key)
        topics.setdefault(topic, set()).add(kind)
    if len(topics) < 2 or any(not (DEFECTS | CONTROLS) <= kinds for kinds in topics.values()):
        raise ValueError('benchmark requires defects and controls on two topics')
