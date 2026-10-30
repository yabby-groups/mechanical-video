"""Create an immutable EP02 task and render its keyframe preflight."""
import argparse, hashlib, json, math, re, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT))
from mechanical_video.runtime import exclusive_lock
from mechanical_video.voiceover import duration, prepare, stamp
from sound import generate as generate_foley

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('mode',choices=['keyframes','preview','full-keyframes','full-preview','production'],default='keyframes',nargs='?'); requested=parser.parse_args().mode
    full=requested.startswith('full-'); mode=requested.removeprefix('full-')
    source=Path(__file__).resolve().parent
    master=ROOT/'series/3d-printer/master_assembly/assembly.json'
    scene=ROOT/'series/3d-printer/renders/EP04/04fdabd9902948771c7e/scene.blend'
    script=source/'narration.txt'
    hashes={p.name:digest(p) for p in source.glob('*.py')}
    hashes['guide_centres.json']=digest(source/'guide_centres.json')
    hashes.update(master=digest(master),source_scene=digest(scene),narration=digest(script),scope='full' if full else 'short')
    key=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:20]
    folder=ROOT/'series/3d-printer-v2/revisions/EP02'/key; archive=folder/'renderer'; archive.mkdir(parents=True,exist_ok=True)
    for p in source.glob('*.py'):
        dest=archive/p.name
        if dest.exists() and digest(dest)!=digest(p): raise RuntimeError('Archived renderer mismatch')
        if not dest.exists(): shutil.copy2(p,dest)
    guide_data=source/'guide_centres.json'; archived_guide=archive/guide_data.name
    if archived_guide.exists() and digest(archived_guide)!=digest(guide_data): raise RuntimeError('Archived guide mismatch')
    if not archived_guide.exists(): shutil.copy2(guide_data,archived_guide)
    (archive/'fingerprints.json').write_text(json.dumps(hashes,indent=2))
    audio_cache=ROOT/'series/3d-printer-v2/revisions/EP02/bff155348591a22210e5/voiceover.mp3'
    lines,_,_,clips=prepare(script,audio_cache,'qwen3-tts-flash','Kai')
    if any(len(line)>20 for line in lines): raise ValueError('Subtitle exceeds 20 characters')
    audio_dir=folder/'trimmed-clips'; audio_dir.mkdir(exist_ok=True)
    trimmed=[]
    for i,(clip,_) in enumerate(clips):
        target=audio_dir/f'{i:03}.wav'
        if not target.exists():
            trim='silenceremove=start_periods=1:start_duration=0.03:start_threshold=-45dB:start_silence=0.08'
            subprocess.run(['ffmpeg','-y','-v','error','-i',str(clip),'-af',f'{trim},areverse,{trim},areverse','-ar','48000','-ac','1',str(target)],check=True)
        trimmed.append((target,duration(target)))
    cursor=.5; events=[]
    for line,(clip,length) in zip(lines,trimmed):
        events.append(dict(text=line,start=cursor,end=cursor+length,duration=length,clip=str(clip)))
        cursor+=length+(.10 if line[-1] in '，、' else .22)
    seconds=max(90,math.ceil(cursor+2)) if full else 36; frames=seconds*30
    samples=[1]+[round((e['start']+e['duration']/2)*30)+1 for e in events if e['start']+e['duration']/2 < seconds]+[frames]
    if full: samples += [round((seconds-i)*30)+1 for i in (14,12,10,8,6,4,2)]
    samples=sorted(set(samples)); job=dict(folder=str(folder),mode=mode,parts=json.loads(master.read_text())['parts'],source_scene=str(scene),model_sha256=hashes['master'],duration=seconds,frames=frames,samples=samples,events=events)
    (folder/'job.json').write_text(json.dumps(job)); (folder/'audio-timeline.json').write_text(json.dumps(dict(model='qwen3-tts-flash',voice='Kai',events=events,seconds=seconds),ensure_ascii=False,indent=2))
    shutil.copy2(script,folder/'narration.txt'); print('task:',folder,flush=True)
    if mode=='production': raise RuntimeError('This is an internal short test only')
    with exclusive_lock(ROOT/'artifacts/render.lock',blocking=True):
        with (folder/f'{mode}-blender.log').open('a') as log:
            subprocess.run(['/Applications/Blender.app/Contents/MacOS/Blender','-b','-t','4','--python-exit-code','1','--python',str(archive/'scene.py'),'--',str(folder/'job.json')],stdout=log,stderr=subprocess.STDOUT,check=True)
    if mode=='keyframes': return
    captions=[]; command=['ffmpeg','-y','-v','error']; filters=[]
    for i,e in enumerate(events):
        command+=['-i',e['clip']]; filters.append(f'[{i}:a]adelay={round(e["start"]*1000)}:all=1[a{i}]')
        captions.append((e['start'],e['end'],e['text']))
    filters.append(''.join(f'[a{i}]' for i in range(len(events)))+f'amix=inputs={len(events)}:normalize=0,apad,atrim=duration={seconds}[out]')
    subprocess.run(command+['-filter_complex',';'.join(filters),'-map','[out]','-ar','48000','-ac','1',str(folder/'narration.wav')],check=True)
    # Synthesized sounds, not recordings of the source machine.
    foley=folder/'synthetic-foley.wav'
    generate_foley(foley,events,seconds)
    mix=folder/'mixed-audio.wav'
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(folder/'narration.wav'),'-i',str(foley),'-filter_complex','[0:a][1:a]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95:latency=1[out]','-map','[out]',str(mix)],check=True)
    srt=folder/'narration.zh.srt'; srt.write_text('\n\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{c}' for i,(a,b,c) in enumerate(captions))+'\n')
    image_dir=folder/('preview' if mode=='preview' else 'frames'); stride=3 if mode=='preview' else 1
    assert sorted(p.name for p in image_dir.glob('*.jpg'))==[f'{i:06}.jpg' for i in range(1,frames+1,stride)]
    output=folder/('preview.mp4' if mode=='preview' else 'EP02.mp4')
    vf=f"scale=1080:1920,subtitles='{srt}':force_style='FontName=Heiti SC,FontSize=7,Alignment=2,MarginL=18,MarginR=18,MarginV=58',drawtext=fontfile='/System/Library/Fonts/STHeiti Medium.ttc':text='运动与受力为示意 非仿真':fontsize=28:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=8:x=45:y=100"
    subprocess.run(['ffmpeg','-y','-v','error','-framerate',str(30//stride),'-pattern_type','glob','-i',str(image_dir/'*.jpg'),'-i',str(mix),'-vf',vf,'-r','30','-c:v','libx264','-threads','4','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-t',str(seconds),str(output)],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]))
    (folder/f'{mode}-verification.json').write_text(json.dumps(dict(probe=probe,full_decode='passed',video_sha256=digest(output),subtitle_timing='measured clip boundaries; listening review required',synthetic_foley='synthesized; listening review required'),indent=2))
    if full:
        (folder/'loop.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>EP02</title><style>html,body{margin:0;height:100%;background:#111}body{display:grid;place-items:center}video{width:auto;height:100%;max-width:100%;object-fit:contain}</style><video controls autoplay loop playsinline src="preview.mp4"></video></html>',encoding='utf-8')
    print('rendered:',output,flush=True)
if __name__=='__main__': main()
