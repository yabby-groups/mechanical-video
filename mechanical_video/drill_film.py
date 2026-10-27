"""Narration-paced, resumable long-form drill disassembly using the shared renderer."""
import argparse
import json
from pathlib import Path
from .voiceover import prepare
from .cli import enqueue

TITLES = ['01 / CORDLESS DRILL', '02 / REMOVE THE BATTERY', '03 / SPLIT THE HOUSING',
          '04 / CHUCK AND SPINDLE', '05 / INFERRED GEAR TRAIN', '06 / INFERRED MOTOR',
          '07 / CONTROLS AND ELECTRONICS', '08 / HYPOTHETICAL BATTERY', '09 / COMPLETE EXPLODED VIEW']

def storyboard(parts, clips, seconds=90):
    """Use measured speech duration and real offsets, never character-based timing."""
    if len(clips)!=9: raise ValueError('Drill film requires nine narration chapters')
    spoken=sum(length for _,length in clips)
    if spoken>seconds: raise ValueError(f'Speech {spoken:.3f}s exceeds target {seconds}s; shorten narration')
    gap=(seconds-spoken)/9
    chapters=[]; cursor=0
    def battery(p): return p['name'].startswith(('battery_', 'inferred_cell_'))
    def front(p): return p['name'].startswith(('chuck_','keyless_','torque_','output_spindle','gearbox_nose'))
    def motor(p): return p['group']=='motor' or p['name'].startswith('motor_')
    def controls(p): return p['group'] in ('control','electrical') and not battery(p)
    for i,(_,length) in enumerate(clips):
        names=[p['name'] for p in parts if i in (0,1,2,8) or
               (i==3 and front(p)) or (i==4 and p['group'] in ('gear','carrier','gearbox','clutch')) or
               (i==5 and motor(p)) or (i==6 and controls(p)) or (i==7 and battery(p))]
        if not names: raise ValueError(f'Empty shot {i}')
        chapters.append({'start':cursor,'speech_end':cursor+length,'end':cursor+length+gap,
                         'title':TITLES[i],'visible_parts':names})
        cursor+=length+gap
    chapters[-1]['end']=seconds
    tracks={}
    for p in parts:
        if battery(p):
            c=chapters[1]; b=chapters[7]
            tracks[p['name']]=[[0,[0,0,0]],[c['start'],[0,0,0]],
                [c['start']+(c['end']-c['start'])*.75,[0,0,-45]],
                [b['start'],[0,0,-45]],[b['start']+(b['end']-b['start'])*.75,p['explode']],
                [seconds,p['explode']]]
            continue
        chapter=2 if p['group']=='shell' or p['group']=='fastener' else 4
        if front(p): chapter=3
        if motor(p): chapter=5
        if controls(p): chapter=6
        c=chapters[chapter]
        tracks[p['name']]=[[0,[0,0,0]],[c['start'],[0,0,0]],
            [c['start']+(c['end']-c['start'])*.75,p['explode']],[seconds,p['explode']]]
    return {'chapters':chapters,'tracks_mm':tracks,'timing':'ffprobe measured speech plus equal chapter pauses',
            'spoken_seconds':spoken,'pause_per_chapter':gap}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--script',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--root',type=Path,default=Path('artifacts'))
    parser.add_argument('--seconds',type=float,default=90)
    args=parser.parse_args()
    data=json.loads(args.manifest.read_text())
    if data.get('product')!='cordless_drill': raise ValueError('A cordless_drill manifest is required')
    lines,folder,cache,clips=prepare(args.script,args.output)
    story=storyboard(data['parts'],clips,args.seconds)
    for chapter,line in zip(story['chapters'],lines): chapter['narration']=line
    story['speech_cache']=str(cache)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    (args.output.parent/'storyboard.json').write_text(json.dumps(story,ensure_ascii=False,indent=2))
    jobs=enqueue(args.root,args.manifest,['explanation'],seconds=args.seconds,storyboard=story)
    (args.output.parent/'render-task.json').write_text(json.dumps(jobs,indent=2))
    print(json.dumps(jobs))

if __name__=='__main__': main()
