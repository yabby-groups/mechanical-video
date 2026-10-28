"""Measured speech, immutable render task, preview gate, decode and queue resume."""
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from mechanical_video.runtime import exclusive_lock
from mechanical_video.voiceover import prepare
from mechanical_video.series import compose

def run(args,**kw): subprocess.run(list(map(str,args)),check=True,**kw)

def main():
    source=ROOT/'scripts/visual_story'
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.py')}
    key=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
    folder=ROOT/f'series/3d-printer/experiments/story-CW2-{key}'
    archive=folder/'renderer'; archive.mkdir(parents=True,exist_ok=True)
    for p in source.glob('*.py'):
        target=archive/p.name
        if target.exists(): assert p.read_bytes()==target.read_bytes()
        else: target.write_bytes(p.read_bytes())
    (archive/'fingerprints.json').write_text(json.dumps(hashes,indent=2))
    spec=importlib.util.spec_from_file_location('story_narration',archive/'narration.py')
    narration=importlib.util.module_from_spec(spec); spec.loader.exec_module(narration)
    lines=narration.LINES
    script=folder/'script.md'; script.write_text('\n'.join(lines)+'\n')
    pointer=ROOT/'series/3d-printer/experiments/latest-visual-story.json'
    pointer.write_text(json.dumps(dict(folder=str(folder),state='audio')))
    _,_,cache,clips=prepare(script,folder/'narration.wav')
    cursor=3.5; chapters=[]; segments=[]
    silence=cache/'lead.wav'
    run(['ffmpeg','-y','-v','error','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t',str(cursor),silence]); segments.append(silence)
    for i,((clip,length),line) in enumerate(zip(clips,lines)):
        span=max(4.2,length+.9)
        chapters.append(dict(start=cursor,speech_end=cursor+length,end=cursor+span,narration=line))
        segment=cache/f'story-{i}.wav'
        run(['ffmpeg','-y','-v','error','-i',clip,'-af',f'apad=whole_dur={span}','-t',str(span),'-ar','48000','-ac','1',segment])
        segments.append(segment); cursor+=span
    seconds=math.ceil((cursor+3)*30)/30
    listing=cache/'story-concat.txt'; listing.write_text(''.join(f"file '{p.name}'\n" for p in segments))
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','1','-i',listing,'-af',f'apad=whole_dur={seconds}','-t',str(seconds),folder/'narration.wav'])
    timeline=dict(seconds=seconds,chapters=chapters,voice=dict(model='qwen3-tts-flash',voice='Ethan'))
    (folder/'timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2))
    model=ROOT/'series/3d-printer/master_assembly/assembly.json'
    audits=sorted(set([1,80,round(chapters[1]['start']*30)+45,round(chapters[4]['start']*30)+45,round(seconds*30)]))
    job=dict(folder=str(folder),timeline=timeline,parts=json.loads(model.read_text())['parts'],model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),source_scene=str(ROOT/'series/3d-printer/renders/EP04/04fdabd9902948771c7e/scene.blend'),audit_frames=audits,schematic_filament=dict(diameter_mm=1.75,path='Estimated Z-directed path between source gear bounds; not measured',speed_mm_s=6))
    (folder/'job.json').write_text(json.dumps(job))
    blender='/Applications/Blender.app/Contents/MacOS/Blender'
    pointer.write_text(json.dumps(dict(folder=str(folder),state='waiting_render_lock')))
    with exclusive_lock(ROOT/'artifacts/render.lock',blocking=True):
        with (folder/'blender.log').open('a') as log:
            run([blender,'-b','-t','4','--python-exit-code','1','--python',archive/'scene.py','--',folder/'job.json','preview'],stdout=log,stderr=subprocess.STDOUT)
        pointer.write_text(json.dumps(dict(folder=str(folder),state='preview_ready')))
        # Internal review checkpoint: production begins only after preview inspection.
        deadline=time.monotonic()+600
        while not (folder/'preview-reviewed.json').exists():
            if time.monotonic()>deadline: raise RuntimeError('Preview review timeout; preserved')
            time.sleep(.5)
        pointer.write_text(json.dumps(dict(folder=str(folder),state='production')))
        with (folder/'blender.log').open('a') as log:
            run([blender,'-b','-t','4','--python-exit-code','1','--python',archive/'scene.py','--',folder/'job.json','production'],stdout=log,stderr=subprocess.STDOUT)
    compose(folder,timeline,folder)
    ass=folder/'captions.ass'
    ass.write_text(ass.read_text().replace('官方2.4r2 CAD · 拆解位移及轨迹为示意','官方CAD · 拆解、线材及送料为示意'))
    # Recompose with the experiment-specific overlay, preserving compose timing.
    output=folder/'story-test.mp4'
    run(['ffmpeg','-y','-v','error','-framerate','30','-i',folder/'frames/%06d.jpg','-i',folder/'narration.wav','-vf',f'ass={ass}','-c:v','libx264','-threads','4','-preset','fast','-crf','18','-pix_fmt','yuv420p','-af','loudnorm=I=-16:TP=-1.5:LRA=9','-c:a','aac','-b:a','192k','-t',str(seconds),'-movflags','+faststart',output])
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]))
    v=next(s for s in probe['streams'] if s['codec_type']=='video'); a=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'],v['codec_name'],v['r_frame_rate'],a['codec_name'])==(1080,1920,'h264','30/1','aac')
    assert abs(float(probe['format']['duration'])-seconds)<.1
    assert all(len(c['narration'])<=20 and '\n' not in c['narration'] for c in chapters)
    run(['ffmpeg','-v','error','-i',output,'-f','null','-'])
    (folder/'validation.json').write_text(json.dumps(dict(passed=True,duration=seconds,full_decode='passed',voice=timeline['voice'],subtitle_single_line_max20=True,model_sha256=job['model_sha256'],video_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),limitations=job['schematic_filament']),indent=2))
    pointer.write_text(json.dumps(dict(folder=str(folder),state='complete')))
    print('COMPLETE',output,flush=True)

if __name__=='__main__':
    try: main()
    finally:
        log=(ROOT/'series/3d-printer/production-EP04-08.log').open('a')
        p=subprocess.Popen([sys.executable,'-u','-m','mechanical_video.cli','series','render','--episodes','5-8'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        record=ROOT/'series/3d-printer/production-EP04-08-run.json'
        data=json.loads(record.read_text()); data.update(pid=p.pid,recovery='Resume after visual story sample'); record.write_text(json.dumps(data,indent=2))
        print('RESUMED_PRODUCTION_PID',p.pid,flush=True)
