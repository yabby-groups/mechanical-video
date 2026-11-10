"""Frozen SpatialPooler/TemporalMemory/classifier pipeline using official bindings."""
import json
from pathlib import Path
import platform
import sys

import numpy as np

from .htm_audio_features import FEATURES, VERSION, encode, ref, verify, sha

SOURCE_REVISION = '0cab77fa638925e0c84a1b2aa6c7cc1258cb66f1'
KINDS = ('normal', 'omission', 'repetition', 'mispronunciation', 'clipping', 'noise',
         'pause', 'splice', 'pace', 'masking', 'naturalness', 'expression')
DIMENSIONS = KINDS[1:]
CLASSIFIER_REPRESENTATION = 'tm_cells+input_sdr+columns+raw_anomaly_v2'


def runtime():
    import htm.bindings.algorithms as algorithms
    import htm.bindings.sdr as sdr
    return {'python': sys.version, 'platform': platform.platform(), 'numpy': np.__version__,
            'bindings': [ref(algorithms.__file__), ref(sdr.__file__)],
            'implementation': [ref(Path(__file__)), ref(Path(__file__).with_name('htm_audio_features.py'))]}


def runtime_identity(value):
    # Paths may change on relocation; bytes and interpreter/ABI must match.
    return {**value, 'bindings': [v['sha256'] for v in value['bindings']],
            'implementation': [v['sha256'] for v in value['implementation']]}


class Engine:
    def __init__(self):
        from htm.bindings.algorithms import SpatialPooler, TemporalMemory, Classifier
        from htm.bindings.sdr import SDR
        self.input = SDR(len(FEATURES)*64)
        self.columns = SDR(512)
        self.classification = SDR(4096+len(FEATURES)*64+512+64)
        self.sp = SpatialPooler(inputDimensions=[len(FEATURES)*64], columnDimensions=[512],
                                potentialRadius=len(FEATURES)*64, potentialPct=.8,
                                globalInhibition=True, localAreaDensity=.04,
                                synPermInactiveDec=.008, synPermActiveInc=.04,
                                synPermConnected=.1, seed=42)
        self.tm = TemporalMemory(columnDimensions=[512], cellsPerColumn=8,
                                 activationThreshold=8, minThreshold=5,
                                 maxNewSynapseCount=16, seed=42)
        self.classifiers = {k: Classifier(alpha=.01) for k in DIMENSIONS}

    def sequence(self, features, learn=False, labels=None, class_repeats=None, supervised_kinds=None):
        """Reset each recording; classifier training never changes SP/TM."""
        self.tm.reset()
        results = []
        for index, values in enumerate(features):
            self.input.sparse = encode(values)
            self.sp.compute(self.input, learn, self.columns)
            self.tm.compute(self.columns, learn=learn)
            cells = self.tm.getActiveCells()
            # Preserve acoustic evidence outside the normal SP vocabulary while
            # retaining learned HTM context. Novelty is a supervised input, never
            # a direct quality score or an automatically passing anomaly value.
            anomaly_bucket = min(59, max(0, round(float(self.tm.anomaly)*59)))
            self.classification.sparse = np.concatenate([
                cells.sparse, self.input.sparse+4096,
                self.columns.sparse+4096+len(FEATURES)*64,
                np.arange(anomaly_bucket, anomaly_bucket+5, dtype=np.uint32)+4096+len(FEATURES)*64+512])
            probabilities = {}
            for kind, classifier in self.classifiers.items():
                if labels is not None and (supervised_kinds is None or kind in supervised_kinds):
                    positive = kind in labels[index]
                    repeats = (class_repeats or {}).get(kind, 1) if positive else 1
                    for _ in range(repeats):
                        classifier.learn(self.classification, int(positive))
                distribution = classifier.infer(self.classification)
                probabilities[kind] = float(distribution[1]) if len(distribution)>1 else 0.
            results.append({'anomaly': float(self.tm.anomaly), 'probabilities': probabilities})
        return results

    def save(self, directory):
        directory = Path(directory)
        self.tm.reset()
        for name, obj in [('sp', self.sp), ('tm', self.tm), *self.classifiers.items()]:
            obj.saveToFile(str(directory/(name+'.bin')), 'BINARY')

    def sequence_set(self, features, learn=False, case=None, class_repeats=None):
        results = {}
        for name, values in [('frames', features), *features.get('sequences', {}).items()]:
            labels = frame_labels(case, values) if case is not None else None
            supervised = supervised_dimensions(case) if case is not None else None
            results[name] = self.sequence(values['features'], learn=learn, labels=labels, class_repeats=class_repeats, supervised_kinds=supervised)
        return results

    @classmethod
    def load(cls, directory):
        directory = Path(directory)
        manifest = json.loads((directory/'manifest.json').read_text())
        if manifest.get('classifier_representation') != CLASSIFIER_REPRESENTATION:
            raise ValueError('unsupported classifier representation; retrain a new checkpoint')
        if manifest['feature_version'] != VERSION or manifest['source_revision'] != SOURCE_REVISION:
            raise ValueError('unsupported feature/source version')
        if runtime_identity(manifest['runtime']) != runtime_identity(runtime()):
            raise ValueError('runtime or adapter differs from frozen training build')
        required = {'sp.bin', 'tm.bin'} | {kind+'.bin' for kind in DIMENSIONS}
        if set(manifest['files']) != required:
            raise ValueError('checkpoint manifest must fingerprint every required component exactly')
        for name, digest in manifest['files'].items():
            if sha(directory/name) != digest:
                raise ValueError('checkpoint fingerprint mismatch')
        if manifest.get('normal_frames', 0) < 100 or manifest.get('normal_recordings', 0) < 2:
            raise ValueError('cold start: insufficient normal training data')
        engine = cls()
        for name, obj in [('sp', engine.sp), ('tm', engine.tm), *engine.classifiers.items()]:
            obj.loadFromFile(str(directory/(name+'.bin')), 'BINARY')
        return engine, manifest


def load_dataset(path):
    """Enforce split disjointness by recording, speaker, normalized frozen text.

    Defect copies inherit source recording_id. A dishonest provenance manifest
    cannot be authenticated by this software; source/license refs are retained.
    """
    from .speech_alignment import normalize
    dataset = json.loads(Path(path).read_text())
    cases = dataset['cases']
    seen, ids = {}, set()
    for c in cases:
        if c['id'] in ids or c['split'] not in ('train', 'calibration', 'development', 'test'):
            raise ValueError('duplicate id or invalid split')
        ids.add(c['id'])
        for field in ('recording_id', 'speaker_id', 'license', 'provenance'):
            if not c.get(field):
                raise ValueError('missing corpus provenance: ' + field)
        for name in ('audio', 'script'):
            verify(c[name])
        if c.get('alignment'):
            verify(c['alignment'])
        for key in ('narration_track', 'mix_track'):
            if c.get(key):
                verify(c[key])
        keys = [('audio_sha256', c['audio']['sha256']), ('recording', c['recording_id']), ('speaker', c['speaker_id']),
                ('text', normalize(Path(c['script']['path']).read_text()))]
        if not keys[-1][1]:
            raise ValueError('empty frozen narration')
        for key in keys:
            if key in seen and seen[key] != c['split']:
                raise ValueError('group leakage across partitions: ' + str(key))
            seen[key] = c['split']
        labels = c.get('labels', [])
        negatives=c.get('negative_kinds', [])
        if (not isinstance(negatives,list) or not set(negatives)<=set(DIMENSIONS)
                or set(negatives)&{l['kind'] for l in labels}):
            raise ValueError('invalid or contradictory negative dimension labels')
        for label in labels:
            if (label['kind'] not in DIMENSIONS or not np.isfinite([label['start'], label['end']]).all()
                    or not 0 <= label['start'] < label['end']):
                raise ValueError('invalid labeled defect')
        if not c.get('label_source') or not c.get('labeler'):
            raise ValueError('quality/defect labels require source and labeler')
        if any(l['kind'] in ('naturalness', 'expression') for l in labels):
            if (c['label_source'] != 'independent_rating' or c['labeler'] == c.get('producer')
                    or not c.get('producer')):
                raise ValueError('subjective dimensions require independent quality labels')
    return dataset


def features_for(case):
    from .htm_audio_features import extract
    result = extract(case['audio']['path'], case.get('alignment', {}).get('path'),
                     case.get('narration_track', {}).get('path'), case.get('mix_track', {}).get('path'))
    if (result['audio']!=case['audio'] or result['alignment']!=case.get('alignment')
            or result['tracks'].get('narration')!=case.get('narration_track')
            or result['tracks'].get('mix')!=case.get('mix_track')):
        raise ValueError('corpus input changed during feature extraction')
    if any(l['end'] > result['duration'] for l in case.get('labels', [])):
        raise ValueError('label exceeds decoded duration')
    return result


def acoustic_normal(case):
    required = {'clipping','noise','pause','splice','pace','masking'}
    return not case.get('labels') and required <= set(case.get('negative_kinds', []))


def supervised_dimensions(case):
    return set(case.get('negative_kinds', [])) | {l['kind'] for l in case.get('labels', [])}


def frame_labels(case, features):
    return [{l['kind'] for l in case.get('labels', []) if l['start'] < end and l['end'] > start}
            for start, end in features['intervals']]


def train(dataset_path, output, build_manifest, epochs=3):
    from .htm_audio_features import sha
    if type(epochs) is not int or not 1 <= epochs <= 100:
        raise ValueError('epochs must be 1..100')
    data = load_dataset(dataset_path)
    build = json.loads(Path(build_manifest).read_text())
    if build['source_revision'] != SOURCE_REVISION:
        raise ValueError('build is not from pinned source')
    current = runtime()
    if [b['sha256'] for b in build['bindings']] != [b['sha256'] for b in current['bindings']]:
        raise ValueError('build fingerprint differs from installed bindings')
    cases = [c for c in data['cases'] if c['split'] == 'train']
    normal = [c for c in cases if acoustic_normal(c)]
    if len({c['recording_id'] for c in normal}) < 2:
        raise ValueError('cold start: need at least two independent normal recordings')
    cached = [(c, features_for(c)) for c in cases]
    normal_frames = sum(len(f['features']) for c, f in cached if acoustic_normal(c))
    if normal_frames < 100:
        raise ValueError('cold start: fewer than 100 normal frames')
    engine = Engine()
    counts = {kind: [0, 0] for kind in DIMENSIONS}
    for case, f in cached:
        for values in [f, *f.get('sequences', {}).values()]:
            for labels in frame_labels(case, values):
                for kind in supervised_dimensions(case):
                    counts[kind][int(kind in labels)] += 1
    class_repeats = {kind: max(1, min(32, round(negative/max(1, positive))))
                     for kind, (negative, positive) in counts.items()}
    for _ in range(epochs):
        for case, f in cached:
            if acoustic_normal(case):
                engine.sequence_set(f, learn=True)
    for _ in range(epochs):
        for case, f in cached:
            engine.sequence_set(f, case=case, class_repeats=class_repeats)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    engine.save(output)
    manifest = {'schema_version': 2, 'source_revision': SOURCE_REVISION,
                'classifier_representation': CLASSIFIER_REPRESENTATION,
                'class_repeats': class_repeats,
                'feature_version': VERSION, 'runtime': current, 'build': ref(build_manifest),
                'normal_frames': normal_frames, 'normal_recordings': len({c['recording_id'] for c in normal}),
                'normal_examples': len(normal),
                'dataset': ref(dataset_path), 'training_cases': [c['id'] for c in cases],
                'training_groups': {key: sorted({c[key] for c in cases}) for key in ('recording_id', 'speaker_id')},
                'training_texts': sorted({sha(c['script']['path']) for c in cases}),
                'epochs': epochs, 'files': {p.name: sha(p) for p in output.glob('*.bin')}}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest
