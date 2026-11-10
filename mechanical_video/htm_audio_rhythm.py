"""Experimental, separately frozen rhythm branch and matched temporal ablations.

Only controlled changes can qualify. Never confers pronunciation, expression,
continuous audiovisual or production listening acceptance.
"""
import json
import shutil
from pathlib import Path

import numpy as np

from .htm_audio_features import extract, ref, verify, sha
from .htm_audio_model import load_dataset, runtime, runtime_identity, SOURCE_REVISION
from .speech_alignment import normalize

VERSION = 'rhythm-window-v1'
KINDS = ('pace', 'pause')
METHODS = ('rules', 'no_tm', 'htm')
CONFIG = dict(window_seconds=2., hop_seconds=.5, minimum_alignment_confidence=.5,
              window_alignment_confidence=.35, localization_iou=.5, seed=42)
FEATURES = ('character_rate', 'extent_rate', 'speech_fraction', 'mean_gap', 'max_gap',
            'character_duration', 'rate_delta', 'pitch_mean', 'pitch_std',
            'energy_mean', 'energy_delta', 'voiced_fraction')
BOUNDS = ((0, 16), (0, 16), (0, 1), (0, 3), (0, 4), (0, .5),
          (-12, 12), (0, 500), (0, 200), (-100, 0), (0, 30), (0, 1))


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def implementation():
    return [ref(__file__), ref(Path(__file__).with_name('htm_audio_features.py')),
            ref(Path(__file__).with_name('htm_audio_model.py'))]


def encode(values):
    if len(values) != len(BOUNDS) or not np.isfinite(values).all():
        raise ValueError('invalid rhythm vector')
    buckets = [round(float(np.clip((v-lo)/(hi-lo), 0, 1))*59) for v, (lo, hi) in zip(values, BOUNDS)]
    return np.asarray([i*64+b+j for i, b in enumerate(buckets) for j in range(5)], dtype=np.uint32)


def window_features(f, chars):
    """CTC supports are timing evidence, not phoneme durations or pronunciation."""
    duration = f['duration']
    starts = list(np.arange(0, max(0., duration-2.)+1e-8, .5)) or [0.]
    if duration > 2 and duration-(starts[-1]+2) > 1e-8:
        starts.append(duration-2.)
    windows = [[float(s), float(min(duration, s+2))] for s in starts]
    centers = [(s+e)/2 for s, e in windows]
    edges = [0.] + [(a+b)/2 for a,b in zip(centers, centers[1:])] + [duration]
    intervals = [[a,b] for a,b in zip(edges, edges[1:])]
    confidence = float(np.mean([c['confidence'] for c in chars])) if chars else 0.
    rows, valid = [], []
    previous_rate = None
    all_gaps = [(a['end'], b['start']) for a,b in zip(chars, chars[1:])]
    t, frames = np.asarray(f['intervals']), np.asarray(f['features'])
    for start,end in windows:
        selected = [c for c in chars if start <= (c['start']+c['end'])/2 < end]
        local = frames[(t[:,0]<end)&(t[:,1]>start)]
        gaps = [min(b,end)-max(a,start) for a,b in all_gaps if a<end and b>start]
        rate = len(selected)/(end-start)
        extent = len(selected)/max(.1, selected[-1]['end']-selected[0]['start']) if len(selected)>1 else rate
        pitch = local[local[:,6]>0,6]
        rows.append([rate, extent, float(np.mean(local[:,8]<.5)),
                     float(np.mean(gaps)) if gaps else 0., max(gaps, default=0.),
                     float(np.mean([c['end']-c['start'] for c in selected])) if selected else 0.,
                     0. if previous_rate is None else rate-previous_rate,
                     float(np.mean(pitch)) if len(pitch) else 0., float(np.std(pitch)) if len(pitch) else 0.,
                     float(local[:,0].mean()), float(np.abs(local[:,9]).mean()), float(np.mean(local[:,6]>0))])
        # An interior silent window can be supported by measured neighbors.
        neighbors = selected or [c for c in chars if c['end']<=start][-1:] + [c for c in chars if c['start']>=end][:1]
        valid.append(bool(confidence>=CONFIG['minimum_alignment_confidence'] and neighbors
                          and np.mean([c['confidence'] for c in neighbors])>=CONFIG['window_alignment_confidence']))
        previous_rate = rate
    return dict(features=rows, intervals=intervals, windows=windows, valid=valid,
                alignment_confidence=confidence, duration=duration,
                coverage_fraction=sum((b-a) for (a,b),v in zip(intervals,valid) if v)/duration)


def features(case, cache=None):
    for key in ('audio','script'):
        verify(case[key])
    alignment = case.get('alignment')
    if not alignment:
        return dict(features=[], intervals=[], windows=[], valid=[], duration=0., coverage_fraction=0.,
                    alignment_confidence=0., uncovered='missing measured alignment')
    verify(alignment)
    inputs = {k:case[k] for k in ('audio','script','alignment')}
    binding = dict(inputs=inputs, implementation=implementation(), config=CONFIG, version=VERSION,
                   numpy=np.__version__, decoders=[ref(shutil.which(tool)) for tool in ('ffmpeg','ffprobe')])
    import hashlib
    key = hashlib.sha256(json.dumps(binding,sort_keys=True).encode()).hexdigest()
    target = Path(cache)/(key+'.json') if cache else None
    if target and target.exists():
        saved = json.loads(target.read_text())
        verify(json.loads(target.with_suffix('.receipt.json').read_text()))
        if saved['binding'] != binding:
            raise ValueError('feature cache binding differs')
        return saved['result']
    data = json.loads(Path(alignment['path']).read_text())
    if normalize(data['transcript']) != normalize(Path(case['script']['path']).read_text()):
        raise ValueError('alignment differs from frozen narration')
    f = extract(case['audio']['path'], alignment['path'])
    result = window_features(f, data['characters'])
    result['audio'] = f['audio']
    result['alignment'] = f['alignment']
    result['raw_amplitude'] = f['raw_amplitude']
    result['sentences'] = []
    for start, end in f['sequences'].get('sentences', {}).get('intervals', []):
        units = [c for c in data['characters'] if c['start']>=start and c['end']<=end]
        result['sentences'].append(dict(start=float(start), end=float(end),
            text=''.join(c['text'] for c in units), measured_character_rate=len(units)/(end-start),
            confidence=float(np.mean([c['confidence'] for c in units]))))
    if result['coverage_fraction'] < 1-1e-9:
        result['uncovered'] = 'insufficient measured character confidence'
    for value in inputs.values():
        verify(value)
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        write(target, dict(binding=binding, result=result))
        write(target.with_suffix('.receipt.json'), ref(target))
    return result


def labels(case, interval, kind):
    start,end = interval
    relevant = [l for l in case.get('labels',[]) if l['kind']==kind]
    overlap = sum(max(0.,min(end,l['end'])-max(start,l['start'])) for l in relevant)
    if overlap >= .5*(end-start):
        return 1
    if overlap > 0:
        return None  # boundary ambiguity must not become a normal label
    if relevant or kind in case.get('negative_kinds',[]):
        return 0
    return None


class RhythmEngine:
    def __init__(self):
        from htm.bindings.algorithms import SpatialPooler, TemporalMemory, Classifier
        from htm.bindings.sdr import SDR
        size = len(FEATURES)*64
        self.input, self.columns, self.pattern = SDR(size), SDR(512), SDR(4096+size+64)
        self.sp = SpatialPooler(inputDimensions=[size],columnDimensions=[512],potentialRadius=size,
            potentialPct=.8,globalInhibition=True,localAreaDensity=.04,
            synPermInactiveDec=.008,synPermActiveInc=.04,synPermConnected=.1,seed=42)
        self.tm = TemporalMemory(columnDimensions=[512],cellsPerColumn=8,
            activationThreshold=8,minThreshold=5,maxNewSynapseCount=16,seed=42)
        self.classifiers = {m:{k:Classifier(alpha=.01) for k in KINDS} for m in ('no_tm','htm')}

    def components(self):
        return {'sp':self.sp,'tm':self.tm,**{m+'-'+k:c for m,cs in self.classifiers.items() for k,c in cs.items()}}

    def sequence(self, f, learn=False, case=None):
        if not learn and case is None and getattr(self, '_frozen_directory', None):
            for name, obj in self.components().items():
                if sha(self._frozen_directory/(name+'.bin')) != self._frozen_files[name+'.bin']:
                    raise ValueError('frozen checkpoint changed between recordings')
                obj.loadFromFile(str(self._frozen_directory/(name+'.bin')), 'BINARY')
        self.tm.reset()
        result = {m:{k:[] for k in KINDS} for m in ('no_tm','htm')}
        anomalies = []
        for i, values in enumerate(f['features']):
            if not f['valid'][i]:
                self.tm.reset()
                anomalies.append(None)
                for m in result:
                    for k in KINDS: result[m][k].append(None)
                continue
            self.input.sparse = encode(values)
            self.sp.compute(self.input,learn,self.columns)
            self.tm.compute(self.columns,learn=learn)
            anomaly = float(self.tm.anomaly)
            bucket = round(anomaly*59)
            self.pattern.sparse = np.concatenate([self.tm.getActiveCells().sparse,
                self.input.sparse+4096, np.arange(bucket,bucket+5,dtype=np.uint32)+4096+len(FEATURES)*64])
            anomalies.append(anomaly)
            for m, pattern in (('no_tm',self.input),('htm',self.pattern)):
                for kind, classifier in self.classifiers[m].items():
                    label = labels(case,f['intervals'][i],kind) if case is not None else None
                    if label is not None:
                        classifier.learn(pattern,label)
                    distribution = classifier.infer(pattern)
                    result[m][kind].append(float(distribution[1]) if len(distribution)>1 else 0.)
        result['anomaly'] = anomalies
        return result

    def save(self, directory):
        self.tm.reset()
        for name,obj in self.components().items(): obj.saveToFile(str(Path(directory)/(name+'.bin')),'BINARY')

    @classmethod
    def load(cls, directory):
        directory=Path(directory)
        manifest=json.loads((directory/'manifest.json').read_text())
        if (manifest['version']!=VERSION or manifest['config']!=CONFIG or manifest['features']!=list(FEATURES)
                or manifest['source_revision']!=SOURCE_REVISION):
            raise ValueError('unsupported rhythm checkpoint')
        if (manifest['implementation']!=implementation() or
                runtime_identity(manifest['runtime'])!=runtime_identity(runtime())):
            raise ValueError('rhythm build differs from frozen checkpoint')
        if manifest['normal_recordings']<2 or manifest['normal_windows']<20:
            raise ValueError('cold start rhythm checkpoint')
        engine=cls()
        if set(manifest['files'])!={n+'.bin' for n in engine.components()}:
            raise ValueError('incomplete rhythm checkpoint')
        for name,obj in engine.components().items():
            if sha(directory/(name+'.bin'))!=manifest['files'][name+'.bin']:
                raise ValueError('rhythm checkpoint fingerprint mismatch')
            obj.loadFromFile(str(directory/(name+'.bin')),'BINARY')
        engine._frozen_directory = directory
        engine._frozen_files = manifest['files']
        return engine,manifest


def is_normal(c):
    return not c.get('labels') and set(KINDS)<=set(c.get('negative_kinds',[]))


def train(dataset_path, output, build_manifest, epochs=3, cache=None):
    if type(epochs) is not int or not 1<=epochs<=100:
        raise ValueError('epochs must be 1..100')
    data=load_dataset(dataset_path)
    build=json.loads(Path(build_manifest).read_text())
    current=runtime()
    if build['source_revision']!=SOURCE_REVISION or [b['sha256'] for b in build['bindings']]!=[b['sha256'] for b in current['bindings']]:
        raise ValueError('unverified native HTM build')
    cases=[c for c in data['cases'] if c['split']=='train']
    cached=[(c,features(c,cache)) for c in cases]
    normals=[(c,f) for c,f in cached if is_normal(c)]
    groups={c['recording_id'] for c,f in normals if any(f['valid'])}
    normal_windows=sum(sum(f['valid']) for c,f in normals)
    if len(groups)<2 or normal_windows<20:
        raise ValueError('cold start: insufficient normal rhythm data')
    engine=RhythmEngine()
    for _ in range(epochs):
        for c,f in normals: engine.sequence(f,learn=True)
    # Interleave labels deterministically; no positive replay or duplicated levels.
    ordered=sorted(cached,key=lambda item:__import__('hashlib').sha256(item[0]['id'].encode()).hexdigest())
    for _ in range(epochs):
        for c,f in ordered: engine.sequence(f,case=c)
    rates=[v[0] for c,f in normals for v,valid in zip(f['features'],f['valid']) if valid and v[2]>.25]
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    engine.save(output)
    manifest=dict(version=VERSION,source_revision=SOURCE_REVISION,config=CONFIG,features=FEATURES,implementation=implementation(),
        runtime=current,build=ref(build_manifest),dataset=ref(dataset_path),epochs=epochs,
        normal_recordings=len(groups),normal_windows=normal_windows,
        training_cases=[c['id'] for c in cases],
        rule_rate_bounds=[float(np.quantile(rates,.05)),float(np.quantile(rates,.95))],
        files={p.name:sha(p) for p in output.glob('*.bin')},
        scope='Controlled rhythm changes only; no contextual appropriateness labels')
    write(output/'manifest.json',manifest)
    return manifest


def partition(dataset, model, split):
    data=load_dataset(dataset)
    manifest=json.loads((Path(model)/'manifest.json').read_text())
    if ref(dataset)!=manifest['dataset']: raise ValueError('dataset differs from frozen training partition')
    cases=[c for c in data['cases'] if c['split']==split]
    if not cases: raise ValueError('missing '+split+' partition')
    return cases


def predict(engine, manifest, f):
    result=engine.sequence(f)
    lo,hi=manifest['rule_rate_bounds']
    result['rules']={'pace':[], 'pause':[]}
    for v,valid in zip(f['features'],f['valid']):
        # Rate under a pause is not independently evidence of slow pronunciation.
        result['rules']['pace'].append(max(0.,lo-v[0],v[0]-hi) if valid and v[2]>.25 else (0. if valid else None))
        result['rules']['pause'].append(v[4] if valid else None)
    return result


def spans(values, intervals, threshold):
    if threshold is None: return []
    result=[]
    for score,(start,end) in zip(values,intervals):
        if score is not None and score>=threshold:
            if result and abs(result[-1][1]-start)<1e-8: result[-1][1]=end
            else: result.append([start,end])
    return result


def iou(a,b):
    overlap=max(0.,min(a[1],b[1])-max(a[0],b[0]))
    return overlap/(max(a[1],b[1])-min(a[0],b[0]))


def grouped(observations, method, kind, threshold, subtype=None):
    positive, normal, cross={}, {}, {}
    errors, overreach=[],[]
    covered=True
    for c,f,p in observations:
        relevant=[l for l in c.get('labels',[]) if l['kind']==kind]
        if subtype and relevant and not any(l.get('subtype',kind)==subtype for l in relevant): continue
        if not relevant and kind not in c.get('negative_kinds',[]): continue
        prediction=spans(p[method][kind],f['intervals'],threshold)
        coverage=f['coverage_fraction']>=1-1e-9
        covered=covered and coverage
        group=c['recording_id']
        if relevant:
            matches=[max(prediction,key=lambda s:iou(s,[l['start'],l['end']])) if prediction else None for l in relevant]
            hit=coverage and all(s is not None and iou(s,[l['start'],l['end']])>=.5 for s,l in zip(matches,relevant))
            positive[group]=positive.get(group,True) and hit
            for s,l in zip(matches,relevant):
                if s is not None:
                    errors.append([abs(s[0]-l['start']),abs(s[1]-l['end'])])
                    overreach.append(max(0.,l['start']-s[0])+max(0.,s[1]-l['end']))
        else:
            bucket=cross if c.get('labels') else normal
            # Missing coverage prevents qualification, not a fabricated false alarm.
            bucket[group]=bucket.get(group,False) or bool(prediction)
    return positive,normal,cross,covered,errors,overreach


def metric(groups):
    p,n,c=groups[:3]
    return sum(p.values())/max(1,len(p))-sum(n.values())/max(1,len(n))


def calibrate(dataset_path, model, output, cache=None):
    engine,manifest=RhythmEngine.load(model)
    cases=partition(dataset_path,model,'calibration')
    observations=[]
    for c in cases:
        f=features(c,cache); observations.append((c,f,predict(engine,manifest,f)))
    thresholds={m:{} for m in METHODS}
    for method in METHODS:
        for kind in KINDS:
            positive={c['recording_id'] for c in cases if any(l['kind']==kind for l in c.get('labels',[]))}
            negative={c['recording_id'] for c in cases if is_normal(c)}
            if min(len(positive),len(negative))<2: thresholds[method][kind]=None;continue
            values=[v for c,f,p in observations for v in p[method][kind] if v is not None]
            if not values: thresholds[method][kind]=None;continue
            candidates=sorted(set(float(v) for v in np.quantile(values,np.linspace(0,1,101))))
            candidates.append(float(np.nextafter(max(values),np.inf)))
            choices=[]
            for t in candidates:
                g=grouped(observations,method,kind,t)
                cross=sum(g[2].values())/max(1,len(g[2]))
                choices.append((metric(g)-cross,-sum(g[1].values()),t))
            thresholds[method][kind]=max(choices)[2]
    result=dict(version=VERSION,model=ref(Path(model)/'manifest.json'),dataset=ref(dataset_path),
        thresholds=thresholds,implementation=implementation(),learning=False,
        cases=[c['id'] for c in cases],scope='Calibration only; no qualification')
    if output: write(output,result)
    return result


def calibration(path, model):
    value=json.loads(Path(path).read_text())
    if value['model']!=ref(Path(model)/'manifest.json') or value['implementation']!=implementation():
        raise ValueError('calibration differs from frozen model/build')
    # Replay calibration rather than trusting a hand-edited threshold receipt.
    return value


def gain_interval(a,b):
    """Paired bootstrap of original recordings, preserving positive/negative pairing."""
    groups=sorted(set(a[0])|set(a[1])|set(b[0])|set(b[1]))
    if not groups or set(a[0])!=set(b[0]) or set(a[1])!=set(b[1]):
        return [None,None]
    rng=np.random.default_rng(42)
    draws=[]
    for _ in range(2000):
        sample=rng.choice(groups,len(groups),replace=True)
        pd=[int(a[0][g])-int(b[0][g]) for g in sample if g in a[0]]
        nd=[int(a[1][g])-int(b[1][g]) for g in sample if g in a[1]]
        if pd and nd: draws.append(float(np.mean(pd)-np.mean(nd)))
    return [float(v) for v in np.quantile(draws,[.025,.975])] if draws else [None,None]


def summarize(observations, thresholds, split):
    from .htm_audio_review import wilson
    result={}
    for kind in KINDS:
        subtypes=sorted({l.get('subtype',kind) for c,f,p in observations for l in c.get('labels',[]) if l['kind']==kind})
        for subtype in [None]+subtypes:
            groups={m:grouped(observations,m,kind,thresholds[m][kind],subtype) for m in METHODS}
            rows={}
            for m,(pos,neg,cross,covered,errors,over) in groups.items():
                r=sum(pos.values())/max(1,len(pos));fp=sum(neg.values())/max(1,len(neg));cf=sum(cross.values())/max(1,len(cross))
                rows[m]=dict(defect_count=len(pos),normal_count=len(neg),known_negative_count=len(cross),
                    true_positive_count=sum(pos.values()),false_positive_count=sum(neg.values()),
                    cross_defect_false_positive_count=sum(cross.values()),recall=r,false_positive_rate=fp,
                    cross_defect_false_positive_rate=cf,recall_ci95=wilson(sum(pos.values()),len(pos)),
                    false_positive_ci95=wilson(sum(neg.values()),len(neg)),
                    cross_defect_false_positive_ci95=wilson(sum(cross.values()),len(cross)),
                    complete_coverage=covered, onset_mae_seconds=float(np.mean([e[0] for e in errors])) if errors else None,
                    offset_mae_seconds=float(np.mean([e[1] for e in errors])) if errors else None,
                    mean_overreach_seconds=float(np.mean(over)) if over else None)
            gains={m:dict(point=metric(groups['htm'])-metric(groups[m]),ci95=gain_interval(groups['htm'],groups[m])) for m in ('rules','no_tm')}
            h=rows['htm']
            passed=(split=='test' and min(h['defect_count'],h['normal_count'],h['known_negative_count'])>=50
                and h['complete_coverage'] and h['recall']>=.95 and h['false_positive_rate']<=.05
                and h['cross_defect_false_positive_rate']<=.05
                and all(g['ci95'][0] is not None and g['ci95'][0]>0 and g['point']>0 for g in gains.values()))
            result[kind if subtype is None else kind+'/'+subtype]=dict(methods=rows,gain=gains,
                status='PASS' if passed else 'UNQUALIFIED',scope='controlled injection; not contextual quality')
    return result


def benchmark(dataset_path, model, calibration_path, output, split='test', cache=None):
    if split not in ('test','development'): raise ValueError('invalid benchmark partition')
    engine,manifest=RhythmEngine.load(model)
    cal=calibration(calibration_path,model)
    if cal != calibrate(dataset_path,model,None,cache):
        raise ValueError('calibration does not replay')
    cases=partition(dataset_path,model,split)
    output=Path(output)
    lock=output.with_suffix('.lock.json')
    binding=dict(model=ref(Path(model)/'manifest.json'),calibration=ref(calibration_path),dataset=ref(dataset_path),
        split=split,implementation=implementation(),cases=[c['id'] for c in cases])
    if lock.exists():
        if json.loads(lock.read_text())!=binding: raise ValueError('benchmark lock differs')
    else: write(lock,binding)
    observations=[]
    for c in cases:
        f=features(c,cache);observations.append((c,f,predict(engine,manifest,f)))
    for item in (binding['model'], binding['calibration'], binding['dataset'], *binding['implementation']):
        verify(item)
    dimensions=summarize(observations,cal['thresholds'],split)
    result=dict(version=VERSION,**binding,dimensions=dimensions,
        status='PASS' if all(v['status']=='PASS' for v in dimensions.values()) else 'UNQUALIFIED',
        observations=[dict(case=c,features=f,predictions=p) for c,f,p in observations],
        scope='Controlled rhythm benchmark only; no automatic production enablement')
    if output.exists():
        if json.loads(output.read_text())!=result: raise ValueError('frozen benchmark replay differs')
    else: write(output,result)
    return result


def evaluate(audio, script, model, calibration_path, alignment=None, cache=None):
    engine,manifest=RhythmEngine.load(model)
    cal=calibration(calibration_path,model)
    if cal!=calibrate(manifest['dataset']['path'],model,None,cache): raise ValueError('calibration does not replay')
    case=dict(audio=ref(audio),script=ref(script),alignment=ref(alignment) if alignment else None)
    f=features(case,cache)
    p=predict(engine,manifest,f)
    return dict(version=VERSION,adapter='htm_rhythm_experimental',status='UNQUALIFIED',
        inputs=case,model=ref(Path(model)/'manifest.json'),calibration=ref(calibration_path),
        coverage_fraction=f['coverage_fraction'],uncovered=f.get('uncovered'),
        dimensions={k:dict(status='UNQUALIFIED',candidates=spans(p['htm'][k],f['intervals'],cal['thresholds']['htm'][k])) for k in KINDS},
        covered_intervals=[t for t,v in zip(f['intervals'],f['valid']) if v],
        decision_intervals=f['intervals'], sentences=f.get('sentences',[]),
        raw_amplitude=f.get('raw_amplitude'), alignment_confidence=f['alignment_confidence'],
        unqualified_capabilities=['contextual_pace','pronunciation','naturalness','expression','continuous_av'],
        comparisons=p,actionable=False,automatic_generation=False,
        scope='Experimental rhythm candidates; no production qualification or pronunciation decisions')


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('train','calibrate','benchmark','evaluate'):
        p=sub.add_parser(name);p.add_argument('--output',required=True);p.add_argument('--cache')
        if name!='train': p.add_argument('--model',required=True)
        if name!='evaluate': p.add_argument('--dataset',required=True)
        if name in ('benchmark','evaluate'): p.add_argument('--calibration',required=True)
        if name=='train':
            p.add_argument('--build-manifest',required=True);p.add_argument('--epochs',type=int,default=3)
        if name=='benchmark': p.add_argument('--split',choices=('development','test'),default='test')
        if name=='evaluate':
            p.add_argument('--audio',required=True);p.add_argument('--script',required=True);p.add_argument('--alignment')
    a=parser.parse_args(argv)
    if a.command=='train': result=train(a.dataset,a.output,a.build_manifest,a.epochs,a.cache)
    elif a.command=='calibrate': result=calibrate(a.dataset,a.model,a.output,a.cache)
    elif a.command=='benchmark': result=benchmark(a.dataset,a.model,a.calibration,a.output,a.split,a.cache)
    else:
        result=evaluate(a.audio,a.script,a.model,a.calibration,a.alignment,a.cache);write(a.output,result)
    print(json.dumps(dict(command=a.command,output=a.output,status=result.get('status','COMPLETE'))))
    return 3 if result.get('status')=='UNQUALIFIED' else 0


if __name__=='__main__':
    raise SystemExit(main())
