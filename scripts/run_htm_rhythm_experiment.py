"""Run one predeclared rhythm candidate, with immutable stage receipts.

--resume verifies completed stages without rerunning the blind benchmark.
--replay explicitly recomputes a completed blind benchmark with frozen weights.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from mechanical_video import htm_audio_rhythm as r
from mechanical_video.htm_audio_features import ref, verify


def run(dataset, build, output, resume=False, replay=False):
    output=Path(output).resolve()
    binding=dict(dataset=ref(dataset),build=ref(build),implementation=r.implementation(),
                 driver=ref(__file__),epochs=3,config=r.CONFIG,
                 selection='One fixed architecture and seed; no tuning on calibration/test; all cases required')
    if output.exists():
        if not resume or json.loads((output/'experiment.json').read_text())!=binding:
            raise ValueError('existing experiment differs; preserve it and use a new directory')
    else:
        output.mkdir(parents=True);r.write(output/'experiment.json',binding)
    existing_files={name for name in ('model/manifest.json','development.json','calibration.json','benchmark.json')
                    if (output/name).exists()}
    cache=output/'features';model=output/'model';cal=output/'calibration.json'
    def receipt(name):
        value=ref(output/name);path=output/(name+'.receipt.json')
        if path.exists():
            if json.loads(path.read_text())!=value: raise ValueError('changed completed stage: '+name)
        else:
            if name in existing_files: raise ValueError('completed stage lacks receipt: '+name)
            r.write(path,value)
    if not model.exists():
        print('training fixed rhythm candidate',flush=True)
        r.train(dataset,model,build,3,cache)
    engine,manifest=r.RhythmEngine.load(model)
    receipt('model/manifest.json')
    diagnostic=output/'development.json'
    if not diagnostic.exists():
        print('development-only probability diagnosis (no model selection)',flush=True)
        rows=[]
        for c in r.partition(dataset,model,'development'):
            f=r.features(c,cache);p=r.predict(engine,manifest,f)
            rows.append(dict(id=c['id'],recording_id=c['recording_id'],coverage=f['coverage_fraction'],
                             transformation=c['provenance']['transformation'],
                             probabilities={m:{k:[float(x) for x in np.quantile([v for v in p[m][k] if v is not None],[0,.5,1])]
                                                  if any(v is not None for v in p[m][k]) else [] for k in r.KINDS}
                                            for m in r.METHODS}))
        r.write(diagnostic,dict(model=ref(model/'manifest.json'),cases=rows,
                               scope='Development only; no threshold/model selection or test qualification'))
    receipt('development.json')
    print('calibration replay/freeze',flush=True)
    if cal.exists():
        if json.loads(cal.read_text())!=r.calibrate(dataset,model,None,cache):
            raise ValueError('completed calibration differs from replay')
    else: r.calibrate(dataset,model,cal,cache)
    receipt('calibration.json')
    target=output/'benchmark.json'
    if target.exists() and not replay:
        receipt('benchmark.json')
        lock=json.loads(target.with_suffix('.lock.json').read_text())
        for key in ('dataset','model','calibration'):
            verify(lock[key])
        for item in lock['implementation']: verify(item)
        result=json.loads(target.read_text())
        print('reused completed benchmark without new blind inference',flush=True)
    else:
        print('frozen blind test'+(' replay' if replay else ''),flush=True)
        result=r.benchmark(dataset,model,cal,target,cache=cache)
        receipt('benchmark.json')
    summary=dict(status=result['status'],dimensions=result['dimensions'],benchmark=ref(target),
                 production_enabled=False,scope='Controlled injection experiment; no complete listening acceptance')
    path=output/'summary.json'
    if path.exists():
        if json.loads(path.read_text())!=summary: raise ValueError('summary differs')
    else: r.write(path,summary)
    for key in ('dataset','build','driver'): verify(binding[key])
    for item in binding['implementation']: verify(item)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('dataset','build','output'): p.add_argument('--'+key,required=True)
    p.add_argument('--resume',action='store_true');p.add_argument('--replay',action='store_true')
    a=p.parse_args();run(a.dataset,a.build,a.output,a.resume,a.replay)
