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
    if '/CW2_Assembly/' in obj.get('source_path','') or '/P6_Assembly' in obj.get('source_path',''):
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
scene.render.fps=30; scene.frame_end=round(job["timeline"]["seconds"]*30)
scene.render.image_settings.file_format='JPEG'; scene.render.image_settings.quality=95
scene.render.film_transparent=False
try: scene.render.engine='BLENDER_EEVEE_NEXT'
except TypeError: scene.render.engine='BLENDER_EEVEE'
scene.render.image_settings.color_mode='RGB'
def smooth(x):
    x=max(0,min(1,x)); return x*x*(3-2*x)

# Feed line is a labelled explanatory overlay, not a new CAD component.
drive=next(o for o in keep if o['source_path'].endswith('/Drive_Gear'))
idler=next(o for o in keep if o['source_path'].endswith('/Idler_Gear'))
def centroid(o): return sum((o.matrix_world@Vector(c) for c in o.bound_box),Vector())/8
feed=(centroid(drive)+centroid(idler))/2
feed_mat=material('illustrative filament cyan',(.025,.65,.9),.15)
bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.000875,depth=.13,location=feed)
filament=bpy.context.object; filament.name='SCHEMATIC filament 1.75mm (assumed)'
filament.data.materials.append(feed_mat)
marks=[]
for i in range(16):
    bpy.ops.mesh.primitive_torus_add(major_radius=.00089,minor_radius=.00012,major_segments=16,minor_segments=6,location=feed)
    mark=bpy.context.object; mark.data.materials.append(gear); marks.append(mark)
story=job['timeline']['chapters']; seconds=job['timeline']['seconds']
def pose(frame):
    t=(frame-1)/30
    opening=smooth((t-1)/2.2)*(1-smooth((t-seconds+3)/2.5))
    close=smooth((t-story[1]['start']+.3)/1.3)*(1-smooth((t-story[-1]['end'])/1.2))
    yaw=-.1+.24*smooth(t/seconds)
    focus=center.lerp(feed,close)
    cam.location=focus+Vector((math.sin(yaw)*2.5,-2.8,.8))*size
    aim(cam,focus)
    cam.data.ortho_scale=size*((2.5+1.8*opening)*(1-close)+1.25*close)
    slip=smooth((t-story[4]['start'])/.7)*(1-smooth((t-story[5]['start'])/.6))
    for obj in keep:
        m=origins[obj.name].copy(); path=obj['source_path']
        is_shell='/CW2_Printed/' in path or '/CW2_hardware/' in path
        if '/CW2_Printed/' in path:
            p=sum((m@Vector(c) for c in obj.bound_box),Vector())/8
            direction=Vector((1 if p.x>=center.x else -1,-.25,.15))
            m.translation+=direction*size*.65*opening
        elif '/CW2_hardware/' in path: m.translation+=Vector((size*.72,0,size*.3))*opening
        elif path.endswith('/LDO-36STH20'): m.translation+=Vector((0,size*.38,0))*opening
        elif path.endswith(('/Drive_Gear','/Idler_Gear','/50T_Drive_Gear')):
            axis=m.to_3x3().col[0 if path.endswith('/50T_Drive_Gear') else 1].normalized()
            pivot=origins[obj.name]@(sum((Vector(c) for c in obj.bound_box),Vector())/8)
            # Both source local axes point -Y; idler counter-rotates.
            angle=max(0,t-3.5)*.9*(1 if path.endswith('/Idler_Gear') else -1)
            m=Matrix.Translation(pivot)@Matrix.Rotation(angle,4,axis)@Matrix.Translation(-pivot)@m
            if path.endswith('/Idler_Gear'): m.translation.x-=.004*slip
        obj.matrix_world=m
        # A hard editorial cut removes the opened housing for the gear macro shot.
        obj.hide_render=bool(close>.9 and (is_shell or path.endswith('/LDO-36STH20') or 'Spring_Assembly' in path))
    # Moving bands show feed direction. During the loose-idler demonstration
    # the bands stop while the gear continues, then resume after re-clamping.
    stop=story[4]['start']; resume=story[5]['start']
    feed_time=t-min(max(t-stop,0),resume-stop)
    for i,mark in enumerate(marks):
        mark.location=feed+Vector((0,0,((i*.008-feed_time*.006+.065)%.13)-.065))
    filament.hide_render=t<story[1]['start']-.5 or t>seconds-2
    for mark in marks: mark.hide_render=filament.hide_render

frames=folder/('preview' if mode=='preview' else 'frames'); frames.mkdir(exist_ok=True)
selected=job["audit_frames"] if mode=='preview' else range(1,scene.frame_end+1)
audit=[]
for f in selected:
    scene.frame_set(f); pose(f); bpy.context.view_layer.update()
    target=frames/f'{f:06}.jpg'
    if target.exists() and target.read_bytes().endswith(b'\xff\xd9'): continue
    scene.render.filepath=str(target); bpy.ops.render.render(write_still=True)
    if f in job["audit_frames"]: audit.append(dict(frame=f,parts=[dict(id=o['part_id'],matrix=[list(r) for r in o.matrix_world]) for o in keep]))
pose(job["audit_frames"][2]); bpy.ops.wm.save_as_mainfile(filepath=str(folder/('preview.blend' if mode=='preview' else 'scene.blend')))
(folder/f'{mode}-audit.json').write_text(json.dumps(dict(source_model_sha256=job['model_sha256'],part_count=len(keep),poses=audit,limitations='Source CAD only; display materials, separation and gear rotation illustrative; not meshing simulation'),indent=2))
