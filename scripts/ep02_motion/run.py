"""Create an immutable EP02 task and render its keyframe preflight."""
import argparse, hashlib, json, math, re, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT))
from mechanical_video.runtime import exclusive_lock
from mechanical_video.voiceover import prepare, stamp

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('mode',choices=['keyframes','preview','production'],default='keyframes',nargs='?'); mode=parser.parse_args().mode
    source=Path(__file__).resolve().parent
    master=ROOT/'series/3d-printer/master_assembly/assembly.json'
    scene=ROOT/'series/3d-printer/renders/EP04/04fdabd9902948771c7e/scene.blend'
    script=source/'narration.txt'
    hashes={p.name:digest(p) for p in source.glob('*.py')}
    hashes.update(master=digest(master),source_scene=digest(scene),narration=digest(script))
    key=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:20]
    folder=ROOT/'series/3d-printer-v2/revisions/EP02'/key; archive=folder/'renderer'; archive.mkdir(parents=True,exist_ok=True)
    for p in source.glob('*.py'):
        dest=archive/p.name
        if dest.exists() and digest(dest)!=digest(p): raise RuntimeError('Archived renderer mismatch')
        if not dest.exists(): shutil.copy2(p,dest)
    (archive/'fingerprints.json').write_text(json.dumps(hashes,indent=2))
    audio_cache=ROOT/'series/3d-printer-v2/revisions/EP02/bff155348591a22210e5/voiceover.mp3'
    lines,_,_,clips=prepare(script,audio_cache,'qwen3-tts-flash','Kai')
    if any(len(line)>20 for line in lines): raise ValueError('Subtitle exceeds 20 characters')
    cursor=.5; events=[]
    for line,(clip,length) in zip(lines,clips):
        events.append(dict(text=line,start=cursor,end=cursor+length,duration=length,clip=str(clip)))
        cursor+=length+.18
    seconds=max(90,math.ceil(cursor+2)); frames=seconds*30
    samples=[1]+[min(frames,round((e['start']+e['duration']/2)*30)+1) for e in events]+[frames]
    job=dict(folder=str(folder),mode=mode,parts=json.loads(master.read_text())['parts'],source_scene=str(scene),model_sha256=hashes['master'],duration=seconds,frames=frames,samples=samples,events=events)
    (folder/'job.json').write_text(json.dumps(job)); (folder/'audio-timeline.json').write_text(json.dumps(dict(model='qwen3-tts-flash',voice='Kai',events=events,seconds=seconds),ensure_ascii=False,indent=2))
    shutil.copy2(script,folder/'narration.txt'); print('task:',folder,flush=True)
    if mode=='production':
        review=folder/'preview-reviewed.json'
        if not review.exists() or not json.loads(review.read_text()).get('passed') or json.loads(review.read_text()).get('video_sha256') != digest(folder/'preview.mp4'): raise RuntimeError('Review of this exact preview required')
    with exclusive_lock(ROOT/'artifacts/render.lock',blocking=True):
        with (folder/f'{mode}-blender.log').open('a') as log:
            subprocess.run(['/Applications/Blender.app/Contents/MacOS/Blender','-b','-t','4','--python-exit-code','1','--python',str(archive/'scene.py'),'--',str(folder/'job.json')],stdout=log,stderr=subprocess.STDOUT,check=True)
    if mode=='keyframes': return
    captions=[]; command=['ffmpeg','-y','-v','error']; filters=[]
    for i,e in enumerate(events):
        command+=['-i',e['clip']]; filters.append(f'[{i}:a]adelay={round(e["start"]*1000)}:all=1[a{i}]')
        chunks=[]
        for phrase in re.findall(r'[^，。！？；：]+[，。！？；：]?',e['text']):
            chunks.extend(phrase[n:n+20] for n in range(0,len(phrase),20))
        cursor=e['start']
        for chunk in chunks:
            end=cursor+e['duration']*len(chunk)/len(e['text']); captions.append((cursor,end,chunk)); cursor=end
    filters.append(''.join(f'[a{i}]' for i in range(len(events)))+f'amix=inputs={len(events)}:normalize=0,apad,atrim=duration={seconds}[out]')
    subprocess.run(command+['-filter_complex',';'.join(filters),'-map','[out]','-ar','48000','-ac','1',str(folder/'narration.wav')],check=True)
    # Synthesized low-level movement and engagement sounds, never machine recordings.
    foley=folder/'synthetic-foley.wav'
    expression=(f"0.012*sin(2*PI*82*t)*(between(t,0,11)+between(t,{seconds-16},{seconds-3}))"
                f"+0.006*sin(2*PI*120*t)*between(t,35,56)"
                f"+0.025*sin(2*PI*210*t)*exp(-18*abs(t-{seconds-3}))")
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i',f"aevalsrc={expression.replace(',', chr(92)+',')}:s=48000:d={seconds}",str(foley)],check=True)
    mix=folder/'mixed-audio.wav'
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(folder/'narration.wav'),'-i',str(foley),'-filter_complex','[0:a][1:a]amix=inputs=2:normalize=0:duration=first[out]','-map','[out]',str(mix)],check=True)
    srt=folder/'narration.zh.srt'; srt.write_text('\n\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{c}' for i,(a,b,c) in enumerate(captions))+'\n')
    image_dir=folder/('preview' if mode=='preview' else 'frames'); stride=3 if mode=='preview' else 1
    assert sorted(p.name for p in image_dir.glob('*.jpg'))==[f'{i:06}.jpg' for i in range(1,frames+1,stride)]
    output=folder/('preview.mp4' if mode=='preview' else 'EP02.mp4')
    vf=f"scale=1080:1920,subtitles='{srt}':force_style='FontName=Heiti SC,FontSize=8,MarginV=58',drawtext=fontfile='/System/Library/Fonts/STHeiti Medium.ttc':text='运动与受力为示意 非仿真':fontsize=28:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=8:x=45:y=100"
    subprocess.run(['ffmpeg','-y','-v','error','-framerate',str(30//stride),'-pattern_type','glob','-i',str(image_dir/'*.jpg'),'-i',str(mix),'-vf',vf,'-r','30','-c:v','libx264','-threads','4','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-t',str(seconds),str(output)],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]))
    (folder/f'{mode}-verification.json').write_text(json.dumps(dict(probe=probe,full_decode='passed',video_sha256=digest(output),subtitle_timing='proportional estimate; review required',synthetic_foley='synthesized; listening review required'),indent=2))
    print('rendered:',output,flush=True)
if __name__=='__main__': main()
