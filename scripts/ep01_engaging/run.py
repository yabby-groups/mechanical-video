"""Isolated, fingerprinted EP01 revision. Preview review precedes production."""
import argparse, hashlib, importlib.util, json, subprocess, sys, os, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT))
from mechanical_video.runtime import exclusive_lock
from mechanical_video.voiceover import RUNNER, prepare, stamp

def run(args,**kw): subprocess.run(list(map(str,args)),check=True,**kw)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('stage',choices=['prepare','preview','production']); a=parser.parse_args()
    source=Path(__file__).resolve().parent
    hashes={p.name:digest(p) for p in source.iterdir() if p.suffix in ('.py','.json')}
    master=ROOT/'series/3d-printer/master_assembly/assembly.json'
    base=ROOT/'series/3d-printer/renders/EP04/04fdabd9902948771c7e/scene.blend'
    hashes['master']=digest(master); hashes['source_scene']=digest(base)
    key=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:20]
    folder=ROOT/'series/3d-printer-v2/revisions/EP01'/key; archive=folder/'renderer'; archive.mkdir(parents=True,exist_ok=True)
    for name in hashes:
        p=source/name
        if not p.is_file(): continue
        q=archive/name
        if q.exists(): assert q.read_bytes()==p.read_bytes()
        else: q.write_bytes(p.read_bytes())
    (archive/'fingerprints.json').write_text(json.dumps(hashes,indent=2))
    job=dict(folder=str(folder),parts=json.loads(master.read_text())['parts'],model_sha256=hashes['master'],source_scene=str(base),source_scene_sha256=hashes['source_scene'])
    (folder/'job.json').write_text(json.dumps(job))
    print(folder,flush=True)
    if a.stage!='prepare':
        existing=folder/('preview.mp4' if a.stage=='preview' else 'EP01.mp4')
        if existing.exists():
            report=folder/f'{a.stage}-verification.json'
            if report.exists() and json.loads(report.read_text()).get('video_sha256')==digest(existing):
                print('PRESERVED verified output',existing,flush=True); return
            raise RuntimeError('Existing unverified output preserved; archive it before retrying mux')
    director=json.loads((archive/'director.json').read_text()); events=director['narration']
    script=folder/'narration.txt'; script.write_text('\n'.join(e['text'] for e in events))
    endpoint=os.getenv('OPENAI_BASE_URL','').strip() or 'https://huabot.com/v1'
    def audio_key(lines):
        identity=dict(lines=lines,model=director['model'],voice=director['voice'],runner_sha256=digest(RUNNER),endpoint=endpoint)
        return hashlib.sha256(json.dumps(identity,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:20]
    target=folder/'voiceover.voiceover'/audio_key([e['text'] for e in events]); target.mkdir(parents=True,exist_ok=True)
    for prior in (ROOT/'series/3d-printer-v2/revisions/EP01').iterdir():
        if prior==folder or not (prior/'renderer/director.json').exists(): continue
        old=json.loads((prior/'renderer/director.json').read_text())
        if (old['model'],old['voice'])!=(director['model'],director['voice']): continue
        old_events=old['narration']; cache=prior/'voiceover.voiceover'/audio_key([e['text'] for e in old_events])
        for i,event in enumerate(events):
            for j,old_event in enumerate(old_events):
                if event['text']!=old_event['text'] or (target/f'{i:03}.mp3').exists(): continue
                clip=cache/f'{j:03}.mp3'
                if clip.exists(): shutil.copy2(clip,target/f'{i:03}.mp3')
                elif (cache/f'{j:03}.submitted').exists(): raise RuntimeError(f'Uncertain prior speech submission: {cache/f"{j:03}.submitted"}')
    lines,_,cache,clips=prepare(script,folder/'voiceover.mp3',director['model'],director['voice'])
    filters=[]; cmd=['ffmpeg','-y','-v','error']; captions=[]
    for i,(e,(clip,length)) in enumerate(zip(events,clips)):
        e['end']=e['start']+length; e['duration']=length
        assert e['end']<(events[i+1]['start'] if i+1<len(events) else 100)
        assert ''.join(e['captions'])==e['text'] and all('\n' not in x and len(x)<=20 for x in e['captions'])
        cursor=e['start']
        for c in e['captions']:
            end=cursor+length*len(c)/len(e['text']); captions.append((cursor,end,c)); cursor=end
        cmd+=['-i',str(clip)]; filters.append(f'[{i}:a]adelay={round(e["start"]*1000)}:all=1[a{i}]')
    spoken=sum(e['duration'] for e in events)
    assert spoken<80, f'Measured narration {spoken:.2f}s leaves too little room for the action'
    filters.append(''.join(f'[a{i}]' for i in range(len(events)))+f'amix=inputs={len(events)}:normalize=0,apad,atrim=duration=100[out]')
    run(cmd+['-filter_complex',';'.join(filters),'-map','[out]','-ar','48000','-ac','1',folder/'narration.wav'])
    (folder/'narration.zh.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(b)} --> {stamp(e)}\n{c}' for i,(b,e,c) in enumerate(captions))+'\n')
    (folder/'audio-timeline.json').write_text(json.dumps(dict(model=director['model'],voice=director['voice'],spoken_seconds=spoken,events=events),ensure_ascii=False,indent=2))
    spec=importlib.util.spec_from_file_location('sound',archive/'sound.py'); sound=importlib.util.module_from_spec(spec); spec.loader.exec_module(sound); sound.generate(folder/'foley.wav',events)
    run(['ffmpeg','-y','-v','error','-i',folder/'narration.wav','-i',folder/'foley.wav','-filter_complex','[0:a][1:a]amix=inputs=2:normalize=0,alimiter=limit=0.9','-c:a','pcm_s16le',folder/'mix.wav'])
    if a.stage=='prepare': return
    if a.stage=='production':
        review=json.loads((folder/'preview-reviewed.json').read_text())
        assert review['passed'] and review['preview_sha256']==digest(folder/'preview.mp4')
    mode=a.stage
    # Reuse only complete, verified frames from the exact same scene version.
    cache_hit=False
    image_dir='preview' if mode=='preview' else 'frames'
    required_frames=750 if mode=='preview' else 3000
    if not (folder/f'{mode}-audit.json').exists():
        for previous in (ROOT/'series/3d-printer-v2/revisions/EP01').glob(f'*/{mode}-verification.json'):
            prior=previous.parent
            if prior==folder: continue
            prior_hashes=json.loads((prior/'renderer/fingerprints.json').read_text())
            if any(prior_hashes.get(k)!=hashes[k] for k in ('scene.py','motion.py','master','source_scene')): continue
            files=list((prior/image_dir).glob('*.jpg'))
            if len(files)!=required_frames or not all(p.read_bytes().endswith(b'\xff\xd9') for p in files): continue
            (folder/image_dir).mkdir(exist_ok=True)
            for frame in files: shutil.copy2(frame,folder/image_dir/frame.name)
            for name in (f'{mode}-audit.json','preview.blend' if mode=='preview' else 'scene.blend','source-paths.json'):
                shutil.copy2(prior/name,folder/name)
            (folder/f'{mode}-frame-cache-provenance.json').write_text(json.dumps(dict(source=str(prior),matched=['scene.py','motion.py','master','source_scene']),indent=2))
            cache_hit=True
            break
    if not cache_hit:
      with exclusive_lock(ROOT/'artifacts/render.lock',blocking=True):
        with (folder/f'{mode}-blender.log').open('a') as log:
            run(['/Applications/Blender.app/Contents/MacOS/Blender','-b','-t','4','--python-exit-code','1','--python',archive/'scene.py','--',folder/'job.json',mode],stdout=log,stderr=subprocess.STDOUT)
    images=folder/('preview' if mode=='preview' else 'frames')
    # Preview is the complete timeline sampled at 7.5 fps; production is 30 fps.
    listing=folder/f'{mode}-frames.txt'
    listing.write_text(''.join(f"file '{images.name}/{p.name}'\nduration {4/30 if mode=='preview' else 1/30:.12f}\n" for p in sorted(images.glob('*.jpg'))))
    label="drawtext=fontfile='/System/Library/Fonts/STHeiti Medium.ttc':text='拆解、温度、线材与沉积示意 · 合成拟音':fontsize=22:fontcolor=white@0.6:x=(w-tw)/2:y=h-65"
    hypothetical="drawtext=fontfile='/System/Library/Fonts/STHeiti Medium.ttc':text='假设：线材过早软化':fontsize=38:fontcolor=white:x=(w-tw)/2:y=90:enable='between(t,18,26)'"
    vf=f"scale=1080:1920,subtitles='{folder/'narration.zh.srt'}':force_style='FontName=Heiti SC,FontSize=8,MarginV=20',"+label+','+hypothetical
    output=folder/('preview.mp4' if mode=='preview' else 'EP01.mp4')
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',listing,'-i',folder/'mix.wav','-vf',vf,'-r','30','-c:v','libx264','-threads','4','-preset','fast','-crf','20' if mode=='preview' else '18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t','100','-movflags','+faststart',output])
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(output)]))
    v=next(s for s in probe['streams'] if s['codec_type']=='video'); au=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'],v['codec_name'],v['r_frame_rate'],au['codec_name'])==(1080,1920,'h264','30/1','aac')
    assert abs(float(probe['format']['duration'])-100)<.1
    run(['ffmpeg','-v','error','-i',output,'-f','null','-'])
    report=dict(passed=True,stage=mode,seconds=float(probe['format']['duration']),full_decode='passed',model_sha256=hashes['master'],video_sha256=digest(output),model=director['model'],voice=director['voice'],spoken_seconds=spoken,visual_acceptance='pending user review',cad_regenerated=False,queue_resumed=False)
    (folder/f'{mode}-verification.json').write_text(json.dumps(report,indent=2)); print('COMPLETE',output,flush=True)
if __name__=='__main__': main()
