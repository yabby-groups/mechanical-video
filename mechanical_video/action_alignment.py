"""Check explicit action assertions against frozen per-frame motion, not inferred speech."""
import argparse
import json
import math
from pathlib import Path
from .scene_fidelity import canonical, file_ref


def number(value):
    return type(value) in (int,float) and math.isfinite(value)


def evaluate(motion, timeline, policy):
    if policy.get('schema_version') != 1 or not policy.get('requirements'):
        raise ValueError('Missing action assertion policy v1')
    poses=motion['poses']; fps=motion['fps']
    if (not number(fps) or fps<=0 or not isinstance(poses,list) or len(poses)!=motion['frames'] or len(poses)<2
            or any(not isinstance(p,dict) or not number(p.get('time')) or abs(p['time']-i/fps)>1e-6 for i,p in enumerate(poses))):
        raise ValueError('Missing/nonfinite/skipped native-frame poses')
    captions=timeline['captions']
    if (not isinstance(captions,list) or not captions or not number(timeline.get('duration'))
            or abs(timeline['duration']-len(poses)/fps)>1/fps+1e-6):
        raise ValueError('Timeline and motion durations differ')
    ids=[]; findings=[]; checks=[]
    for row in policy['requirements']:
        rid=row['id']
        if not isinstance(rid,str) or not rid or rid in ids or not row.get('assertions'):
            raise ValueError('Missing/duplicate requirement or action assertions')
        ids.append(rid)
        for assertion in row['assertions']:
            text=assertion['caption_text']; channel=assertion['channel']; relation=assertion['relation']
            if not isinstance(text,str) or not text or not isinstance(channel,str) or not channel:
                raise ValueError('Missing caption/channel')
            matches=[c for c in captions if c.get('text')==text]
            if len(matches)!=1:
                raise ValueError('Action caption absent or ambiguous: '+text)
            cap=matches[0];start=cap['start'];end=cap['end']
            if not number(start) or not number(end) or not 0<=start<end<=timeline['duration']:
                raise ValueError('Invalid caption interval')
            samples=[p for p in poses if start<=p['time']<end]
            if len(samples)<2 or any(not number(p.get(channel)) for p in samples):
                raise ValueError('Missing actual action channel samples')
            values=[p[channel] for p in samples];change=values[-1]-values[0]
            if relation in ('increasing','decreasing'):
                minimum=assertion['min_change']
                if not number(minimum) or minimum<=0:
                    raise ValueError('Invalid expected movement threshold')
                sign=1 if relation=='increasing' else -1
                passed=sign*change>=minimum and all(sign*(b-a)>=-1e-6 for a,b in zip(values,values[1:]))
            elif relation in ('held_above','held_below'):
                bound=assertion['bound'];fraction=assertion['min_fraction']
                if not number(bound) or not number(fraction) or not 0<fraction<=1:
                    raise ValueError('Invalid expected held-state threshold')
                count=sum(v>=bound if relation=='held_above' else v<=bound for v in values)
                passed=count/len(values)>=fraction
            else:
                raise ValueError('Unsupported action assertion')
            check=dict(requirement=rid,caption=text,interval=[start,end],channel=channel,expected=relation,
                       first=values[0],last=values[-1],minimum=min(values),maximum=max(values),samples=len(values),
                       status='PASS' if passed else 'BLOCKED')
            checks.append(check)
            if not passed:findings.append(check)
    return dict(status='BLOCKED' if findings else 'PASS',requirements=ids,checks=checks,failures=findings,
                scope='Explicit caption-to-motion assertions only; no word alignment, audio perception or automatic semantic understanding.')


def inspect(motion_path,timeline_path,policy_path):
    refs={k:file_ref(p) for k,p in dict(motion=motion_path,timeline=timeline_path,policy=policy_path).items()}
    data={k:json.loads(Path(v['path']).read_text()) for k,v in refs.items()}
    result=evaluate(data['motion'],data['timeline'],data['policy'])
    if any(file_ref(v['path'])!=v for v in refs.values()):
        raise ValueError('Inputs changed during action check')
    report=dict(schema_version=1,kind='caption-action-alignment',inputs=refs,
                implementation_sha256=file_ref(__file__)['sha256'],**result)
    report['result_sha256']=canonical(report)
    return report


def verify(report,assets,required_ids):
    try:
        if set(report['inputs'])!={'motion','timeline','policy'}:
            return False
        expected_assets={'motion':'motion','timeline':'timeline','policy':'action_alignment_policy'}
        for name,ref in report['inputs'].items():
            if ref!=assets[expected_assets[name]] or file_ref(ref['path'])!=ref:return False
        fresh=inspect(*(report['inputs'][k]['path'] for k in ['motion','timeline','policy']))
        return report==fresh and fresh['status']=='PASS' and set(fresh['requirements'])==set(required_ids)
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        return False


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--motion',type=Path,required=True);parser.add_argument('--timeline',type=Path,required=True)
    parser.add_argument('--policy',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        report=inspect(args.motion,args.timeline,args.policy)
        with args.output.open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc)},ensure_ascii=False));return 2
    print(json.dumps({'status':report['status'],'failed_assertions':len(report['failures'])}));return 1 if report['status']=='BLOCKED' else 0


if __name__=='__main__':raise SystemExit(main())
