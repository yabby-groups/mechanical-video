"""Compose a measured storyboard voice track and burn readable Chinese captions."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import textwrap
from .cli import verify
from .voiceover import duration, stamp

def ass_stamp(t):
    cs=round(t*100)
    return f'{cs//360000:01}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'

def caption_lines(text):
    if not text or len(text)>20 or any(c in text for c in ('\n','\r')):
        raise ValueError('Generate one speech clip per single-line caption of at most 20 characters')
    return [text]

def prepare_audio(story_path):
    story_path=Path(story_path).resolve(); folder=story_path.parent
    story=json.loads(story_path.read_text()); cache=Path(story['speech_cache'])
    segments=[]; subtitles=[]; dialogues=[]
    for i,c in enumerate(story['chapters']):
        clip=cache/f'{i:03}.mp3'; actual=duration(clip)
        if abs(actual-(c['speech_end']-c['start']))>.03:
            raise ValueError('Audio clip duration changed since storyboard creation')
        segment=folder/f'segment-{i:02}.wav'; length=c['end']-c['start']
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(clip),'-af',f'apad=whole_dur={length:.9f}',
            '-t',str(length),'-ar','48000','-ac','1',str(segment)],check=True)
        segments.append(segment)
        lines=caption_lines(c['narration'])
        text='\n'.join(lines)
        subtitles.append(f'{i+1}\n{stamp(c["start"])} --> {stamp(c["speech_end"])}\n{text}')
        escaped=text.replace('\\','\\\\').replace('{','\\{').replace('}','\\}').replace('\n',r'\N')
        dialogues.append(f'Dialogue: 0,{ass_stamp(c["start"])},{ass_stamp(c["speech_end"])},Narration,,0,0,0,,{escaped}')
    listing=folder/'audio-concat.txt'; listing.write_text(''.join(f"file '{s.name}'\n" for s in segments))
    audio=folder/'narration.wav'
    subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','1','-i',str(listing),'-c:a','pcm_s16le',str(audio)],check=True)
    if abs(duration(audio)-story['chapters'][-1]['end'])>.03: raise ValueError('Composed narration duration mismatch')
    (folder/'narration.zh.srt').write_text('\n\n'.join(subtitles)+'\n',encoding='utf-8')
    ass='''[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Narration,Arial Unicode MS,30,&H00FFFFFF,&H00FFFFFF,&H00101822,&H90000000,0,0,0,0,100,100,0,0,1,2,1,2,80,80,34,1
Style: Caveat,Arial Unicode MS,20,&H00CBDAE6,&H00FFFFFF,&H00101822,&H90000000,0,0,0,0,100,100,0,0,1,1,0,9,50,45,28,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    ass+=f'Dialogue: 1,0:00:00.00,{ass_stamp(story["chapters"][-1]["end"])},Caveat,,0,0,0,,内部结构与尺寸均为推测\n'
    (folder/'captions.zh.ass').write_text(ass+'\n'.join(dialogues)+'\n',encoding='utf-8')
    return audio

def compose(video,story_path,output):
    video=Path(video).resolve(); story_path=Path(story_path).resolve(); output=Path(output).resolve()
    if output.exists() or video==output: raise ValueError('Choose a new output filename')
    audio=prepare_audio(story_path); folder=story_path.parent
    story=json.loads(story_path.read_text()); seconds=story['chapters'][-1]['end']
    titles=['外观与模型说明','移开电池包','拆分机壳','夹头与输出主轴','推测的减速机构','推测的电机','操作与控制部件','推测的电池内部','完整机械爆炸图']
    metadata=';FFMETADATA1\n'
    for i,c in enumerate(story['chapters']):
        title=c.get('title',titles[i % len(titles)])
        metadata+=f'[CHAPTER]\nTIMEBASE=1/1000\nSTART={round(c["start"]*1000)}\nEND={round(c["end"]*1000)}\ntitle={title}\n'
    (folder/'chapters.ffmeta').write_text(metadata,encoding='utf-8')
    temp=folder/'final-encoding.mp4'
    command=['ffmpeg','-y','-v','warning','-i',str(video),'-i',str(audio),
        '-i',str(folder/'chapters.ffmeta'),'-map_metadata','2','-map_chapters','2',
        '-map','0:v:0','-map','1:a:0','-vf','ass=captions.zh.ass:fontsdir=/System/Library/Fonts/Supplemental',
        '-af','loudnorm=I=-16:TP=-1.5:LRA=11','-c:v','libx264','-threads','4','-preset','medium','-crf','18',
        '-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000',
        '-metadata:s:a:0','language=zho','-t',str(seconds),'-movflags','+faststart',str(temp)]
    (folder/'composition-command.json').write_text(json.dumps(command,ensure_ascii=False,indent=2))
    with (folder/'composition.log').open('w') as log:
        subprocess.run(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,check=True)
    report=verify(temp,{'width':1280,'height':720,'seconds':seconds})
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(temp)]))
    stream=next(s for s in probe['streams'] if s['codec_type']=='audio')
    if stream['codec_name']!='aac' or abs(float(stream['duration'])-seconds)>.1: raise ValueError('Final audio mismatch')
    temp.replace(output); temp.with_suffix('.verification.json').unlink(missing_ok=True)
    report.update(audio='aac',sample_rate=stream['sample_rate'],audio_seconds=stream['duration'],
        narration_model='qwen3-tts-flash',voice='Ethan',language='zho',burned_subtitles=True,
        chapters=len(story['chapters']),spoken_seconds=story['spoken_seconds'])
    output.with_suffix('.verification.json').write_text(json.dumps(report,indent=2))
    # Preserve the exact composition source and reusable audio alongside the final film.
    archive=folder/'production'; archive.mkdir(exist_ok=True)
    for source in [Path(__file__),Path(__file__).with_name('drill_film.py'),Path(__file__).with_name('voiceover.py')]:
        target=archive/source.name
        if target.exists() and target.read_bytes()!=source.read_bytes(): raise ValueError('Production archive differs; choose new task folder')
        if not target.exists(): shutil.copy2(source,target)
    (archive/'fingerprints.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in archive.glob('*.py')},indent=2))
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--storyboard',type=Path,required=True)
    p.add_argument('--video',type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.video and a.output: print(json.dumps(compose(a.video,a.storyboard,a.output)))
    elif not a.video and not a.output: print(prepare_audio(a.storyboard))
    else: p.error('Both --video and --output are required for composition')

if __name__=='__main__': main()
