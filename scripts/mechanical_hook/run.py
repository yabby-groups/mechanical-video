"""Independent 15s action/foley test. Never resumes a rejected production queue."""
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT))
from mechanical_video.runtime import exclusive_lock

def run(args,**kw): subprocess.run(list(map(str,args)),check=True,**kw)

def main():
    source=ROOT/'scripts/mechanical_hook'
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.py')}
    key=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
    folder=ROOT/f'series/3d-printer-v2/experiments/mechanical-hook-{key}'
    archive=folder/'renderer'; archive.mkdir(parents=True,exist_ok=True)
    for p in source.glob('*.py'):
        q=archive/p.name
        if q.exists(): assert q.read_bytes()==p.read_bytes()
        else: q.write_bytes(p.read_bytes())
    (archive/'fingerprints.json').write_text(json.dumps(hashes,indent=2))
    master=ROOT/'series/3d-printer/master_assembly/assembly.json'
    job=dict(folder=str(folder),parts=json.loads(master.read_text())['parts'],model_sha256=hashlib.sha256(master.read_bytes()).hexdigest(),source_scene=str(ROOT/'series/3d-printer/renders/EP04/04fdabd9902948771c7e/scene.blend'))
    (folder/'job.json').write_text(json.dumps(job))
    pointer=ROOT/'series/3d-printer-v2/latest-mechanical-hook.json'
    pointer.write_text(json.dumps(dict(folder=str(folder),state='preview')))
    blender='/Applications/Blender.app/Contents/MacOS/Blender'
    with exclusive_lock(ROOT/'artifacts/render.lock',blocking=True):
        with (folder/'blender.log').open('a') as log:
            run([blender,'-b','-t','4','--python-exit-code','1','--python',archive/'scene.py','--',folder/'job.json','preview'],stdout=log,stderr=subprocess.STDOUT)
        pointer.write_text(json.dumps(dict(folder=str(folder),state='preview_ready')))
        deadline=time.monotonic()+600
        while not (folder/'preview-reviewed.json').exists():
            if time.monotonic()>deadline: raise RuntimeError('Preview review timeout')
            time.sleep(.5)
        pointer.write_text(json.dumps(dict(folder=str(folder),state='production')))
        with (folder/'blender.log').open('a') as log:
            run([blender,'-b','-t','4','--python-exit-code','1','--python',archive/'scene.py','--',folder/'job.json','production'],stdout=log,stderr=subprocess.STDOUT)
    spec=importlib.util.spec_from_file_location('hook_sound',archive/'sound.py')
    sound=importlib.util.module_from_spec(spec); spec.loader.exec_module(sound); sound.generate(folder/'foley.wav')
    output=folder/'mechanical-hook.mp4'
    label="drawtext=fontfile='/System/Library/Fonts/STHeiti Medium.ttc':text='源CAD · 局部近似 · 拆解与送料示意 · 合成拟音':fontsize=23:fontcolor=white@0.6:x=(w-tw)/2:y=h-65"
    run(['ffmpeg','-y','-v','error','-framerate','30','-i',folder/'frames/%06d.jpg','-i',folder/'foley.wav','-vf',label,'-c:v','libx264','-threads','4','-preset','fast','-crf','18','-pix_fmt','yuv420p','-af','loudnorm=I=-20:TP=-2:LRA=9','-c:a','aac','-b:a','192k','-t','15','-movflags','+faststart',output])
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]))
    v=next(s for s in probe['streams'] if s['codec_type']=='video'); a=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'],v['codec_name'],v['r_frame_rate'],a['codec_name'])==(1080,1920,'h264','30/1','aac')
    assert abs(float(probe['format']['duration'])-15)<.05
    run(['ffmpeg','-v','error','-i',output,'-f','null','-'])
    audit=json.loads((folder/'production-audit.json').read_text())
    assert len(audit['continuity'])==449 and audit['hard_cuts']==0
    report=dict(passed=True,duration=15,full_decode='passed',shots=1,hard_cuts=0,visibility_changes=0,continuity_max_camera_step=max(s['camera_step'] for s in audit['continuity']),narration=False,sound='Continuous procedural foley; no edit impacts or claimed recording',source_model_sha256=job['model_sha256'],video_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    (folder/'validation.json').write_text(json.dumps(report,indent=2))
    pointer.write_text(json.dumps(dict(folder=str(folder),state='complete')))
    print('COMPLETE',output,flush=True)

if __name__=='__main__': main()
