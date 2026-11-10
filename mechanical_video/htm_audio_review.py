"""Local audio-only HTM review: train / calibrate / evaluate / benchmark.

PASS is dimension-scoped and requires a matching held-out qualification report.
Anomaly is reported independently, never converted into a listening score.
"""
import argparse
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path

import numpy as np

from .htm_audio_features import extract, ref, verify, sha
from .htm_audio_model import (DIMENSIONS, Engine, features_for, frame_labels,
                              load_dataset, runtime, runtime_identity, train, supervised_dimensions, acoustic_normal)
from .speech_alignment import normalize

_QUALIFICATION_CACHE = {}
_CALIBRATION_CACHE = set()
_CALIBRATION_INPUTS = {}


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def identity(model):
    return ref(Path(model)/'manifest.json')


def partition(dataset_path, model, split):
    data = load_dataset(dataset_path)
    manifest = json.loads((Path(model)/'manifest.json').read_text())
    if data and ref(dataset_path) != manifest['dataset']:
        raise ValueError('use the frozen, disjoint corpus manifest from training')
    cases = [c for c in data['cases'] if c['split'] == split]
    if not cases:
        raise ValueError('missing held-out ' + split + ' cases')
    return cases


def scores(sequence, kind):
    return np.asarray([row['probabilities'][kind] for row in sequence])


def spans(values, intervals, threshold, minimum_seconds=.06):
    if threshold is None:
        return []
    flagged = np.r_[False, np.asarray(values) >= threshold, False].astype(int)
    starts, ends = np.flatnonzero(np.diff(flagged)==1), np.flatnonzero(np.diff(flagged)==-1)
    return [[float(intervals[a, 0]), float(intervals[b-1, 1])]
            for a, b in zip(starts, ends) if intervals[b-1, 1]-intervals[a, 0] >= minimum_seconds-1e-9]


def baseline(features):
    """Conservative existing-style amplitude/silence rules, with context caveats."""
    f, t = features['features'], features['intervals']
    results = {k: [] for k in DIMENSIONS}
    results['clipping'] = spans(f[:, 2], t, .01)
    results['pause'] = spans(f[:, 8], t, .5, minimum_seconds=1.)
    return results


def text_candidates(script, alignment, duration):
    if not alignment:
        return [], 'UNQUALIFIED'
    expected = normalize(Path(script).read_text())
    data = json.loads(Path(alignment).read_text())
    actual = normalize(data['greedy_transcript'])
    measured=[];cursor=0;previous=0.
    for unit in data.get('recognition_units', []):
        token=normalize(unit['text'])
        if (not token or not all(np.isfinite(unit[k]) for k in ('start','end','confidence'))
                or not 0<=previous<=unit['start']<unit['end']<=duration
                or not 0<=unit['confidence']<=1):
            raise ValueError('invalid actual recognition unit')
        measured.append((cursor,cursor+len(token),unit))
        cursor+=len(token);previous=unit['end']
    recognized_timing = bool(measured) and ''.join(normalize(u[2]['text']) for u in measured)==actual
    if normalize(data['transcript']) != expected:
        raise ValueError('alignment does not use frozen narration')
    candidates = []
    for op, a, b, c, d in SequenceMatcher(None, expected, actual, autojunk=False).get_opcodes():
        if op == 'equal':
            continue
        selected = data['characters'][a:b]
        start=selected[0]['start'] if selected else 0.
        end=selected[-1]['end'] if selected else duration
        timing='expected-text alignment candidate';confidence=None
        if recognized_timing:
            actual_units=[u for lo,hi,u in measured if lo<d and hi>c]
            if actual_units:
                start,end=actual_units[0]['start'],actual_units[-1]['end']
                confidence=float(np.mean([u['confidence'] for u in actual_units]))
                timing='actual recognized token interval'
            else:
                before=[u for lo,hi,u in measured if hi<=c]
                after=[u for lo,hi,u in measured if lo>=c]
                start=before[-1]['end'] if before else 0.
                end=after[0]['start'] if after else duration
                if end<=start:
                    start=before[-1]['start'] if before else 0.
                    end=after[0]['end'] if after else duration
                timing='actual recognized neighbor bracket; missing speech has no observed token span'
        kind={'delete':'omission','insert':'repetition','replace':'mispronunciation'}[op]
        if op=='insert' and actual[c:d] not in expected:
            kind='extra_speech'
        candidates.append({'kind': kind,
                           'expected': expected[a:b], 'recognized': actual[c:d],
                           'start': start, 'end': end,
                           'recognition_confidence': confidence,
                           'confidence': None, 'status': 'UNQUALIFIED',
                           'actionable': False, 'automatic_generation': False,
                           'reason': 'Pronunciation-only policy: ASR spelling is not a speech defect; actual sound requires corroboration',
                           'timing': timing})
    # Technical terms get explicit candidate evidence, never auto-resynthesis.
    terms_path = Path(__file__).resolve().parent.parent/'docs/mechanical-terms.json'
    if terms_path.is_file():
        for term in json.loads(terms_path.read_text())['terms']:
            if normalize(term) in expected and normalize(term) not in actual:
                candidates.append({'kind': 'terminology', 'expected': term,
                                   'recognized': actual, 'start': 0., 'end': duration,
                                   'confidence': None, 'status': 'UNQUALIFIED',
                                   'actionable': False, 'automatic_generation': False,
                                   'reason': 'mechanical term not recognized; spelling alone cannot trigger repair; acoustic corroboration required'})
    return candidates, 'UNQUALIFIED' if candidates else 'MATCH_CANDIDATE'


def calibrate(dataset_path, model, output):
    cases = partition(dataset_path, model, 'calibration')
    observations, normals = [], []
    for c in cases:
        engine, _ = Engine.load(model)  # same frozen checkpoint for each audio
        f = features_for(c)
        seq = engine.sequence_set(f)['frames']
        observations.append((c, f, seq))
        if acoustic_normal(c):
            normals.append(c['recording_id'])
    if len(set(normals)) < 2:
        raise ValueError('insufficient calibration: need two independent normal recordings')
    thresholds = {}
    for kind in DIMENSIONS:
        positives = {c['recording_id'] for c in cases if any(l['kind']==kind for l in c.get('labels', []))}
        if len(positives)<2:
            thresholds[kind] = None
            continue
        best = None
        values = np.concatenate([scores(seq, kind) for _, _, seq in observations])
        thresholds_to_try = sorted(set([.001,.005,.01,.02,.05,.1,.2,.3,.4,.5,.6,.7,.8,.9,.95,.99] +
                                      [float(v) for v in np.quantile(values, np.linspace(0, 1, 21)) if 0 < v <= 1]))
        for threshold in thresholds_to_try:
            positives_by_group, normals_by_group = {}, {}
            for c, f, seq in observations:
                labels = [l for l in c.get('labels', []) if l['kind']==kind]
                prediction = spans(scores(seq, kind), f['intervals'], threshold)
                group = c['recording_id']
                if labels:
                    localized = all(any(a<l['end'] and b>l['start'] for a,b in prediction) for l in labels)
                    positives_by_group[group] = positives_by_group.get(group, True) and localized
                elif kind in supervised_dimensions(c):
                    normals_by_group[group] = normals_by_group.get(group, True) and not bool(prediction)
            recall = sum(positives_by_group.values())/max(1,len(positives_by_group))
            fpr = 1-sum(normals_by_group.values())/max(1,len(normals_by_group))
            metric = recall-fpr
            if best is None or (metric, threshold) > best:
                best = (metric, float(threshold))
        thresholds[kind] = best[1]
    anomaly = [r['anomaly'] for c, _, seq in observations if acoustic_normal(c) for r in seq]
    result = {'schema_version': 1, 'model': identity(model), 'dataset': ref(dataset_path),
              'thresholds': thresholds, 'anomaly_threshold': float(np.quantile(anomaly, .95)),
              'cases': [c['id'] for c in cases], 'learning': False,
              'scope': 'calibration only; no qualification or overall quality score'}
    if output is not None:
        write_new(output, result)
    return result


def load_calibration(path, model):
    result = json.loads(Path(path).read_text())
    if result['model'] != identity(model) or result.get('learning') is not False:
        raise ValueError('calibration mismatch')
    if set(result['thresholds']) != set(DIMENSIONS):
        raise ValueError('incomplete calibration dimensions')
    if any(v is not None and (not np.isfinite(v) or not 0 < v <= 1)
           for v in result['thresholds'].values()):
        raise ValueError('invalid calibration threshold')
    _, frozen = Engine.load(model)
    key = (sha(path), sha(Path(model)/'manifest.json'), tuple(sorted(frozen['files'].items())))
    if key in _CALIBRATION_CACHE:
        for dependency in _CALIBRATION_INPUTS[key]:
            verify(dependency)
    else:
        cases=partition(result['dataset']['path'], model, 'calibration')
        actual = calibrate(result['dataset']['path'], model, None)
        if actual != result:
            raise ValueError('calibration differs from frozen calibration-only execution')
        if len(_CALIBRATION_CACHE) >= 8:
            _CALIBRATION_CACHE.clear()
            _CALIBRATION_INPUTS.clear()
        _CALIBRATION_CACHE.add(key)
        _CALIBRATION_INPUTS[key]=[result['dataset']] + [c[k] for c in cases
            for k in ('audio','script','alignment','narration_track','mix_track') if c.get(k)]
    return result


def qualification(path, model, calibration):
    if path is None:
        return set()
    value = json.loads(Path(path).read_text())
    if value.get('split', 'test') != 'test':
        raise ValueError('development results cannot qualify a capability')
    if (value['model'] != identity(model) or value['calibration'] != ref(calibration)
            or value['adapter'] != ref(Path(__file__))):
        raise ValueError('qualification does not match frozen runtime/model/calibration')
    if not value.get('evidence') or not value.get('cases'):
        raise ValueError('qualification lacks held-out case evidence')
    for evidence in value['evidence']:
        verify(evidence)
    cal = load_calibration(calibration, model)
    expected_cases = partition(cal['dataset']['path'], model, 'test')
    # Revalidate evidence and checkpoint bytes before using any cached execution.
    _, frozen = Engine.load(model)
    cache_key = (sha(path), sha(calibration), sha(Path(model)/'manifest.json'),
                 tuple(sorted(frozen['files'].items())))
    if cache_key in _QUALIFICATION_CACHE:
        return set(_QUALIFICATION_CACHE[cache_key])
    expected = {c['id']: c for c in expected_cases}
    if len(value['cases']) != len(expected):
        raise ValueError('qualification must cover the entire frozen test partition')
    seen = set()
    for observation in value['cases']:
        case, review = observation['case'], observation['review']
        if case['id'] in seen or case != expected.get(case['id']):
            raise ValueError('qualification case differs from frozen test partition')
        seen.add(case['id'])
        if (review['audio'] != case['audio'] or review['script'] != case['script']
                or review['model'] != identity(model) or review['calibration'] != ref(calibration)
                or review['learning'] is not False):
            raise ValueError('qualification observation input/model mismatch')
        coverage = review['coverage']
        if coverage['source_samples'] <= 0 or coverage['source_samples'] != coverage['samples_consumed']:
            raise ValueError('incomplete held-out audio coverage')
        validate_predictions(review, cal)
        actual = evaluate(case['audio']['path'], case['script']['path'], model, calibration,
                          case.get('alignment', {}).get('path'), subject_id=case['id'],
                          narration_track=case.get('narration_track', {}).get('path'),
                          mix_track=case.get('mix_track', {}).get('path'))
        # A self-consistent edited probability array must not enable a capability.
        for field in ('frame_predictions', 'baseline', 'coverage', 'dimensions', 'tracks', 'alignment'):
            if actual[field] != review[field]:
                raise ValueError('held-out result differs from actual frozen inference: '+field)
    calculated = summarize(value['cases'])
    if calculated != value['dimensions']:
        raise ValueError('qualification metrics differ from held-out observations')
    result = {kind for kind, row in calculated.items() if eligible(row)}
    if len(_QUALIFICATION_CACHE) >= 8:
        _QUALIFICATION_CACHE.clear()
    _QUALIFICATION_CACHE[cache_key] = frozenset(result)
    return result


def validate_predictions(review, cal):
    frames = review['frame_predictions']
    intervals = np.asarray([[f['start'], f['end']] for f in frames])
    if (not len(frames) or not np.isfinite(intervals).all() or intervals[0, 0] != 0
            or np.any(intervals[:, 1] <= intervals[:, 0])
            or not np.allclose(intervals[1:, 0], intervals[:-1, 1], atol=1e-9)
            or abs(intervals[-1, 1] - review['coverage']['end']) > 1e-9):
        raise ValueError('incomplete frame prediction coverage')
    for frame in frames:
        probabilities = frame['probabilities']
        if (set(probabilities) != set(DIMENSIONS)
                or any(not np.isfinite(v) or not 0 <= v <= 1 for v in probabilities.values())):
            raise ValueError('invalid classifier probabilities')
    for kind in DIMENSIONS:
        predicted = spans([f['probabilities'][kind] for f in frames], intervals, cal['thresholds'][kind])
        dimension = review['dimensions'][kind]
        if (predicted != dimension['candidate_intervals'] or dimension['threshold'] != cal['thresholds'][kind]
                or abs(dimension['predicted_quality'] - (1-float(np.mean([f['probabilities'][kind] for f in frames])))) > 1e-9):
            raise ValueError('predictions disagree with raw frame results')


def evaluate(audio, script, model, calibration, alignment=None, qualified=None,
             narration_track=None, mix_track=None, subject_id=None):
    engine, manifest = Engine.load(model)
    cal = load_calibration(calibration, model)
    f = extract(audio, alignment, narration_track, mix_track)
    sequence_levels = engine.sequence_set(f)
    sequence = sequence_levels['frames']
    qualified_dimensions = qualification(qualified, model, calibration)
    candidates, text_status = text_candidates(script, alignment, f['duration'])
    dimensions, issues = {}, []
    subject = subject_id or sha(script)
    for kind in DIMENSIONS:
        detected = spans(scores(sequence, kind), f['intervals'], cal['thresholds'][kind])
        enabled = kind in qualified_dimensions
        # Raw acoustics do not establish which words were spoken.
        if kind in ('omission', 'repetition', 'mispronunciation') and not alignment:
            enabled = False
        state = ('REWORK' if detected else 'PASS') if enabled else 'UNQUALIFIED'
        dimensions[kind] = {'status': state, 'threshold': cal['thresholds'][kind],
                            'candidate_intervals': detected,
                            'predicted_quality': 1-float(np.mean(scores(sequence, kind))),
                            'confidence': None, 'confidence_note': 'classifier probability is not calibrated confidence'}
        if detected:
            # One persistent issue per subject and dimension, retaining all local
            # intervals. Removing the first defect cannot renumber the others.
            start, end = detected[0][0], detected[-1][1]
            stable = hashlib.sha256(f'{subject}:{kind}'.encode()).hexdigest()[:16]
            issues.append({'issue_id': 'HTMA-'+stable, 'kind': kind, 'start': start, 'end': end,
                           'affected_intervals': detected,
                           'status': state, 'owner': 'Audio Production' if enabled else 'Director',
                           'confidence': None, 'evidence': f['audio'],
                           'required_checks': ['htm_audio:'+kind, 'remeasured_alignment',
                                               'neighbor_continuity', 'final_mix', 'independent_recheck'],
                           'dependency': 'existing_authorization_required_before_resynthesis',
                           'automatic_generation': False})
    tracks = f['tracks']
    if not tracks:
        dimensions['masking']['status'] = 'UNQUALIFIED'
    if candidates:
        for kind in ('omission', 'repetition', 'mispronunciation'):
            dimensions[kind]['status'] = 'UNQUALIFIED'
    for issue in issues:
        issue['status'] = dimensions[issue['kind']]['status']
        if issue['status'] == 'UNQUALIFIED':
            issue['owner'] = 'Director'
    statuses = {v['status'] for v in dimensions.values()}
    baseline_results = baseline(f)
    for candidate in candidates:
        if candidate['kind'] in baseline_results:
            baseline_results[candidate['kind']].append([candidate['start'], candidate['end']])
    return {'schema_version': 1, 'adapter': 'htm_audio_review', 'capability': 'htm_audio_review',
            'status': 'REWORK' if 'REWORK' in statuses else ('UNQUALIFIED' if 'UNQUALIFIED' in statuses else 'PASS'),
            'subject_id': subject_id,
            'text_policy': 'pronunciation_only; ignore ASR orthographic errors when actual sound is correct; no text-only repair',
            'audio': f['audio'], 'script': ref(script), 'alignment': f['alignment'],
            'model': identity(model), 'calibration': ref(calibration),
            'qualification': ref(qualified) if qualified else None, 'runtime': manifest['runtime'],
            'coverage': f['coverage'], 'raw_amplitude': f['raw_amplitude'],
            'dimensions': dimensions, 'issues': issues, 'text_status': text_status,
            'text_candidates': candidates, 'tracks': tracks, 'learning': False,
            'anomaly': {'threshold': cal['anomaly_threshold'],
                        'mean': float(np.mean([r['anomaly'] for r in sequence])),
                        'frames': [{'start': float(t[0]), 'end': float(t[1]), 'value': r['anomaly']}
                                   for t, r in zip(f['intervals'], sequence)],
                        'scope': 'raw temporal novelty, not a quality score'},
            'frame_predictions': [{'start': float(t[0]), 'end': float(t[1]), 'probabilities': r['probabilities']}
                                  for t, r in zip(f['intervals'], sequence)],
            'sequence_levels': {name: {'count': len(values), 'anomaly_mean': float(np.mean([v['anomaly'] for v in values]))}
                                for name, values in sequence_levels.items()},
            'alignment_unit_scope': 'measured characters and sentences; no verified syllable/phoneme boundaries',
            'uncovered': [k for k, v in dimensions.items() if v['status']=='UNQUALIFIED'] +
                         ['visual_understanding', 'continuous_av', 'formal_delivery'],
            'baseline': baseline_results}


def wilson(successes, count):
    if not count:
        return [0., 1.]
    z, p = 1.95996398454, successes/count
    center = (p+z*z/(2*count))/(1+z*z/count)
    half = z*np.sqrt(p*(1-p)/count+z*z/(4*count*count))/(1+z*z/count)
    return [float(center-half), float(center+half)]


def rank(values):
    a = np.asarray(values)
    return np.asarray([np.sum(a < v)+(np.sum(a == v)+1)/2 for v in a])


def spearman(x, y):
    if len(x)<3 or np.std(rank(x)) == 0 or np.std(rank(y)) == 0:
        return None
    return float(np.corrcoef(rank(x), rank(y))[0, 1])


def eligible(row):
    return (row['defect_count'] >= 50 and row['normal_count'] >= 50
            and row['recall'] >= .95 and row['false_positive_rate'] <= .05
            and row['supported'] and row['independent_test_groups'] and row['htm_gain'] > 0
            and (row['subjective'] or (row.get('known_negative_count',0)>=50
                 and row.get('cross_defect_false_positive_rate',1.)<=.05))
            and (not row['subjective'] or (row['independent_ratings'] >= 50
                 and row['spearman'] is not None and row['spearman'] >= .7)))


def summarize(observations):
    dimensions = {}
    for kind in DIMENSIONS:
        positives, negatives, tp, fp, baseline_tp, baseline_fp = set(), set(), set(), set(), set(), set()
        positive_results, baseline_results, rating_groups = {}, {}, {}
        known_negatives, cross_fp = set(), set()
        errors, ratings, quality = [], [], []
        subjective = kind in ('naturalness', 'expression')
        for obs in observations:
            c, r = obs['case'], obs['review']
            group = c['recording_id']
            labels = [l for l in c.get('labels', []) if l['kind']==kind]
            detected = r['dimensions'][kind]['candidate_intervals']
            base = r['baseline'][kind]
            if kind in c.get('negative_kinds', []) and c.get('labels'):
                known_negatives.add(group)
                if detected:cross_fp.add(group)
            hit = lambda predicted: all(any(a < l['end'] and b > l['start'] for a, b in predicted) for l in labels)
            if labels:
                positives.add(group)
                positive_results[group] = positive_results.get(group, True) and hit(detected)
                baseline_results[group] = baseline_results.get(group, True) and hit(base)
                if hit(detected):
                    tp.add(group)
                    errors.extend(min(abs(a-l['start']) for a,b in detected
                                      if a<l['end'] and b>l['start']) for l in labels
                                  if any(a<l['end'] and b>l['start'] for a,b in detected))
                if hit(base):
                    baseline_tp.add(group)
            elif not c.get('labels') and kind in supervised_dimensions(c):
                negatives.add(group)
                if detected:
                    fp.add(group)
                if base:
                    baseline_fp.add(group)
            rating = c.get('quality_ratings', {}).get(kind)
            if (rating is not None and c['label_source']=='independent_rating'
                    and c.get('producer') and c['labeler'] != c['producer']):
                if not np.isfinite(rating):
                    raise ValueError('invalid independent quality rating')
                rating_groups.setdefault(group, []).append((rating, r['dimensions'][kind]['predicted_quality']))
        # All copies stay in one original-recording group. Every defect copy in
        # that group must be detected; any normal-copy false alarm counts once.
        tp = {g for g, passed in positive_results.items() if passed}
        baseline_tp = {g for g, passed in baseline_results.items() if passed}
        for pairs in rating_groups.values():
            ratings.append(float(np.mean([p[0] for p in pairs])))
            quality.append(float(np.mean([p[1] for p in pairs])))
        independent = bool(positives and negatives) and all(o['case']['split']=='test' for o in observations)
        recall, fpr = len(tp)/max(1,len(positives)), len(fp)/max(1,len(negatives))
        br, bf = len(baseline_tp)/max(1,len(positives)), len(baseline_fp)/max(1,len(negatives))
        row = {'defect_count': len(positives), 'normal_count': len(negatives),
               'true_positive_count': len(tp), 'false_positive_count': len(fp),
               'known_negative_count': len(known_negatives),
               'cross_defect_false_positive_count': len(cross_fp),
               'cross_defect_false_positive_rate': len(cross_fp)/max(1,len(known_negatives)),
               'cross_defect_false_positive_ci95': wilson(len(cross_fp),len(known_negatives)),
               'recall': recall, 'false_positive_rate': fpr,
               'recall_ci95': wilson(len(tp),len(positives)),
               'false_positive_ci95': wilson(len(fp),len(negatives)),
               'baseline_recall': br, 'baseline_false_positive_rate': bf,
               'htm_gain': recall-fpr-(br-bf),
               'localization_mae_seconds': float(np.mean(errors)) if errors else None,
               'independent_test_groups': independent, 'subjective': subjective,
               'supported': (kind != 'masking' or all(o['review']['tracks'] for o in observations)),
               'independent_ratings': len(ratings), 'spearman': spearman(ratings, quality)}
        row['status'] = 'PASS' if eligible(row) else 'UNQUALIFIED'
        dimensions[kind] = row
    return dimensions


def benchmark(dataset_path, model, calibration, output, split='test'):
    if split not in ('test','development'):
        raise ValueError('benchmark split must be test or development')
    cases = partition(dataset_path, model, split)
    load_calibration(calibration, model)
    observations, evidence = [], [ref(dataset_path)]
    for c in cases:
        report = evaluate(c['audio']['path'], c['script']['path'], model, calibration,
                          c.get('alignment', {}).get('path'),
                          narration_track=c.get('narration_track', {}).get('path'),
                          mix_track=c.get('mix_track', {}).get('path'), subject_id=c['id'])
        if (report['audio']!=c['audio'] or report['script']!=c['script']
                or report['alignment']!=c.get('alignment')
                or report['tracks'].get('narration')!=c.get('narration_track')
                or report['tracks'].get('mix')!=c.get('mix_track')):
            raise ValueError('benchmark input changed after frozen split validation')
        evidence.extend([c['audio'], c['script']])
        if c.get('alignment'):
            evidence.append(c['alignment'])
        observations.append({'case': c, 'review': report})
    dimensions = summarize(observations)
    result = {'schema_version': 1, 'adapter': ref(Path(__file__)),
              'split': split,
              'model': identity(model), 'calibration': ref(calibration),
              'status': 'PASS' if all(r['status']=='PASS' for r in dimensions.values()) else 'UNQUALIFIED',
              'dimensions': dimensions, 'evidence': evidence, 'cases': observations,
              'scope': 'audio dimensions only; synthetic controls do not validate subjective quality'}
    write_new(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('train', 'calibrate', 'benchmark', 'evaluate'):
        p = sub.add_parser(name)
        p.add_argument('--output', required=True)
        if name != 'train':
            p.add_argument('--model', required=True)
        if name != 'evaluate':
            p.add_argument('--dataset', required=True)
        if name in ('benchmark', 'evaluate'):
            p.add_argument('--calibration', required=True)
        if name == 'train':
            p.add_argument('--build-manifest', required=True)
            p.add_argument('--epochs', type=int, default=3)
        if name == 'benchmark':
            p.add_argument('--split', choices=('test','development'), default='test')
        if name == 'evaluate':
            for arg in ('audio', 'script'):
                p.add_argument('--'+arg, required=True)
            for arg in ('alignment', 'qualified', 'narration-track', 'mix-track', 'subject-id'):
                p.add_argument('--'+arg)
    args = vars(parser.parse_args())
    command, output = args.pop('command'), args.pop('output')
    if command == 'train':
        result = train(args['dataset'], output, args['build_manifest'], args['epochs'])
    elif command == 'calibrate':
        result = calibrate(args['dataset'], args['model'], output)
    elif command == 'benchmark':
        result = benchmark(args['dataset'], args['model'], args['calibration'], output, args['split'])
    else:
        result = evaluate(**args)
        write_new(output, result)
    print(json.dumps({'command': command, 'output': output, 'status': result.get('status', 'COMPLETE')}))
    return {'REWORK': 2, 'UNQUALIFIED': 3}.get(result.get('status'), 0)


if __name__ == '__main__':
    raise SystemExit(main())
