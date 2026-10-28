"""Independent Blender acceptance of the saved documentary scene."""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix,Vector
from bpy_extras.object_utils import world_to_camera_view

job_path=Path(sys.argv[sys.argv.index('--')+1]); job=json.loads(job_path.read_text())
folder=Path(job['folder']); model=json.loads(Path(job['manifest']).read_text())
motion=json.loads((folder/'motion_audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(folder/'scene.blend'))
scene=bpy.context.scene
assert scene['source_model_sha256']==job['model_sha256']
objects={obj['part_id']:obj for obj in scene.objects if 'part_id' in obj}
assert set(objects)=={part['id'] for part in model['parts']}
baseline={}
scene.frame_set(1)
for part in model['parts']:
    obj=objects[part['id']]; expected=Matrix(part['matrix_mm']); expected.translation*=.001
    assert max(abs(obj.matrix_world[i][j]-expected[i][j]) for i in range(4) for j in range(4))<2e-5,part['id']
    assert len(obj.data.polygons)>0,part['id']
    baseline[part['id']]=obj.matrix_world.translation.copy()
changed=set(); maximum=0; projected_min=Vector((1,1)); projected_max=Vector((0,0))
for frame in motion['camera_fit_frames']:
    scene.frame_set(frame); bpy.context.view_layer.update()
    for identity,obj in objects.items():
        displacement=(obj.matrix_world.translation-baseline[identity]).length
        if displacement>1e-6: changed.add(identity)
        maximum=max(maximum,displacement)
        for corner in obj.bound_box:
            point=world_to_camera_view(scene,scene.camera,obj.matrix_world@Vector(corner))
            assert -.0001<=point.x<=1.0001 and -.0001<=point.y<=1.0001 and point.z>0,(frame,identity,list(point))
            projected_min.x=min(projected_min.x,point.x); projected_min.y=min(projected_min.y,point.y)
            projected_max.x=max(projected_max.x,point.x); projected_max.y=max(projected_max.y,point.y)
assert changed and maximum>.005
scene.frame_set(scene.frame_end)
assert all((obj.matrix_world.translation-baseline[identity]).length<1e-6 for identity,obj in objects.items())
result=dict(passed=True,source_model_sha256=job['model_sha256'],parts=len(objects),
    native_initial_placements='matched source occurrence matrices',native_end_placements='restored',
    sampled_frames=motion['camera_fit_frames'],moving_parts=len(changed),maximum_displacement_m=maximum,
    projected_bounds=[list(projected_min),list(projected_max)],all_sampled_cad_bounds_in_frame=True)
(folder/'native-validation.json').write_text(json.dumps(result,indent=2))
print('NATIVE_SCENE_ACCEPTED',len(objects),'parts',len(changed),'moving',flush=True)
