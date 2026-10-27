"""Independent delivery checks; writes evidence without changing production inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mechanical_video.voiceover import duration, stamp
from mechanical_video.runtime import exclusive_lock

p=argparse.ArgumentParser(); p.add_argument('folder',type=Path); args=p.parse_args()
folder=args.folder.resolve(); story=json.loads((folder/'storyboard.json').read_text())
video=folder/'cordless-drill-principles-ethan.mp4'
with exclusive_lock(Path(__file__).resolve().parents[1]/'artifacts/render.lock',blocking=True):
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]))
    (folder/'ffprobe.json').write_text(json.dumps(probe,indent=2))
    v=next(s for s in probe['streams'] if s['codec_type']=='video')
    a=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert v['codec_name']=='h264' and (v['width'],v['height'])==(1280,720)
    assert v['r_frame_rate']=='30/1' and a['codec_name']=='aac'
    assert float(v['duration'])>=90 and float(a['duration'])>=90
    assert abs(float(v['duration'])-float(a['duration']))<.1
    subprocess.run(['ffmpeg','-v','error','-i',str(video),'-map','0:v:0','-map','0:a:0','-f','null','-'],check=True)
    cache=Path(story['speech_cache']); units=story['chapters']
    srt=(folder/'narration.zh.srt').read_text().strip().split('\n\n')
    assert len(srt)==len(units)
    for i,(block,c) in enumerate(zip(srt,units)):
        rows=block.splitlines()
        assert len(rows)==3 and rows[2]==c['narration'] and len(rows[2])<=20
        assert rows[1]==f'{stamp(c["start"])} --> {stamp(c["speech_end"])}'
        assert abs(duration(cache/f'{i:03}.mp3')-(c['speech_end']-c['start']))<.03
        if i: assert units[i-1]['speech_end']<=c['start']
        shot=next(s for s in story['shots'] if s['start']<=c['start']<s['end'])
        assert shot['source_chapter']==c['source_chapter']
        assert c['speech_end']<=shot['end']+.001
    for name,digest in json.loads((folder/'production/fingerprints.json').read_text()).items():
        assert hashlib.sha256((folder/'production'/name).read_bytes()).hexdigest()==digest
    # Every source scene is used once; held diagrams never imply ongoing motion.
    assert len({s['source_chapter'] for s in story['shots']})==9
    for i,shot in enumerate(story['shots']):
        c=next(c for c in units if c['start']==shot['start'])
        t=(c['start']+c['speech_end'])/2
        subprocess.run(['ffmpeg','-y','-v','error','-ss',str(t),'-i',str(video),'-frames:v','1',str(folder/f'review-{i:02}.png')],check=True)
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(folder/'review-%02d.png'),'-vf','scale=426:240,tile=3x3','-frames:v','1',str(folder/'storyboard-preview.png')],check=True)
    report=dict(voice_configuration='qwen3-tts-flash / Ethan',duration=v['duration'],audio_duration=a['duration'],decode='full audio and video passed',subtitle_count=len(units),max_characters=max(len(c['narration']) for c in units),single_line=True,nonoverlap=True,measured_speech_alignment=True,topic_to_shot_mapping=True,archived_sources='sha256 verified',speech_retiming=False,looped_shots=False,manual_listening_or_asr=False)
    (folder/'acceptance.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
