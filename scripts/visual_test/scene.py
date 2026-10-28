"""CW2 visual study using unchanged pinned CAD meshes; no inferred internals."""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector, Matrix

jobpath=Path(sys.argv[sys.argv.index('--')+1])
mode=sys.argv[sys.argv.index('--')+2]
job=json.loads(jobpath.read_text()); folder=Path(job['folder'])
bpy.ops.wm.open_mainfile(filepath=job['source_scene'])
scene=bpy.context.scene
scene.animation_data_clear()
keep=[]
for obj in list(scene.objects):
    if '/CW2_Assembly/' in obj.get('source_path',''):
        obj.animation_data_clear()
        # Restore original source occurrence transform, not the exploded film pose.
        part=next(p for p in job['parts'] if p['id']==obj['part_id'])
        matrix=Matrix(part['matrix_mm']); matrix.translation*=.001
        obj.parent=None; obj.matrix_world=matrix
        keep.append(obj)
    else: bpy.data.objects.remove(obj,do_unlink=True)
bpy.context.view_layer.update()
points=[o.matrix_world@Vector(c) for o in keep for c in o.bound_box]
low=Vector(tuple(min(p[i] for p in points) for i in range(3)))
high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
center=(low+high)/2; size=max(high-low)
origins={o.name:o.matrix_world.copy() for o in keep}

def material(name,color,metal=.0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    s=m.node_tree.nodes.get('Principled BSDF'); s.inputs['Base Color'].default_value=(*color,1)
    s.inputs['Metallic'].default_value=metal; s.inputs['Roughness'].default_value=.3
    return m
shell=material('graphite housing',(.045,.065,.085),.25)
gear=material('copper drive highlight',(.95,.28,.055),.65)
steel=material('satin steel',(.44,.57,.65),.75)
for obj in keep:
    obj.data=obj.data.copy(); obj.data.materials.clear()
    name=obj['source_path']
    obj.data.materials.append(gear if 'Gear' in name else shell if 'CW2_Printed' in name else steel)

scene.world.color=(.02,.02,.02)
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.012,.022,.035,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.4
bpy.ops.object.camera_add(); cam=bpy.context.object; scene.camera=cam
cam.data.type='ORTHO'; cam.data.lens=55
def aim(obj,target): obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()
for offset,power,scale in [((1,-2,3),.7,2),((-2,-1,.4),.45,1.5),((0,2,1.5),.85,1.2)]:
    bpy.ops.object.light_add(type='AREA',location=center+Vector(offset)*size)
    light=bpy.context.object; light.data.energy=power; light.data.shape='DISK'; light.data.size=size*scale; aim(light,center)
scene.render.resolution_x=1080; scene.render.resolution_y=1920
scene.render.resolution_percentage=35 if mode=='preview' else 100
scene.render.fps=30; scene.frame_end=300
scene.render.image_settings.file_format='JPEG'; scene.render.image_settings.quality=95
scene.render.film_transparent=False
try: scene.render.engine='BLENDER_EEVEE_NEXT'
except TypeError: scene.render.engine='BLENDER_EEVEE'
scene.render.image_settings.color_mode='RGB'
def smooth(x):
    x=max(0,min(1,x)); return x*x*(3-2*x)

def pose(frame):
    t=(frame-1)/30
    opening=smooth((t-1.2)/2.2)*(1-smooth((t-8)/1.8))
    yaw=-.15+.35*smooth(t/10)
    cam.location=center+Vector((math.sin(yaw)*2.5,-2.8,1.0))*size
    aim(cam,center+Vector((0,0,.015))*size)
    cam.data.ortho_scale=size*(2.5+1.8*opening)
    for obj in keep:
        m=origins[obj.name].copy(); path=obj['source_path']
        if '/CW2_Printed/' in path:
            # Separate source housing pieces while preserving their shape.
            p=sum((m@Vector(c) for c in obj.bound_box),Vector())/8
            direction=Vector((1 if p.x>=center.x else -1, -.25, .15))
            m.translation+=direction*size*.65*opening
        elif '/CW2_hardware/' in path:
            m.translation+=Vector((size*.72,0,size*.3))*opening
        elif path.endswith('/LDO-36STH20'):
            m.translation+=Vector((0,size*.38,0))*opening
        # Rotate source gears about their source local axial direction.
        # This is illustrative rotation, not a calibrated meshing simulation.
        elif path.endswith(('/Drive_Gear','/Idler_Gear','/50T_Drive_Gear')):
            local_axis=0 if path.endswith('/50T_Drive_Gear') else 1
            axis=m.to_3x3().col[local_axis].normalized()
            local_center=sum((Vector(c) for c in obj.bound_box),Vector())/8
            pivot=m@local_center
            angle=max(0,t-3.4)*1.0*(1 if path.endswith('/Idler_Gear') else -1)
            m=Matrix.Translation(pivot)@Matrix.Rotation(angle,4,axis)@Matrix.Translation(-pivot)@m
        obj.matrix_world=m

frames=folder/('preview' if mode=='preview' else 'frames'); frames.mkdir(exist_ok=True)
selected=[1,70,150,230,300] if mode=='preview' else range(1,301)
audit=[]
for f in selected:
    scene.frame_set(f); pose(f); bpy.context.view_layer.update()
    target=frames/f'{f:06}.jpg'
    if target.exists() and target.read_bytes().endswith(b'\xff\xd9'): continue
    scene.render.filepath=str(target); bpy.ops.render.render(write_still=True)
    if f in (1,70,150,230,300): audit.append(dict(frame=f,parts=[dict(id=o['part_id'],matrix=[list(r) for r in o.matrix_world]) for o in keep]))
pose(150); bpy.ops.wm.save_as_mainfile(filepath=str(folder/('preview.blend' if mode=='preview' else 'scene.blend')))
(folder/f'{mode}-audit.json').write_text(json.dumps(dict(source_model_sha256=job['model_sha256'],part_count=len(keep),poses=audit,limitations='Source CAD only; display materials, separation and gear rotation illustrative; not meshing simulation'),indent=2))
