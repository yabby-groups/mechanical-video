"""Small frozen waveform feasibility trial; controlled injections are not listening labels."""
import json
from pathlib import Path
import numpy as np
from mechanical_video.htm_waveform import Config, Engine, decode, review, sha

import argparse
p = argparse.ArgumentParser()
p.add_argument('--output', required=True)
args = p.parse_args()
root = Path(args.output)
root.mkdir(exist_ok=False)
data = json.load(open('reports/htm-audio-aishell-v1/dataset.json'))['cases']
def originals(split):
    return [c for c in data if c['split']==split and '/originals/' in c['audio']['path'] and not c.get('labels')]
train = originals('train')[:2]
held = originals('test')[:2]
cfg, _ = decode(train[0]['audio']['path'])
e = Engine(cfg)
e.fit([decode(case['audio']['path'])[1] for case in train],3)
e.save(root/'model',[c['audio'] for c in train])
results=[]
for number,case in enumerate(held):
    c,x=decode(case['audio']['path']); assert c==cfg
    a,b=len(x)//3,len(x)//3+cfg.rate//4
    t=np.arange(len(x))[:,None]/cfg.rate
    versions={'normal':x.copy(),'reasonable_pause':np.concatenate([x[:a],np.zeros((cfg.rate//5,cfg.channels)),x[a:]]),
        'bgm_change':np.clip(x+.015*np.sin(2*np.pi*220*t)*(t>len(x)/cfg.rate/2),-1,1),
        'dropout':x.copy(),'clipping':x.copy(),'repetition':x.copy(),'splice':x.copy(),'gain_jump':x.copy()}
    versions['dropout'][a:b]=0
    versions['clipping'][a:b]=np.clip(x[a:b]*30,-1,1)
    versions['repetition'][a:b]=np.resize(x[a:a+cfg.rate//50],(b-a,cfg.channels))
    versions['splice'][a:b]=x[a:b][::-1]
    versions['gain_jump'][a:b]=np.clip(x[a:b]*4,-1,1)
    for name,samples in versions.items():
        out=root/f'{number}-{name}'
        r=review(e,samples,dict(original=case['audio'],variant=name,synthetic_intervention=True),out,.8)
        timeline=json.loads((out/'timeline.json').read_text())
        focus=[v for v in timeline if v['start_sample']<b and v['end_sample']>a]
        results.append(dict(recording=number,variant=name,source=case['audio'],
            intervention=[a/cfg.rate,b/cfg.rate] if name not in ('normal','reasonable_pause','bgm_change') else None,
            mean_anomaly=float(np.mean([v['anomaly'] for v in timeline[1:]])),
            alarm_fraction=float(np.mean([v['anomaly']>=.8 for v in timeline[1:]])),
            intervention_alarm_fraction=float(np.mean([v['anomaly']>=.8 for v in focus])),
            report=str(out/'report.json')))
(root/'summary.json').write_text(json.dumps(dict(train=[c['audio'] for c in train],results=results,
    interpretation='Controlled variants and original-as-repaired pairs; no independent perceptual labels.'),indent=2)+'\n')
print(json.dumps(results,indent=2))
