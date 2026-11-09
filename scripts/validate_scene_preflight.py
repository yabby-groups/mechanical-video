"""Blender-only regression fixture: does not render or alter production scenes."""
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from mechanical_video.scene_preflight import audit, verify
from mechanical_video.scene_fidelity import file_ref

out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(exist_ok=False)
# If audit accidentally calls rendering, fail instead of rendering a fixture.
def prohibit_render(*args, **kwargs):
    raise RuntimeError('Render forbidden in preflight regression')
bpy.app.handlers.render_pre.append(prohibit_render)
results=[]
for case in ['clear','shell-occluded','offscreen','too-small','disconnected','no-motion']:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.render.resolution_x=600;scene.render.resolution_y=600;scene.render.resolution_percentage=100
    bpy.ops.object.camera_add(location=(0,-8,0));camera=bpy.context.object;camera.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=6;scene.camera=camera
    bpy.ops.mesh.primitive_cube_add(size=1);target=bpy.context.object;target.name='button'
    link=bpy.data.objects.new('link',None);scene.collection.objects.link(link)
    if case=='shell-occluded':
        bpy.ops.mesh.primitive_cube_add(size=3,location=(0,-3,0));bpy.context.object.name='housing'
    def pose(frame):
        target.location.x=10 if case=='offscreen' else 0 if case=='no-motion' else frame*.1
        target.scale=(.001,)*3 if case=='too-small' else (1,)*3
        link.location=target.location
        if case=='disconnected':link.location.x+=1
    policy={'schema_version':1,'pose_mode':'renderer_callback','requirements':[{'id':'external-control','frames':[1,3],'motion_object':'button','min_motion':.05,'targets':[{'object':'button','point':[0,-.5,0],'min_pixels':40,'tolerance':.001}],'connections':[{'a':{'object':'button','point':[0,0,0]},'b':{'object':'link','point':[0,0,0]},'max_distance':.01}]}]}
    policy_path=out/(case+'-policy.json');policy_path.write_text(json.dumps(policy))
    report=audit(scene,policy_path,__file__,__file__,out/(case+'.json'),pose=pose)
    assets={k:v for k,v in report['inputs'].items()}
    valid=verify(report,assets,['external-control'])
    expected='PASS' if case=='clear' else 'BLOCKED'
    assert report['status']==expected,(case,report['failures'])
    assert valid==(case=='clear'),case
    assert report['coverage']=={'external-control':[1,2,3]}
    assert scene.frame_current==1
    results.append({'case':case,'status':report['status'],'verified':valid,'failures':report['failures']})
(out/'results.json').write_text(json.dumps({'status':'PASS','cases':results,'render_calls':0},indent=2))
print('PRE_RENDER_REGRESSION_PASS',json.dumps(results),flush=True)
