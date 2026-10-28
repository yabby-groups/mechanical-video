"""Serialized preview/production and encode, followed by production-queue resume."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from mechanical_video.runtime import exclusive_lock

def run(args,**kwargs): subprocess.run(list(map(str,args)),check=True,**kwargs)

def main():
    source=ROOT/'scripts/visual_test'
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.py')}
    key=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
    folder=ROOT/f'series/3d-printer/experiments/visual-CW2-{key}'
    archive=folder/'renderer'; archive.mkdir(parents=True,exist_ok=True)
    for p in source.glob('*.py'):
        dest=archive/p.name
        if dest.exists(): assert dest.read_bytes()==p.read_bytes()
        else: dest.write_bytes(p.read_bytes())
    (archive/'fingerprints.json').write_text(json.dumps(hashes,indent=2))
    model=ROOT/'series/3d-printer/master_assembly/assembly.json'
    job=dict(folder=str(folder),model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),parts=json.loads(model.read_text())['parts'],source_scene=str(ROOT/'series/3d-printer/renders/EP04/04fdabd9902948771c7e/scene.blend'),duration=10,voice=None)
    (folder/'job.json').write_text(json.dumps(job))
    (ROOT/'series/3d-printer/experiments/latest-visual-test.json').write_text(json.dumps(dict(folder=str(folder),state='running')))
    blender='/Applications/Blender.app/Contents/MacOS/Blender'
    with exclusive_lock(ROOT/'artifacts/render.lock',blocking=True):
        for mode in ['preview','production']:
            with (folder/'blender.log').open('a') as log:
                run([blender,'-b','-t','4','--python-exit-code','1','--python',archive/'scene.py','--',folder/'job.json',mode],stdout=log,stderr=subprocess.STDOUT)
    font='/System/Library/Fonts/STHeiti Medium.ttc'
    output=folder/'visual-test.mp4'
    run(['ffmpeg','-y','-v','error','-framerate','30','-i',folder/'frames/%06d.jpg','-vf',f"drawtext=fontfile='{font}':text='源CAD · 拆解与转动为示意':fontsize=28:fontcolor=white@0.7:x=(w-tw)/2:y=h-90",'-c:v','libx264','-threads','4','-preset','fast','-crf','18','-pix_fmt','yuv420p','-t','10','-an','-movflags','+faststart',output])
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]))
    v=probe['streams'][0]; assert (v['width'],v['height'],v['codec_name'],v['r_frame_rate'])==(1080,1920,'h264','30/1')
    assert abs(float(probe['format']['duration'])-10)<.05
    run(['ffmpeg','-v','error','-i',output,'-f','null','-'])
    (folder/'validation.json').write_text(json.dumps(dict(passed=True,duration=10,full_decode='passed',audio='none',model_sha256=job['model_sha256'],video_sha256=hashlib.sha256(output.read_bytes()).hexdigest()),indent=2))
    (ROOT/'series/3d-printer/experiments/latest-visual-test.json').write_text(json.dumps(dict(folder=str(folder),state='complete')))
    print('COMPLETE',output,flush=True)

if __name__=='__main__':
    try: main()
    finally:
        # Preserve the user's original EP05-08 production request.
        log=(ROOT/'series/3d-printer/production-EP04-08.log').open('a')
        p=subprocess.Popen([sys.executable,'-u','-m','mechanical_video.cli','series','render','--episodes','5-8'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        print('RESUMED_PRODUCTION_PID',p.pid,flush=True)
