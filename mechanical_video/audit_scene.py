"""Independent saved-scene acceptance checks, executed inside Blender."""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
folder=Path(sys.argv[sys.argv.index('--')+1]); spec=json.loads((folder/'job.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(folder/'scene.blend'))
s=bpy.context.scene; cam=s.camera
parts=[o for o in s.objects if 'part_group' in o]; failures=[]
expected=len(json.loads(Path(spec['manifest']).read_text())['parts'])
if len(parts)!=expected: failures.append(f'Expected {expected} independent objects, found {len(parts)}')
if spec['template']=='explode' or spec.get('storyboard'):
    s.frame_set(1); initial={o.name:o.location.copy() for o in parts}
    s.frame_set(s.frame_end); deltas={o.name:o.location-initial[o.name] for o in parts}
    if sum(d.length>.01 for d in deltas.values())<10: failures.append('Too few independently moving parts')
    if max((d-deltas[parts[0].name]).length for d in deltas.values())<.1: failures.append('Only whole-model translation detected')
if s.render.fps!=30: failures.append('fps is not 30')
if spec.get('engine','eevee')=='cycles':
    if s.render.engine!='CYCLES' or s.cycles.device!='GPU': failures.append('Cycles GPU configuration mismatch')
elif s.render.engine not in ('BLENDER_EEVEE','BLENDER_EEVEE_NEXT'):
    failures.append('Eevee configuration mismatch')
if (s.render.resolution_x,s.render.resolution_y)!=(spec['width'],spec['height']): failures.append('Resolution mismatch')
frames=[1, max(1,s.frame_end//4),max(1,s.frame_end//2),max(1,int(s.frame_end*.8)),s.frame_end]
if spec.get('storyboard'):
    for chapter in spec['storyboard']['chapters']:
        first=max(1,round(chapter['start']*30)+1); last=min(s.frame_end,round(chapter['end']*30))
        frames.extend([first,(first+last)//2,last])
for frame in sorted(set(frames)):
    s.frame_set(frame); bpy.context.view_layer.update()
    for o in parts+[ob for ob in s.objects if ob.type=='FONT']:
        if o.hide_render: continue
        for corner in o.bound_box:
            q=world_to_camera_view(s,cam,o.matrix_world@Vector(corner))
            if not (-.005<=q.x<=1.005 and -.005<=q.y<=1.005 and q.z>0):
                failures.append(f'{o.name} outside camera at frame {frame}'); break
    if spec['template'] in ('gears','working'):
        for o in parts:
            if o.name.startswith('planet_') and not o.name.startswith('planet_pin'):
                nominal=math.hypot(*next(p['position'][:2] for p in json.loads(Path(spec['manifest']).read_text())['parts'] if p['name']==o.name))/100
                if abs(math.hypot(o.location.x,o.location.y)-nominal)>.001: failures.append(f'{o.name} orbit is not circular at frame {frame}')
if spec['template']=='overview':
    s.frame_set(1); first=cam.location.copy(); s.frame_set(s.frame_end//2)
    if (cam.location-first).length<2: failures.append('Overview camera does not complete a true orbit')
report={'parts':len(parts),'template':spec['template'],'bounds_and_motion':'passed' if not failures else 'failed','failures':list(dict.fromkeys(failures))}
(folder/'scene.validation.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report))
if failures: raise RuntimeError('Scene acceptance checks failed')
