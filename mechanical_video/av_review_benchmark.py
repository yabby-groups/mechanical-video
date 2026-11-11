"""Frozen-policy, source-disjoint controlled benchmark. Never production qualification."""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time
import numpy as np
from .av_technical_review import DEFAULT, KINDS, make_report, digest, policy_hash


def score_events(predicted,expected,minimum_iou=.3):
    candidates=[]
    for i,p in enumerate(predicted):
        for j,g in enumerate(expected):
            overlap=max(0.,min(p['end'],g['end'])-max(p['start'],g['start']))
            union=max(p['end'],g['end'])-min(p['start'],g['start'])
            if overlap and overlap/union>=minimum_iou:candidates.append((overlap/union,i,j))
    used_p=set();used_g=set();errors=[]
    for iou,i,j in sorted(candidates,reverse=True):
        if i in used_p or j in used_g:continue
        used_p.add(i);used_g.add(j)
        errors.append(dict(start=abs(predicted[i]['start']-expected[j]['start']),end=abs(predicted[i]['end']-expected[j]['end']),iou=iou))
    return dict(tp=len(used_p),fp=len(predicted)-len(used_p),fn=len(expected)-len(used_g),boundary_errors=errors)

def wilson(k,n):
    if not n:return None
    z=1.96;p=k/n;den=1+z*z/n
    middle=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0.,middle-half),min(1.,middle+half)]

def validate_manifest(manifest,root):
    groups={};hashes={};ids=set()
    for c in manifest['cases']:
        if c['id'] in ids:raise ValueError('duplicate case id')
        ids.add(c['id'])
        if c['split'] not in ('development','test'):raise ValueError('invalid split')
        for value,registry in [(c['family'],groups),(c['sha256'],hashes)]:
            if value in registry and registry[value]!=c['split']:raise ValueError('source/bytes leakage between splits')
            registry[value]=c['split']
        path=Path(root)/c['path']
        if digest(path)!=c['sha256']:raise ValueError('media fingerprint mismatch')
        for label in c['labels']:
            if label['kind'] not in KINDS or not 0<=label['start']<label['end']<=c['duration']+1e-6:raise ValueError('invalid label')
    if set(groups.values())!={'development','test'}:raise ValueError('both disjoint splits required')

def create_corpus(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    # Freeze the code and policy BEFORE creating or evaluating the held-out split.
    frozen=dict(policy=asdict(DEFAULT),policy_sha256=policy_hash(DEFAULT),implementation_sha256=digest(Path(__file__).with_name('av_technical_review.py')),
        evaluation=dict(event_match_iou=.3,minimum_recall=.9,minimum_precision=.9,maximum_clean_clip_false_alarm_rate=.05),
        domain='procedurally generated lossless short clips; labels from controlled construction, not real human-reviewed defects',created=time.time())
    (output/'frozen-policy.json').write_text(json.dumps(frozen,indent=2))
    cases=[];fps=30;duration=3.;n=90;rate=48000
    y,x=np.mgrid[:64,:96]
    for split,seeds in [('development',[101,102]),('test',[701,702,703,704])]:
        for seed in seeds:
            rng=np.random.default_rng(seed)
            rgb=[]
            for i in range(n):
                # Different phase/speed/palette families; never share a source across splits.
                phase=i*(2+seed%5)
                rgb.append(np.stack([45+(x*2+phase+seed)%150,40+(y*3+phase//2+seed)%160,45+((x+y)*2-phase+seed)%150],axis=-1).astype(np.uint8))
            rgb=np.array(rgb)
            t=np.arange(int(rate*duration))/rate
            tone=(.20*np.sin(2*np.pi*(200+seed%173)*t)+.08*np.sin(2*np.pi*(530+seed%199)*t)).astype('<f4')[:,None]
            # All interval times are fixed before evaluation and variants stay within their family.
            for variant in ('normal','black','freeze','flash','dropout','clipping','intended_black','intended_hold','natural_pause','normal_cut','bright_sine'):
                v=rgb.copy();audio=tone.copy();labels=[]
                if variant in ('black','intended_black'):
                    a,b=30,39;v[a:b]=0
                    if variant=='black':labels=[dict(kind='black',start=a/fps,end=b/fps)]
                elif variant in ('freeze','intended_hold'):
                    a,b=27,51;v[a:b]=v[a]
                    if variant=='freeze':labels=[dict(kind='freeze',start=a/fps,end=b/fps)]
                elif variant=='flash':
                    a,b=34,36;v[a:b]=255;labels=[dict(kind='flash',start=a/fps,end=b/fps)]
                elif variant in ('dropout','natural_pause'):
                    a,b=1.,1.24;lo,hi=round(a*rate),round(b*rate)
                    audio[lo:hi]=0
                    if variant=='dropout':labels=[dict(kind='dropout',start=a,end=b)]
                    else:
                        ramp=int(.12*rate);audio[lo-ramp:lo]*=np.linspace(1,0,ramp)[:,None];audio[hi:hi+ramp]*=np.linspace(0,1,ramp)[:,None]
                elif variant=='clipping':
                    a,b=.9,1.15;lo,hi=round(a*rate),round(b*rate)
                    audio[lo:hi]=np.clip(audio[lo:hi]*12,-1,1);labels=[dict(kind='clipping',start=a,end=b)]
                elif variant=='normal_cut':v[45:]=255-v[45:]
                elif variant=='bright_sine':audio=(.999*np.sin(2*np.pi*(440+seed%137)*t)).astype('<f4')[:,None]
                name=f'{split}-{seed}-{variant}';raw=output/(name+'.rgb');pcm=output/(name+'.f32');path=output/(name+'.mov')
                raw.write_bytes(v.tobytes());pcm.write_bytes(audio.tobytes())
                subprocess.run(['ffmpeg','-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size','96x64','-framerate','30','-i',str(raw),'-f','f32le','-ar',str(rate),'-ac','1','-i',str(pcm),'-map','0:v:0','-map','1:a:0','-c:v','qtrle','-c:a','pcm_f32le',str(path)],check=True)
                raw.unlink();pcm.unlink()  # Only this generator's disposable inputs; encoded evidence retained.
                cases.append(dict(id=name,path=path.name,sha256=digest(path),family=f'procedural-{seed}',split=split,variant=variant,duration=duration,labels=labels,
                    normal_control=not labels,label_provenance='construction schedule; intended controls share a physical pattern with defects'))
    manifest=dict(schema_version=1,synthetic=True,policy=frozen,cases=cases)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest

def evaluate_corpus(root):
    root=Path(root);manifest=json.loads((root/'manifest.json').read_text());validate_manifest(manifest,root)
    frozen=manifest['policy']
    if frozen['policy_sha256']!=policy_hash(DEFAULT) or frozen['implementation_sha256']!=digest(Path(__file__).with_name('av_technical_review.py')):raise ValueError('policy/code changed after freezing; create a new benchmark')
    result_dir=root/'results';result_dir.mkdir(exist_ok=False)
    evaluated=[]
    for c in manifest['cases']:
        report=make_report(root/c['path'])
        assert report['coverage']['video_frames']==90 and report['coverage']['audio_samples']==144000
        (result_dir/(c['id']+'.json')).write_text(json.dumps(report,ensure_ascii=False))
        evaluated.append(dict(case=c,predictions=report['findings']))
    metrics={}
    for split in ('development','test'):
        cohort=[r for r in evaluated if r['case']['split']==split]
        metrics[split]={}
        for kind in KINDS:
            tp=fp=fn=normal_fp=0;errors=[]
            normal=[r for r in cohort if r['case']['normal_control']]
            for r in cohort:
                preds=[f for f in r['predictions'] if f['kind']==kind];labels=[g for g in r['case']['labels'] if g['kind']==kind]
                score=score_events(preds,labels)
                tp+=score['tp'];fp+=score['fp'];fn+=score['fn'];errors.extend(score['boundary_errors'])
                if r['case']['normal_control'] and preds:normal_fp+=1
            precision=tp/(tp+fp) if tp+fp else None;recall=tp/(tp+fn) if tp+fn else None
            clean_seconds=sum(r['case']['duration'] for r in normal)
            clean_events=sum(sum(f['kind']==kind for f in r['predictions']) for r in normal)
            passed=bool(precision is not None and precision>=.9 and recall is not None and recall>=.9 and normal_fp/len(normal)<=.05)
            metrics[split][kind]=dict(tp=tp,fp=fp,fn=fn,precision=precision,recall=recall,miss_rate=fn/(tp+fn) if tp+fn else None,
                recall_95_interval=wilson(tp,tp+fn),precision_95_interval=wilson(tp,tp+fp),
                clean_clips=len(normal),clean_clips_flagged=normal_fp,clean_clip_false_alarm_rate=normal_fp/len(normal),
                false_events_per_clean_minute=clean_events/(clean_seconds/60),
                mean_start_error_seconds=float(np.mean([e['start'] for e in errors])) if errors else None,
                max_boundary_error_seconds=max((max(e['start'],e['end']) for e in errors),default=None),
                synthetic_criteria_passed=passed,production_qualified=False)
    report=dict(schema_version=1,status='MEASURED_NOT_PRODUCTION_QUALIFIED',metrics=metrics,
        manifest_sha256=digest(root/'manifest.json'),policy=frozen,case_count=len(evaluated),
        test_family_count=len({r['case']['family'] for r in evaluated if r['case']['split']=='test'}),
        limitation='Synthetic source-disjoint control test only. Intentional holds/black/silence are deliberate false-alarm stress cases. No real independently labelled defect corpus, no production qualification.')
    (root/'benchmark.json').write_text(json.dumps(report,indent=2))
    lines=['# 技术审查受控基准','',report['limitation'],'','| 类型 | TP / FP / FN | 召回 | 精确率 | 正常片误报率 | 最大边界误差 |','|---|---|---|---|---|---|']
    for k,v in metrics['test'].items():lines.append(f"| {k} | {v['tp']} / {v['fp']} / {v['fn']} | {v['recall']} | {v['precision']} | {v['clean_clip_false_alarm_rate']:.3f} | {v['max_boundary_error_seconds']} s |")
    (root/'benchmark.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(report['metrics']['test'],indent=2),flush=True)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);args=p.parse_args()
    create_corpus(args.output);evaluate_corpus(args.output)
if __name__=='__main__':main()
