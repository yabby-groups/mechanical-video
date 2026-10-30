"""Immutable local visual test: approved Kai is reused by downstream Editor."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from mechanical_video.runtime import exclusive_lock,require_metal_device,GPUUnavailable

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','keyframes','render']);a=p.parse_args()
 source=Path(__file__).resolve().parent
 manifest=ROOT/'series/3d-printer-v2/models/source-repair-280890c41faa1c14/assembly.json'
 scene=ROOT/'series/3d-printer-v2/revisions/EP02/source-corrected-adapter-20261030/corrected-source.blend'
 baseline=ROOT/'series/3d-printer-v2/revisions/EP01/286fbb6553fde95a5e0d'
 files={f.name:digest(f) for f in sorted(source.glob('*.py'))}
 inputs={'model':digest(manifest),'scene':digest(scene),'baseline_video':digest(baseline/'EP01.mp4'),'narration':digest(baseline/'narration.wav'),'mix':digest(baseline/'mix.wav'),'subtitles':digest(baseline/'narration.zh.srt')}
 key=hashlib.sha256(json.dumps({'renderer':files,'inputs':inputs},sort_keys=True).encode()).hexdigest()[:20]
 folder=ROOT/'series/3d-printer-v2/revisions/EP01/data-driven-20261030/visual'/key
 archive=folder/'renderer';archive.mkdir(parents=True,exist_ok=True)
 for name,expected in files.items():
  target=archive/name
  if target.exists():assert digest(target)==expected,'Archived script changed'
  else:target.write_bytes((source/name).read_bytes())
 job={'folder':str(folder),'parts':json.loads(manifest.read_text())['parts'],'model_sha256':inputs['model'],'source_scene':str(scene),'source_scene_sha256':inputs['scene'],'end_frame':1080,'keyframes':[1,151,271,361,541,631,691,811,901,1021,1080]}
 def write(name,data): (folder/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 if not (folder/'job.json').exists():write('job.json',job)
 else:assert json.loads((folder/'job.json').read_text())==job
 write('fingerprints.json',{'renderer':files,'inputs':inputs,'scope':'0–36s local visual-only B; approved Kai assets unchanged; no full production/publication','native':{'width':540,'height':960,'fps':30}})
 print(folder,flush=True)
 if a.stage=='prepare':return
 state=folder/'status.json'
 if state.exists() and json.loads(state.read_text()).get('status')=='blocked':raise RuntimeError('Blocked render preserved; explicit investigated recovery required')
 try:
  require_metal_device()
  with exclusive_lock(ROOT/'artifacts/render.lock'):
   write('status.json',{'status':'running','stage':a.stage,'task_id':key})
   with (folder/(a.stage+'-blender.log')).open('a') as log:
    result=subprocess.run(['/Applications/Blender.app/Contents/MacOS/Blender','-b','-t','4','--python-exit-code','1','--python',str(archive/'scene.py'),'--',str(folder/'job.json'),a.stage],stdout=log,stderr=subprocess.STDOUT)
   if result.returncode:
    write('status.json',{'status':'blocked','stage':a.stage,'returncode':result.returncode,'task_id':key});raise RuntimeError('Render failed; preserved without automatic retry')
   write('status.json',{'status':'visual_frames_complete','stage':a.stage,'task_id':key,'qa':'NEEDS_REVIEW'})
 except GPUUnavailable:
  write('status.json',{'status':'gpu_unavailable','stage':a.stage,'attempt_consumed':False,'task_id':key});raise
 print('COMPLETE',a.stage,flush=True)
if __name__=='__main__':main()
