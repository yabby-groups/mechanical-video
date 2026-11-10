"""Make new grouped rhythm controls, preserving every source and failed case.

The inspected pace corpus supplies train and development only. New speakers
supply calibration/test. Synthetic speed changes are not quality ratings.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from mechanical_video.htm_audio_features import ref
from mechanical_video.htm_audio_model import load_dataset
from mechanical_video.htm_audio_review import write_new
from scripts.prepare_htm_aishell import prepare, read, save


def tempo(audio, output, speed):
    subprocess.run(['ffmpeg','-v','error','-i',str(audio),'-af','atempo='+str(speed),str(output)],check=True)
    return read(Path(output).read_bytes())


def prepare_rhythm(source, previous, output, plan, vocabulary, excludes=()):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    old=load_dataset(previous)
    if any(split not in ('calibration','test') for split,count in plan.values()):
        raise ValueError('fresh speaker plan must contain only calibration/test')
    old_speakers={c['speaker_id'] for c in old['cases']}
    if old_speakers & set(plan): raise ValueError('new holdout speakers already observed')
    fresh=prepare(source,output/'fresh',plan,[previous,*excludes],vocabulary)
    cases=load_dataset(fresh)['cases']
    # Prior training retained; prior calibration is now explicitly development.
    # Previously inspected test recordings are excluded, never silently reused.
    for c in old['cases']:
        if c['split'] not in ('train','calibration'): continue
        item=copy.deepcopy(c)
        item['split']='train' if c['split']=='train' else 'development'
        item.pop('alignment',None)
        cases.append(item)
    for c in cases:
        for l in c.get('labels',[]):
            l['subtype']='global_fast' if l['kind']=='pace' else l['kind']
    derived=output/'derived';derived.mkdir()
    for c in list(cases):
        if c['provenance']['transformation']!='normal': continue
        x,rate=read(Path(c['audio']['path']).read_bytes())
        seed=int(hashlib.sha256(('rhythm-v1:'+c['recording_id']).encode()).hexdigest()[:8],16)
        rng=np.random.default_rng(seed)
        for subtype in ('slow','local_fast','normal_local_tempo'):
            item=copy.deepcopy(c);item['id']=c['recording_id']+'-'+subtype
            audio=derived/(item['id']+'.wav')
            speed=float(rng.uniform(.65,.8) if subtype=='slow' else
                        rng.uniform(1.65,1.9) if subtype=='local_fast' else rng.uniform(.95,1.05))
            if subtype=='slow':
                y,_=tempo(c['audio']['path'],audio,speed);start,end=0.,len(y)/rate
            else:
                # Fixed source-relative segment, not selected using predictions.
                left,right=round(len(x)*.2),round(len(x)*.8)
                segment=derived/(item['id']+'-source-segment.wav');save(segment,x[left:right],rate)
                changed=derived/(item['id']+'-tempo-segment.wav');part,_=tempo(segment,changed,speed)
                y=np.r_[x[:left],part,x[right:]];save(audio,y,rate)
                start,end=left/rate,(left+len(part))/rate
            item.update(audio=ref(audio),narration_track=ref(audio),mix_track=ref(audio),
                        labels=[] if subtype.startswith('normal') else [dict(kind='pace',subtype=subtype,start=start,end=end)])
            item['provenance']={**item['provenance'],'transformation':subtype,'speed':speed,
                                'seed':'SHA256(rhythm-v1:recording id)'}
            if not subtype.startswith('normal'):
                # Slow tempo can lengthen real pauses: do not invent a negative.
                item['negative_kinds']=['clipping','noise','masking']+(['pause'] if subtype=='local_fast' else [])
            cases.append(item)
    value=dict(schema_version=2,cases=cases,source=ref(fresh),previous=ref(previous),
               selection_plan=plan,scope='Controlled pace/pause perturbations, not contextual quality labels',
               split_policy='Prior train retained; prior calibration becomes development; prior test excluded; fresh calibration/test speakers and texts',
               transformation_policy=dict(global_fast=[1.65,1.9],slow=[.65,.8],local_fast=[1.65,1.9],
                                          local_fraction=[.2,.8],normal_local_tempo=[.95,1.05]))
    write_new(output/'dataset.json',value);load_dataset(output/'dataset.json')
    return output/'dataset.json'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','previous','output','plan','vocabulary'): p.add_argument('--'+name,required=True)
    p.add_argument('--exclude-dataset',action='append',default=[])
    a=p.parse_args()
    print(prepare_rhythm(a.source,a.previous,a.output,json.loads(Path(a.plan).read_text()),a.vocabulary,a.exclude_dataset))
