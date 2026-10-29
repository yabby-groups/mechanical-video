"""Immutable second-edition series plan, sequential queue and media acceptance."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

from .remake_content import EPISODES, VOICE, selected, validate_editorial
from .runtime import exclusive_lock
from .voiceover import prepare, duration, stamp
from .film_audio import ass_stamp
from .series import geometry_inventory

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'series/3d-printer-v2'
MASTER=ROOT/'series/3d-printer/master_assembly/assembly.json'
SOURCE_SCENE=ROOT/'series/3d-printer/renders/EP04/04fdabd9902948771c7e/scene.blend'
SOURCES=['remake.py','remake_content.py','remake_scene.py','voiceover.py','film_audio.py','series.py']
RUNNER=ROOT/'.agents/skills/audiogen/scripts/audio_gen.py'

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p,d):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix(p.suffix+'.tmp'); temp.write_text(json.dumps(d,ensure_ascii=False,indent=2)); temp.replace(p)
def run(args,**kwargs): subprocess.run(list(map(str,args)),check=True,**kwargs)
def queue():
    BASE.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(BASE/'queue.sqlite',timeout=30)
    db.execute('CREATE TABLE IF NOT EXISTS episodes (number INTEGER PRIMARY KEY, state TEXT NOT NULL, task TEXT, error TEXT, updated REAL)')
    return db
def state(n,status,task=None,error=None):
    with queue() as db:
        db.execute('UPDATE episodes SET state=?,task=COALESCE(?,task),error=?,updated=? WHERE number=?',(status,task,error,time.time(),n))
def fingerprints(): return {name:digest(Path(__file__).with_name(name)) for name in SOURCES}
def plan():
    validate_editorial()
    master=read(MASTER); acceptance=read(MASTER.parent/'validation.json')
    assert acceptance['passed'] and acceptance['model_sha256']==digest(MASTER)
    sources=fingerprints()
    geometry=geometry_inventory(MASTER)
    assert geometry==acceptance['geometry_sha256']
    series=dict(name='拆解一台3D打印机 · 动作先行重制版',edition=2,episodes=12,minimum_duration=90,voice=VOICE,model_sha256=digest(MASTER),geometry_sha256=geometry,cad_commit=master['commit'],model=str(MASTER),source_scene_sha256=digest(SOURCE_SCENE),format=dict(width=1080,height=1920,fps=30,video='h264',audio='aac'),old_outputs='Preserved; old queue superseded',renderer_fingerprints=sources)
    existing=BASE/'series.json'
    if existing.exists() and read(existing).get('renderer_fingerprints')!=sources:
        # Per-task folders remain immutable; plan tracks the active source revision.
        history=BASE/'plan-history'/f'{digest(existing)[:16]}.json'
        if not history.exists(): write(history,read(existing))
    write(existing,series)
    modelparts=master['parts']
    with queue() as db:
        for n,(title,shots) in EPISODES.items():
            folder=BASE/f'episodes/EP{n:02}'; folder.mkdir(parents=True,exist_ok=True)
            storyboard=[]
            for area,action,seconds,lines in shots:
                count=sum(selected(area,p) for p in modelparts)
                if not count: raise ValueError(f'Unsupported source area {area}')
                storyboard.append(dict(area=area,action=action,visual_seconds=seconds,narration=lines,source_occurrences=count))
            write(folder/'plan.json',dict(episode=n,title=title,voice=VOICE,shots=storyboard,minimum_duration=90,minimum_visual_duration=sum(s[2] for s in shots),model_sha256=series['model_sha256']))
            (folder/'script.md').write_text('\n'.join(line for s in shots for line in s[3])+'\n')
            db.execute('INSERT OR IGNORE INTO episodes VALUES (?,?,?,?,?)',(n,'queued',None,None,time.time()))
    return series

def rejected_status(message):
    """Only a definite provider rejection is eligible for an audited retry."""
    for status in (429,503):
        if f'Error: Audio provider request failed: HTTP {status}' in message: return status
    return None

def prepare_clips(script,folder):
    lines=script.read_text().splitlines()
    identity=dict(lines=lines,voice=VOICE,runner_sha256=digest(RUNNER),endpoint=os.getenv('OPENAI_BASE_URL','').strip() or 'https://huabot.com/v1')
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:20]
    cache=folder/f'narration.voiceover/{key}'; cache.mkdir(parents=True,exist_ok=True)
    write(cache/'identity.json',identity); clips=[]
    for i,line in enumerate(lines):
        target=cache/f'{i:03}.mp3'; pending=cache/f'{i:03}.submitted'
        text=cache/f'{i:03}.txt'; text.write_text(line)
        if target.exists(): clips.append((target,duration(target))); continue
        if pending.exists(): raise RuntimeError(f'Uncertain prior speech submission preserved: {pending}')
        if not os.getenv('OPENAI_API_KEY','').strip(): raise RuntimeError('Set OPENAI_API_KEY before speech synthesis')
        for attempt in range(3):
            pending.touch(); log=cache/f'{i:03}-request-{time.time_ns()}.log'
            with log.open('w') as handle:
                result=subprocess.run([sys.executable,str(RUNNER),'--text-file',str(text),'--model',VOICE['model'],'--voice',VOICE['voice'],'--out',str(target)],stdout=handle,stderr=subprocess.STDOUT)
            if result.returncode==0:
                clips.append((target,duration(target))); print('AUDIO',target.name,VOICE['voice'],flush=True); break
            status=rejected_status(log.read_text())
            if status is None: raise RuntimeError(f'Speech outcome uncertain; inspect {log}; submission marker preserved')
            archived=pending.with_name(pending.name+f'.http{status}.{time.time_ns()}'); pending.rename(archived)
            write(archived.with_suffix(archived.suffix+'.json'),dict(http_status=status,request_log=str(log),attempt=attempt+1,disposition='Definite rejection; retry authorized within series production'))
            if attempt==2: raise RuntimeError(f'Provider HTTP {status}; three rejected submissions preserved in {cache}')
            time.sleep(5*(attempt+1))
    return cache,clips

def audio(n):
    folder=BASE/f'episodes/EP{n:02}'; spec=read(folder/'plan.json')
    script=folder/'script.md'; narration=folder/'narration.wav'
    # The cache key includes every utterance, voice, model, runner and endpoint.
    cache,clips=prepare_clips(script,folder)
    cursor=0; chapters=[]; shots=[]; segments=[]; i=0
    for index,shot in enumerate(spec['shots']):
        lengths=[clips[i+k][1] for k in range(len(shot['narration']))]
        lead=1.1 if index else 1.8
        spoken=sum(lengths); between=.24*(len(lengths)-1)
        span=max(shot['visual_seconds'],lead+spoken+between+1)
        end=cursor+span
        shots.append(dict(area=shot['area'],action=shot['action'],start=cursor,end=end))
        silence=cache/f'lead-{index}.wav'
        run(['ffmpeg','-y','-v','error','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t',str(lead),silence]); segments.append(silence)
        t=cursor+lead
        for k,line in enumerate(shot['narration']):
            clip,length=clips[i]; gap=.24 if k<len(lengths)-1 else end-(t+length)
            chapters.append(dict(start=t,speech_end=t+length,end=t+length+gap,narration=line,shot=index))
            segment=cache/f'utterance-{i}.wav'
            run(['ffmpeg','-y','-v','error','-i',clip,'-af',f'apad=whole_dur={length+gap}','-t',str(length+gap),'-ar','48000','-ac','1',segment])
            segments.append(segment); t+=length+gap; i+=1
        cursor=end
    seconds=math.ceil(cursor*30)/30
    assert seconds>=90
    listing=cache/'remake-concat.txt'; listing.write_text(''.join(f"file '{p.name}'\n" for p in segments))
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','1','-i',listing,'-af',f'apad=whole_dur={seconds}','-t',str(seconds),narration])
    timeline=dict(seconds=seconds,chapters=chapters,shots=shots,voice=VOICE,script_sha256=digest(script),speech_cache=str(cache),spoken_seconds=sum(d for _,d in clips))
    write(folder/'timeline.json',timeline)
    (folder/'subtitles.srt').write_text('\n\n'.join(f'{k+1}\n{stamp(c["start"])} --> {stamp(c["speech_end"])}\n{c["narration"]}' for k,c in enumerate(chapters))+'\n')
    return timeline

def captions(folder,timeline):
    text='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,STHeiti,44,&H00FFFFFF,&H00FFFFFF,&H00101822,&H90000000,0,0,0,0,100,100,0,0,1,3,1,2,40,40,170,1
Style: Label,STHeiti,25,&H00C2C4C6,&H00FFFFFF,&H00101822,&H90000000,0,0,0,0,100,100,0,0,1,2,0,8,45,45,100,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    for c in timeline['chapters']:
        assert 0<len(c['narration'])<=20 and '\n' not in c['narration']
        text+=f'Dialogue: 0,{ass_stamp(c["start"])},{ass_stamp(c["speech_end"])},Default,,0,0,0,,{c["narration"]}\n'
    text+=f'Dialogue: 1,0:00:00.00,{ass_stamp(timeline["seconds"])},Label,,0,0,0,,官方CAD · 局部近似 · 拆解与运动为示意\n'
    for s in timeline['shots']:
        if s['action'] in ('feed','loose','retract','layer'):
            text+=f'Dialogue: 1,{ass_stamp(s["start"])},{ass_stamp(s["end"])},Label,,0,0,38,,线材、送料和沉积路径为原理示意\n'
    (folder/'captions.ass').write_text(text)

def verify(path,task,job):
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
    v=next(s for s in probe['streams'] if s['codec_type']=='video'); a=next(s for s in probe['streams'] if s['codec_type']=='audio')
    seconds=float(probe['format']['duration']); t=job['timeline']
    assert seconds>=90 and abs(seconds-t['seconds'])<.12
    assert (v['codec_name'],v['width'],v['height'],v['r_frame_rate'],a['codec_name'])==('h264',1080,1920,'30/1','aac')
    assert t['voice']==VOICE and job['model_sha256']==digest(MASTER)
    assert job['geometry_sha256']==geometry_inventory(MASTER)
    previous=0
    for c in t['chapters']:
        assert c['start']>=previous and c['start']<c['speech_end']<=c['end']<=seconds+.02
        assert 0<len(c['narration'])<=20 and '\n' not in c['narration']; previous=c['speech_end']
    native=read(task/'production-audit.json'); preview=read(task/'preview-audit.json')
    assert native['passed'] and preview['passed']
    assert native['source_model_sha256']==job['model_sha256'] and native['shots']==8
    changes=0
    for i in range(8):
        x,y=[s for s in native['samples'] if s['shot']==i]
        first={p['id']:p['position'] for p in x['source_positions']}
        if any(p['id'] in first and max(abs(a-b) for a,b in zip(first[p['id']],p['position']))>1e-5 for p in y['source_positions']): changes+=1
    assert changes>=3, f'Insufficient distinct source-part motion: {changes}'
    run(['ffmpeg','-v','error','-i',path,'-f','null','-'])
    return dict(passed=True,duration=seconds,width=1080,height=1920,fps=30,video='h264',audio='aac',voice=VOICE,full_decode='passed',source_model_sha256=job['model_sha256'],mechanical_motion_shots=changes,subtitle_single_line_max20=True,video_sha256=digest(path),native_scene=str(task/'scene.blend'),limitations=native['classification'])

def render(n,preview_only=False):
    episode=BASE/f'episodes/EP{n:02}'; output=BASE/f'output/EP{n:02}.mp4'
    if output.exists():
        report=read(episode/'validation.json')
        assert report['passed'] and report['video_sha256']==digest(output)
        state(n,'complete'); print('PRESERVED',output,flush=True); return
    state(n,'audio')
    timeline=audio(n)
    geometry=geometry_inventory(MASTER)
    assert geometry==read(BASE/'series.json')['geometry_sha256']
    identity=dict(episode=n,model=digest(MASTER),geometry=geometry,timeline=timeline,sources=fingerprints(),voice=VOICE,source_scene_sha256=digest(SOURCE_SCENE))
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:20]
    task=BASE/f'renders/EP{n:02}/{key}'; archive=task/'renderer'; archive.mkdir(parents=True,exist_ok=True)
    for name in SOURCES:
        src=Path(__file__).with_name(name); target=archive/name
        if target.exists(): assert digest(target)==digest(src)
        else: shutil.copy2(src,target)
    write(archive/'fingerprints.json',fingerprints())
    job=dict(episode=n,title=EPISODES[n][0],manifest=str(MASTER),model_sha256=digest(MASTER),geometry_sha256=geometry,source_scene=str(SOURCE_SCENE),source_scene_sha256=digest(SOURCE_SCENE),timeline=timeline,identity=identity)
    write(task/'job.json',job); write(episode/'job.json',dict(job,task=str(task)))
    shutil.copy2(episode/'narration.wav',task/'narration.wav')
    blender=os.getenv('BLENDER_BIN') or '/Applications/Blender.app/Contents/MacOS/Blender'
    with exclusive_lock(ROOT/'artifacts/render.lock',blocking=True):
        for mode in (['preview'] if preview_only else ['preview','production']):
            state(n,mode,str(task))
            with (task/'blender.log').open('a') as log:
                run([blender,'-b','-t','4','--python-exit-code','1','--python',archive/'remake_scene.py','--',task/'job.json',mode],stdout=log,stderr=subprocess.STDOUT)
            report=read(task/f'{mode}-audit.json')
            assert report['passed'] and len(report['samples'])==16
            assert all(s['visible_parts']>0 and s['camera_scale']>=s['required_scale']*.999 for s in report['samples'])
        if preview_only:
            state(n,'preview_ready',str(task)); print('PREVIEW',task,flush=True); return
    state(n,'encoding',str(task)); captions(task,timeline)
    pending=task/'encoding.mp4'
    with (task/'composition.log').open('a') as log:
        run(['ffmpeg','-y','-v','error','-framerate','30','-i',task/'frames/%06d.jpg','-i',task/'narration.wav','-vf','ass=captions.ass:fontsdir=/System/Library/Fonts','-af','loudnorm=I=-16:TP=-1.5:LRA=9','-c:v','libx264','-threads','4','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t',str(timeline['seconds']),'-movflags','+faststart',pending],cwd=task,stdout=log,stderr=subprocess.STDOUT)
    state(n,'validating',str(task)); report=verify(pending,task,job)
    write(task/'validation.json',report); write(episode/'validation.json',report)
    output.parent.mkdir(exist_ok=True); shutil.copy2(pending,output); pending.rename(task/'final.mp4')
    state(n,'complete',str(task)); print('COMPLETE',output,flush=True)

def worker():
    if (BASE/'editorial-hold.json').exists():
        raise RuntimeError('Batch is on editorial hold after EP01 rejection; preserve old tasks and create a revised editorial version before resuming')
    with exclusive_lock(BASE/'worker.lock'):
        while True:
            with queue() as db:
                row=db.execute("SELECT number FROM episodes WHERE state!='complete' ORDER BY number LIMIT 1").fetchone()
            if not row: return
            n=row[0]
            try: render(n)
            except Exception as e:
                state(n,'failed',error=f'{type(e).__name__}: {e}'); raise

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('plan'); sub.add_parser('worker'); sub.add_parser('status')
    render_parser=sub.add_parser('render'); render_parser.add_argument('--episode',type=int,required=True); render_parser.add_argument('--preview-only',action='store_true')
    a=p.parse_args(argv)
    if a.command=='plan': print(json.dumps(plan(),ensure_ascii=False,indent=2))
    elif a.command=='status':
        with queue() as db:
            for row in db.execute('SELECT number,state,task,error FROM episodes ORDER BY number'): print(json.dumps(row,ensure_ascii=False))
    elif a.command=='worker': worker()
    else:
        if a.episode not in EPISODES: p.error('Episode must be 1..12')
        with exclusive_lock(BASE/'worker.lock'): render(a.episode,a.preview_only)

if __name__=='__main__': main()
