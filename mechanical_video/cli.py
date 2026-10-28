import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
from .model import build
from .config import vision_model

TEMPLATES=['overview','shell','internals','explode','gears','closeup','transparent','assembly','working','explanation']
ROOT=Path(__file__).resolve().parents[1]

def connect(root):
    root.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(root/'queue.sqlite'); db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, spec TEXT, state TEXT, attempts INTEGER DEFAULT 0, error TEXT, updated REAL)')
    return db

def enqueue(root,manifest,templates,portrait=False,production=False,seconds=5,engine="eevee",storyboard=None):
    import math
    from .runtime import source_fingerprints,snapshot_sources
    if not math.isfinite(seconds) or not 1/30 <= seconds <= 120: raise ValueError('seconds must be finite and between 1/30 and 120')
    seconds=round(seconds*30)/30
    if seconds.is_integer(): seconds=int(seconds)
    if not templates or any(t not in TEMPLATES for t in templates):
        raise ValueError('Select at least one supported template')
    product=json.loads(manifest.read_text()).get('product','planetary_reducer')
    if product=='cordless_drill' and any(t in ('gears','working','closeup') for t in templates):
        raise ValueError('Drill supports static/disassembly themes; reducer-specific gear simulation and sun closeup are unavailable')
    db=connect(root)
    results=[]
    for template in templates:
        spec=dict(manifest=str(manifest.resolve()),template=template,seconds=seconds,
                  width=(1080 if production else 720) if portrait else (1920 if production else 1280),
                  height=(1920 if production else 1280) if portrait else (1080 if production else 720))
        if storyboard is not None:
            if product!='cordless_drill' or template!='explanation':
                raise ValueError('Storyboard requires cordless_drill explanation')
            spec['storyboard']=storyboard
        if engine!='eevee': spec['engine']=engine
        spec['renderer_files']=source_fingerprints()
        spec['model_hash']=hashlib.sha256(manifest.read_bytes()).hexdigest()
        key=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()[:20]
        spec['directory']=str((root/'videos'/key).resolve())
        snapshot_sources(Path(spec['directory']),spec['renderer_files'])
        cursor=db.execute('INSERT OR IGNORE INTO jobs(id,spec,state,updated) VALUES(?,?,?,?)',(key,json.dumps(spec),'pending',time.time()))
        results.append({'id':key,'template':template,'created':cursor.rowcount==1})
        print(key,template)
    db.commit(); db.close()
    return results

def verify(path, spec=None):
    result=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
    stream=next(s for s in result['streams'] if s['codec_type']=='video')
    assert stream['codec_name']=='h264'
    if spec:
        assert (stream['width'],stream['height'])==(spec['width'],spec['height'])
        assert abs(float(result['format']['duration'])-spec['seconds'])<.1
        assert stream['r_frame_rate']=='30/1'
    subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],check=True,stdout=subprocess.DEVNULL)
    report=dict(codec=stream['codec_name'],width=stream['width'],height=stream['height'],duration=result['format']['duration'],frames=stream.get('nb_frames'),decode='passed')
    path.with_suffix('.verification.json').write_text(json.dumps(report,indent=2))
    return report

def worker(root,watch=False,retries=3):
    """One queue consumer; rendering and acceptance share a separate short lease."""
    from .runtime import exclusive_lock
    root.mkdir(parents=True,exist_ok=True)
    with exclusive_lock(root/'worker.lock'):
        _consume(root,watch,retries)


def _consume(root,watch,retries):
    from .runtime import exclusive_lock, render_sources, caption_video
    db=connect(root)
    with exclusive_lock(root/'render.lock',blocking=True):
        db.execute("UPDATE jobs SET state='pending' WHERE state='running'"); db.commit()
    blender=os.environ.get('BLENDER_BIN') or shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender'
    try:
        while True:
            row=db.execute("SELECT * FROM jobs WHERE state IN ('pending','failed') AND attempts < ? ORDER BY updated LIMIT 1",(retries,)).fetchone()
            if row is None:
                if watch: time.sleep(5); continue
                break
            with exclusive_lock(root/'render.lock',blocking=True):
                spec=json.loads(row['spec']); folder=Path(spec['directory']); folder.mkdir(parents=True,exist_ok=True)
                job=folder/'job.json'; job.write_text(json.dumps(spec,indent=2))
                db.execute("UPDATE jobs SET state='running',attempts=attempts+1,updated=? WHERE id=?",(time.time(),row['id'])); db.commit()
                started=time.monotonic()
                try:
                    from PIL import Image
                    sources=render_sources(folder,spec)
                    if hashlib.sha256(Path(spec['manifest']).read_bytes()).hexdigest()!=spec['model_hash']:
                        raise ValueError('Model manifest changed after enqueue; enqueue a new task')
                    for frame_file in (folder/'frames').glob('*.png'):
                        try:
                            with Image.open(frame_file) as image: image.verify()
                        except Exception: frame_file.unlink()
                    with (folder/'blender.log').open('a') as log:
                        subprocess.run([blender,'-b','--python-exit-code','1','-t','6','--python',str(sources/'blender_scene.py'),'--',str(job)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=7200)
                        subprocess.run([blender,'-b','--python-exit-code','1','--python',str(sources/'audit_scene.py'),'--',str(folder)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
                    video=folder/'video.mp4'; temp=folder/'encoding.mp4'
                    subprocess.run(['ffmpeg','-y','-v','error','-framerate','30','-start_number','1','-i',str(folder/'frames/%04d.png'),'-frames:v',str(int(spec['seconds']*30)),'-c:v','libx264','-threads','4','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],check=True)
                    verify(temp,spec); temp.replace(video)
                    caption_video(folder,spec); verify(video,spec)
                    temp.with_suffix('.verification.json').unlink(missing_ok=True)
                    (folder/'metrics.json').write_text(json.dumps({'wall_seconds':round(time.monotonic()-started,3),'engine':spec.get('engine','eevee'),'frames':int(spec['seconds']*30)},indent=2))
                    db.execute("UPDATE jobs SET state='done',error=NULL,updated=? WHERE id=?",(time.time(),row['id']))
                    print('DONE',video,flush=True)
                except Exception as exc:
                    db.execute("UPDATE jobs SET state='failed',error=?,updated=? WHERE id=?",(str(exc),time.time(),row['id']))
                    print('FAILED',row['id'],str(exc),flush=True)
                db.commit()
        failures=db.execute("SELECT count(*) FROM jobs WHERE state='failed'").fetchone()[0]
        if failures: raise RuntimeError(f'{failures} failed tasks; inspect status and blender.log')
    finally:
        db.close()

def analyze(image, root):
    import requests
    from PIL import Image
    with Image.open(image) as im:
        if im.width*im.height > 24_000_000: raise ValueError('Image exceeds 24 megapixels; resize before analysis')
        im.verify()
    digest=hashlib.sha256(image.read_bytes()).hexdigest(); folder=root/'inputs'/digest; folder.mkdir(parents=True,exist_ok=True)
    shutil.copy2(image,folder/image.name)
    endpoint=os.environ.get('VISION_ENDPOINT'); model=vision_model(); key=os.environ.get('VISION_API_KEY')
    if not endpoint:
        raise RuntimeError('Image saved. Configure VISION_ENDPOINT (chat/completions URL) and optional VISION_API_KEY; no image recognition result has been fabricated.')
    import mimetypes
    uri='data:'+ (mimetypes.guess_type(image.name)[0] or 'image/png')+';base64,'+base64.b64encode(image.read_bytes()).decode()
    prompt='Analyze this mechanical product. Return JSON only: product_type, supported_family (planetary_reducer, cordless_drill or unsupported), confidence (0..1), visible_features list, inferred_parts list, uncertain_details list, parameters {module: number}. Never claim hidden geometry is observed. Module is an explicitly inferred estimate in mm.'
    response=requests.post(endpoint,headers={'Authorization':f'Bearer {key}'} if key else {},json={'model':model,'messages':[{'role':'user','content':[{'type':'text','text':prompt},{'type':'image_url','image_url':{'url':uri}}]}]},timeout=120)
    response.raise_for_status(); content=response.json()['choices'][0]['message']['content'].strip()
    if content.startswith('```'): content=content.split('\n',1)[1].rsplit('```',1)[0]
    result=json.loads(content)
    if result.get('supported_family') not in ['planetary_reducer','cordless_drill','unsupported']: raise ValueError('Invalid model family')
    result['source_sha256']=digest; result['internal_geometry_status']='inferred'
    (folder/'analysis.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
    if result['supported_family']=='cordless_drill':
        from .drill import build as build_drill
        return build_drill(root)
    if result['supported_family']!='planetary_reducer': raise ValueError('Recognized product is outside implemented CAD families; analysis saved, no substitute model created')
    return build(root,result.get('parameters',{}))

def main():
    if len(sys.argv)>1 and sys.argv[1]=='series':
        from .series import main as series_main
        return series_main(sys.argv[2:])
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,default=ROOT/'artifacts')
    sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('model'); s.add_argument('--family',choices=['planetary_reducer','cordless_drill'],default='planetary_reducer'); s.add_argument('--module',type=float,default=2); sub.add_parser('status'); sub.add_parser('retry')
    for name in ['batch','demo','image']:
        s=sub.add_parser(name); s.add_argument('--portrait',action='store_true'); s.add_argument('--production',action='store_true'); s.add_argument('--seconds',type=float,default=5); s.add_argument('--engine',choices=['eevee','cycles'],default='eevee'); s.add_argument('--templates',nargs='+',choices=TEMPLATES,default=TEMPLATES if name=='batch' else ['shell','explode'])
        if name=='image': s.add_argument('path',type=Path)
        else: s.add_argument('--module',type=float,default=2)
    s=sub.add_parser('worker'); s.add_argument('--watch',action='store_true')
    s=sub.add_parser('verify'); s.add_argument('path',type=Path)
    a=p.parse_args(); a.root=a.root.resolve(); a.root.mkdir(parents=True,exist_ok=True)
    if a.command=='model':
        if a.family=='cordless_drill':
            from .drill import build as build_drill
            print(build_drill(a.root))
        else: print(build(a.root,{'module':a.module} if a.module!=2 else {}))
    elif a.command in ['batch','demo','image']:
        manifest=analyze(a.path,a.root) if a.command=='image' else build(a.root,{'module':a.module} if a.module!=2 else {})
        enqueue(a.root,manifest,a.templates,a.portrait,a.production,a.seconds,a.engine)
        if a.command=='demo': worker(a.root)
    elif a.command=='worker': worker(a.root,a.watch)
    elif a.command=='verify': print(json.dumps(verify(a.path),indent=2))
    elif a.command=='retry':
        db=connect(a.root); db.execute("UPDATE jobs SET attempts=0,state='pending' WHERE state='failed'"); db.commit(); db.close()
    elif a.command=='status':
        db=connect(a.root)
        for row in db.execute('SELECT id,state,attempts,error FROM jobs'): print(dict(row))
if __name__=='__main__': main()
