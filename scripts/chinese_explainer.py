"""Assemble a 90-second narrated edit from independently verified cached shots."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from mechanical_video.cli import ROOT, verify
from mechanical_video.voiceover import prepare, compose

def main():
    output=ROOT/'artifacts/机械拆解-90秒-中文.mp4'
    script=ROOT/'docs/narration-90s.zh.txt'
    lines,_,cache,clips=prepare(script,output)
    target=90
    spoken=sum(d for _,d in clips)
    if spoken>target: raise ValueError('Speech exceeds 90 seconds')
    shots=['1de3ee9b2ee856f321df','63187187e725d26bf3c4','f0d46d1190e78f6a4246',
           'b3d4dd3173474e8fdc16','b3d4dd3173474e8fdc16','f0d46d1190e78f6a4246',
           '3d2d54388d04dd774803','b3d4dd3173474e8fdc16','3d2d54388d04dd774803',
           '2252aec71e5bc4b2c7e4','1de3ee9b2ee856f321df']
    if len(lines)!=len(shots): raise ValueError('Update shot plan for the edited narration')
    folder=ROOT/'artifacts/videos/chinese-explainer-90s'
    folder.mkdir(parents=True,exist_ok=True)
    fingerprint=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    archive=folder/'director.py'
    if archive.exists() and hashlib.sha256(archive.read_bytes()).hexdigest()!=fingerprint:
        raise ValueError('Archived director differs; use a new production directory')
    if not archive.exists(): shutil.copy2(__file__,archive)
    gap=(target-spoken)/len(clips); timeline=[]; cursor=0; previous=0
    for i,(key,(_,length)) in enumerate(zip(shots,clips)):
        source=ROOT/'artifacts/videos'/key
        spec=json.loads((source/'job.json').read_text())
        report=json.loads((source/'video.verification.json').read_text())
        if report.get('decode')!='passed' or not (source/'scene.validation.json').is_file():
            raise ValueError(f'Shot not verified: {key}')
        cursor+=length+gap; end=round(cursor*30); frames=end-previous
        previous=end; segment=folder/f'shot-{i:02}.mp4'
        timeline.append({'text':lines[i],'source':key,'frames':frames,'speech_seconds':length,'pause_seconds':gap,'source_sha256':hashlib.sha256((source/'video.mp4').read_bytes()).hexdigest()})
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(source/'video.mp4'),'-map','0:v:0','-vf',f'setpts={(frames/30)/spec["seconds"]:.12f}*PTS,fps=30,tpad=stop_mode=clone:stop_duration=1','-frames:v',str(frames),'-an','-sn','-c:v','libx264','-threads','4','-preset','fast','-crf','20','-pix_fmt','yuv420p',str(segment)],check=True)
    (folder/'timeline.json').write_text(json.dumps({'duration':90,'fps':30,'director_sha256':fingerprint,'speech_cache':str(cache),'shots':timeline},ensure_ascii=False,indent=2))
    listing=folder/'shots.txt'; listing.write_text(''.join(f"file 'shot-{i:02}.mp4'\n" for i in range(len(shots))))
    base=folder/'video.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','1','-i',str(listing),'-c','copy','-movflags','+faststart',str(base)],check=True)
    verify(base,{'width':1280,'height':720,'seconds':90})
    compose(base,script,output)
    print(output)

if __name__=='__main__': main()
