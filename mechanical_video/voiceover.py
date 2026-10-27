"""Chinese voiceover using the project-local audiogen runner, with reusable clips."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

RUNNER=Path(__file__).resolve().parents[1]/'.agents/skills/audiogen/scripts/audio_gen.py'

def duration(path):
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)]))
    if not any(s['codec_type']=='audio' for s in data['streams']): raise ValueError('Audio stream missing')
    seconds=float(data['format']['duration'])
    if seconds<=0: raise ValueError('Audio is empty')
    subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],check=True)
    return seconds

def stamp(t):
    ms=round(t*1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'

def prepare(script,output,model='qwen3-tts-flash',voice='Roy'):
    output=output.resolve()
    lines=[line for line in script.read_text(encoding='utf-8').splitlines() if line.strip()]
    if not lines: raise ValueError('Narration script is empty')
    folder=output.parent/(output.stem+'.voiceover'); folder.mkdir(parents=True,exist_ok=True)
    identity={'lines':lines,'model':model,'voice':voice,'runner_sha256':hashlib.sha256(RUNNER.read_bytes()).hexdigest(),'endpoint':os.getenv('OPENAI_BASE_URL','').strip() or 'https://huabot.com/v1'}
    key=hashlib.sha256(json.dumps(identity,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:20]
    cache=folder/key; cache.mkdir(exist_ok=True)
    (cache/'script.txt').write_text('\n'.join(lines),encoding='utf-8')
    clips=[]
    for i,line in enumerate(lines):
        clip=cache/f'{i:03}.mp3'; text=cache/f'{i:03}.txt'; pending=cache/f'{i:03}.submitted'
        text.write_text(line,encoding='utf-8')
        if not clip.exists():
            if pending.exists(): raise RuntimeError(f'Uncertain prior speech submission: {pending}. Inspect before explicitly removing marker to retry.')
            if not os.getenv('OPENAI_API_KEY','').strip(): raise RuntimeError('Set OPENAI_API_KEY before generating audio')
            pending.touch()
            subprocess.run([sys.executable,str(RUNNER),'--text-file',str(text),'--model',model,'--voice',voice,'--out',str(clip)],check=True)
        clips.append((clip,duration(clip)))
    return lines,folder,cache,clips

def compose(video,script,output,model='qwen3-tts-flash',voice='Roy'):
    video=video.resolve(); output=output.resolve()
    if output.exists() or video==output: raise ValueError('Choose a new output filename')
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(video)]))
    target=float(probe['format']['duration'])
    lines,folder,cache,clips=prepare(script,output,model,voice)
    spoken=sum(d for _,d in clips)
    if spoken>target: raise ValueError(f'Narration lasts {spoken:.2f}s, exceeding video {target:.2f}s; shorten script or render a longer video')
    gap=(target-spoken)/len(clips); cursor=0; subtitles=[]; segments=[]
    for i,((clip,length),line) in enumerate(zip(clips,lines)):
        subtitles.append(f'{i+1}\n{stamp(cursor)} --> {stamp(cursor+length)}\n{line}')
        segment=cache/f'{i:03}.wav'
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(clip),'-af',f'apad=whole_dur={length+gap:.9f}','-t',str(length+gap),'-ar','48000','-ac','1',str(segment)],check=True)
        segments.append(segment); cursor+=length+gap
    listing=cache/'concat.txt'
    # Generated basenames avoid concat quoting problems with arbitrary task paths.
    listing.write_text(''.join(f"file '{p.name}'\n" for p in segments))
    audio=cache/'narration.wav'
    subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','1','-i',str(listing),'-c:a','pcm_s16le',str(audio)],check=True)
    srt=cache/'narration.zh.srt'; srt.write_text('\n\n'.join(subtitles)+'\n',encoding='utf-8')
    temporary=folder/'composing.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(video),'-i',str(audio),'-i',str(srt),'-map','0:v:0','-map','1:a:0','-map','2:0','-c:v','copy','-c:a','aac','-c:s','mov_text','-metadata:s:a:0','language=zho','-metadata:s:s:0','language=zho','-t',str(target),'-movflags','+faststart',str(temporary)],check=True)
    from .cli import verify
    report=verify(temporary)
    actual=duration(temporary)
    if abs(actual-target)>.1: raise ValueError('Composed duration mismatch')
    temporary.replace(output)
    temporary.with_suffix('.verification.json').unlink(missing_ok=True)
    output.with_suffix('.verification.json').write_text(json.dumps(report|{'audio':'aac','language':'zho','model':model,'voice':voice,'spoken_seconds':spoken,'cache':str(cache)},indent=2))
    return output

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('video',type=Path); p.add_argument('--script',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True); p.add_argument('--model',default='qwen3-tts-flash'); p.add_argument('--voice',default='Roy')
    a=p.parse_args(); print(compose(a.video,a.script,a.out,a.model,a.voice))

if __name__=='__main__': main()
