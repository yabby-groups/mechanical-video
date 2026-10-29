"""Render an isolated short print-birth experiment with archived inputs."""
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from mechanical_video.runtime import exclusive_lock


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, **kwargs):
    subprocess.run(list(map(str,args)),check=True,**kwargs)


def main():
    source=Path(__file__).resolve().parent
    master=ROOT/'series/3d-printer/master_assembly/assembly.json'
    scene=ROOT/'series/3d-printer/renders/EP04/04fdabd9902948771c7e/scene.blend'
    hashes={p.name:digest(p) for p in source.glob('*.py')}
    hashes.update(master=digest(master),source_scene=digest(scene))
    key=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:20]
    folder=ROOT/'series/3d-printer-v2/experiments'/f'print-birth-{key}'
    archive=folder/'renderer'; archive.mkdir(parents=True,exist_ok=True)
    for path in source.glob('*.py'):
        target=archive/path.name
        if target.exists():
            assert target.read_bytes()==path.read_bytes()
        else:
            target.write_bytes(path.read_bytes())
    (archive/'fingerprints.json').write_text(json.dumps(hashes,indent=2))
    job=dict(folder=str(folder),parts=json.loads(master.read_text())['parts'],model_sha256=hashes['master'],source_scene=str(scene),source_scene_sha256=hashes['source_scene'])
    (folder/'job.json').write_text(json.dumps(job))
    print(folder,flush=True)
    output=folder/'print-birth.mp4'
    if output.exists():
        report=json.loads((folder/'validation.json').read_text())
        assert report['video_sha256']==digest(output)
        print('PRESERVED',output,flush=True)
        return
    with exclusive_lock(ROOT/'artifacts/render.lock',blocking=True):
        with (folder/'blender.log').open('a') as log:
            run(['/Applications/Blender.app/Contents/MacOS/Blender','-b','-t','4','--python-exit-code','1','--python',archive/'scene.py','--',folder/'job.json','production'],stdout=log,stderr=subprocess.STDOUT)
    spec=importlib.util.spec_from_file_location('birth_sound',archive/'sound.py')
    sound=importlib.util.module_from_spec(spec); spec.loader.exec_module(sound)
    sound.generate(folder/'foley.wav')
    label="drawtext=fontfile='/System/Library/Fonts/STHeiti Medium.ttc':text='加速成型示意 · 合成拟音':fontsize=17:fontcolor=white@0.65:x=(w-tw)/2:y=h-45"
    run(['ffmpeg','-y','-v','error','-framerate','30','-i',folder/'frames/%06d.jpg','-i',folder/'foley.wav','-vf',label,'-c:v','libx264','-threads','4','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-t','16','-movflags','+faststart',output])
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(output)]))
    v=next(s for s in probe['streams'] if s['codec_type']=='video')
    a=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'],v['codec_name'],v['r_frame_rate'],int(v['nb_frames']),a['codec_name'])==(720,1280,'h264','30/1',480,'aac')
    assert abs(float(probe['format']['duration'])-16)<.1
    run(['ffmpeg','-v','error','-i',output,'-f','null','-'])
    audit=json.loads((folder/'production-audit.json').read_text())
    assert len(audit['continuity'])==len(audit['gear_continuity'])==479
    report=dict(passed=True,seconds=16,full_decode='passed',narration=False,sound='synthetic foley',visual_acceptance='pending user review',source_model_sha256=hashes['master'],video_sha256=digest(output),scope='accelerated illustrative deposition, not physical simulation')
    (folder/'validation.json').write_text(json.dumps(report,indent=2))
    print('COMPLETE',output,flush=True)


if __name__=='__main__':
    main()
