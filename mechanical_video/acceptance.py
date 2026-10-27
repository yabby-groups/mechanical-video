"""Acceptance of real rendered assets, serialized with rendering itself."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from .cli import ROOT,connect,verify
from .catalog import generate
from .runtime import caption_video, render_sources

def accept(root,wait=False):
    root.mkdir(parents=True,exist_ok=True)
    lock=(root/'render.lock').open('w'); deadline=time.time()+7200
    while True:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB); break
        except BlockingIOError:
            if not wait or time.time()>deadline: raise RuntimeError('Renderer active; run acceptance --wait or wait for the queue')
            time.sleep(5)
    con=connect(root); rows=con.execute("SELECT * FROM jobs WHERE state='done' OR (state='failed' AND error LIKE 'Acceptance: %') ORDER BY updated").fetchall()
    blender=os.environ.get('BLENDER_BIN') or shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender'
    reports=[]; failures=[]
    for row in rows:
        spec=json.loads(row['spec']); folder=Path(spec['directory'])
        try:
            with (folder/'scene-audit.log').open('w') as log:
                subprocess.run([blender,'-b','--python-exit-code','1','--python',str(render_sources(folder,spec)/'audit_scene.py'),'--',str(folder)],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=120)
            caption_video(folder,spec); report=verify(folder/'video.mp4',spec)
            reports.append({'id':row['id'],'template':spec['template'],'video':str(folder/'video.mp4'),'scene':str(folder/'scene.blend'),'verification':report,'scene_checks':json.loads((folder/'scene.validation.json').read_text())})
            con.execute("UPDATE jobs SET state='done',error=NULL WHERE id=?",(row['id'],)); con.commit()
            print('ACCEPTED',row['id'],spec['template'],flush=True)
        except Exception as exc:
            failures.append({'id':row['id'],'error':str(exc)})
            con.execute("UPDATE jobs SET state='failed',error=?,attempts=0 WHERE id=?",('Acceptance: '+str(exc),row['id'])); con.commit()
            print('REJECTED',row['id'],str(exc),flush=True)
    result={'accepted':len(reports),'failures':failures,'outputs':reports}
    (root/'acceptance.json').write_text(json.dumps(result,indent=2)); generate(root)
    con.close(); lock.close()
    if failures: raise RuntimeError('Scene acceptance rejected outputs; inspect scene-audit.log and acceptance.json')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--wait',action='store_true'); a=p.parse_args(); accept(ROOT/'artifacts',a.wait)
