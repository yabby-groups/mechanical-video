"""Create an isolated short narration edit from the corrected EP01 frames."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from mechanical_video.runtime import exclusive_lock

SOURCE=ROOT/'series/3d-printer-v2/revisions/EP01/d5ce7c04cb16858e806f'
SPEECH='两颗齿轮夹住线材。齿轮一转，旋转就变成了向下的推力。'
CAPTIONS=['两颗齿轮夹住线材。','齿轮一转，','旋转就变成了向下的推力。']
START=5.5


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, **kwargs):
    subprocess.run(list(map(str,args)),check=True,**kwargs)


def stamp(seconds):
    ms=round(seconds*1000)
    h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def main():
    source_report=json.loads((SOURCE/'production-verification.json').read_text())
    assert source_report['passed'] and source_report['full_decode']=='passed'
    assert digest(SOURCE/'EP01.mp4')==source_report['video_sha256']
    frames=[SOURCE/'frames'/f'{n:06}.jpg' for n in range(1,541)]
    assert all(p.is_file() and p.read_bytes().endswith(b'\xff\xd9') for p in frames)
    script=Path(__file__).resolve()
    identity=dict(script=digest(script),source_video=source_report['video_sha256'],
                  source_foley=digest(SOURCE/'foley.wav'),speech=SPEECH,model='qwen3-tts-flash',voice='Ryan')
    key=hashlib.sha256(json.dumps(identity,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:20]
    folder=ROOT/'series/3d-printer-v2/experiments'/f'disassembly-feed-{key}'
    archive=folder/'renderer'; archive.mkdir(parents=True,exist_ok=True)
    target=archive/'run.py'
    if target.exists(): assert target.read_bytes()==script.read_bytes()
    else: target.write_bytes(script.read_bytes())
    (archive/'fingerprints.json').write_text(json.dumps(identity,ensure_ascii=False,indent=2))
    (folder/'source-frames.json').write_text(json.dumps(dict(folder=str(SOURCE),frames={p.name:digest(p) for p in frames}),indent=2))
    print(folder,flush=True)
    output=folder/'disassembly-feed.mp4'
    if output.exists():
        assert json.loads((folder/'validation.json').read_text())['video_sha256']==digest(output)
        print('PRESERVED',output,flush=True); return
    voice=folder/'ryan.mp3'; marker=folder/'ryan.submitted'
    if not voice.exists():
        if marker.exists(): raise RuntimeError('Uncertain previous speech request; inspect before retrying')
        marker.write_text('submitted\n')
        run([ROOT/'.venv/bin/python',ROOT/'.agents/skills/audiogen/scripts/audio_gen.py','--text',SPEECH,'--model','qwen3-tts-flash','--voice','Ryan','--out',voice])
        marker.unlink()
    length=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(voice)]))
    assert length>0 and START+length<18 and ''.join(CAPTIONS)==SPEECH
    assert all(len(c)<=20 and '\n' not in c for c in CAPTIONS)
    cursor=START; blocks=[]
    for i,caption in enumerate(CAPTIONS):
        end=cursor+length*len(caption)/len(SPEECH)
        blocks.append(f'{i+1}\n{stamp(cursor)} --> {stamp(end)}\n{caption}')
        cursor=end
    (folder/'narration.zh.srt').write_text('\n\n'.join(blocks)+'\n')
    (folder/'narration.json').write_text(json.dumps(dict(text=SPEECH,model='qwen3-tts-flash',voice='Ryan',start=START,duration=length,caption_timing='proportional approximation'),ensure_ascii=False,indent=2))
    label="drawtext=fontfile='/System/Library/Fonts/STHeiti Medium.ttc':text='拆解与送料示意 · 合成拟音':fontsize=17:fontcolor=white@0.65:x=(w-tw)/2:y=h-45"
    vf=f"scale=720:1280,subtitles='{folder/'narration.zh.srt'}':force_style='FontName=Heiti SC,FontSize=8,MarginV=35',"+label
    with exclusive_lock(ROOT/'artifacts/render.lock',blocking=True):
        run(['ffmpeg','-y','-v','error','-framerate','30','-start_number','1','-i',SOURCE/'frames/%06d.jpg','-i',SOURCE/'foley.wav','-i',voice,'-filter_complex',f'[1:a]volume=0.7[fx];[2:a]adelay={round(START*1000)}:all=1[voice];[fx][voice]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.9[a]','-map','0:v','-map','[a]','-vf',vf,'-c:v','libx264','-threads','4','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-t','18','-movflags','+faststart',output])
        run(['ffmpeg','-v','error','-i',output,'-f','null','-'])
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]))
    v=next(s for s in probe['streams'] if s['codec_type']=='video'); a=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'],v['codec_name'],v['r_frame_rate'],int(v['nb_frames']),a['codec_name'])==(720,1280,'h264','30/1',540,'aac')
    assert abs(float(probe['format']['duration'])-18)<.1
    report=dict(passed=True,seconds=18,full_decode='passed',video_sha256=digest(output),source_revision=str(SOURCE),source_video_sha256=source_report['video_sha256'],visual='existing corrected EP01 frames, no new animation',voice='Ryan',model='qwen3-tts-flash',narration_seconds=length,caption_timing='proportional approximation',sound='synthetic foley',visual_and_audio_acceptance='pending user review')
    (folder/'validation.json').write_text(json.dumps(report,indent=2))
    print('COMPLETE',output,flush=True)


if __name__=='__main__': main()
