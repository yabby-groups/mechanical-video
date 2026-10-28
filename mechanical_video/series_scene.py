"""Blender-only archived renderer for official, independently exported CAD parts."""
import hashlib
import json
import math
from pathlib import Path
import sys
import os
import time
from array import array

import bpy
from mathutils import Matrix, Vector

job_path=Path(sys.argv[sys.argv.index('--')+1]); mode=sys.argv[sys.argv.index('--')+2]
job=json.loads(job_path.read_text()); folder=Path(job['folder'])
manifest=Path(job['manifest']); model=json.loads(manifest.read_text())
assert hashlib.sha256(manifest.read_bytes()).hexdigest()==job['model_sha256']
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
try: scene.render.engine='BLENDER_EEVEE_NEXT'
except TypeError: scene.render.engine='BLENDER_EEVEE'
if hasattr(scene,'eevee') and hasattr(scene.eevee,'taa_render_samples'):
    scene.eevee.taa_render_samples=8
scene.render.resolution_x=1080; scene.render.resolution_y=1920
scene.render.resolution_percentage=25 if mode=='preview' else 100
scene.render.fps=30
scene.render.image_settings.file_format='JPEG'; scene.render.image_settings.quality=93
scene.render.film_transparent=False
scene['source_model_sha256']=job['model_sha256']
scene.world=bpy.data.worlds.new('Industrial studio'); scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.04,.055,.075,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
scene.view_settings.view_transform='AgX'
palette={'frame':(.2,.24,.29,1),'panels':(.11,.16,.2,1),'toolhead':(.9,.15,.035,1),
    'gantry':(.18,.4,.45,1),'z_drive':(.75,.16,.04,1),'bed':(.3,.34,.38,1),
    'motors':(.09,.1,.12,1),'motion':(.18,.2,.22,1),'other':(.23,.25,.28,1)}
materials={}
for group,color in palette.items():
    mat=bpy.data.materials.new(group); mat.diffuse_color=color; mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF'); shader.inputs['Base Color'].default_value=color
    shader.inputs['Metallic'].default_value=.45 if group in ('frame','bed','motion') else .1
    shader.inputs['Roughness'].default_value=.48
    materials[group]=mat

meshes={}; objects=[]
for part in model['parts']:
    source=manifest.parent/part['mesh']
    if part['mesh'] not in meshes:
        bpy.ops.wm.stl_import(filepath=str(source))
        obj=bpy.context.object; meshes[part['mesh']]=obj.data
    else:
        obj=bpy.data.objects.new(part['id'],meshes[part['mesh']]); scene.collection.objects.link(obj)
    obj.name=part['id']+'_'+part['name']
    transform=Matrix(part['matrix_mm']); transform.translation*=.001
    # STL coordinates are in millimetres. Scale local vertices exactly once.
    if not obj.data.get('metres'):
        obj.data.transform(Matrix.Scale(.001,4))
        obj.data.update()
        obj.data['metres']=True
    obj.matrix_world=transform
    obj.data.materials.clear(); obj.data.materials.append(materials[part['group']])
    obj['part_id']=part['id']; obj['source_path']=part['path']; obj['group']=part['group']
    objects.append(obj)

bpy.context.view_layer.update()
points=[o.matrix_world@Vector(v) for o in objects for v in o.bound_box]
lower=Vector(tuple(min(p[i] for p in points) for i in range(3)))
upper=Vector(tuple(max(p[i] for p in points) for i in range(3)))
center=(lower+upper)*.5; size=max(upper-lower)
if size<=0: raise ValueError('Empty assembly bounds')

# A CAD assembly may use Y-up. Preserve source coordinates in manifest, apply a
# single documented presentation parent rotation rather than rewriting parts.
root=bpy.data.objects.new('CAD world presentation',None); scene.collection.objects.link(root)
for obj in objects: obj.parent=root

def aim(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(); camera=bpy.context.object; scene.camera=camera
camera.data.type='ORTHO'; camera.data.ortho_scale=size*2.65
camera.location=center+Vector((size*1.6,-size*2.8,size*1.1)); aim(camera,center)
for pos,power,scale in [((1,-2,3),1200,3),((-2,-1,1),900,2),((0,2,2),1500,2)]:
    bpy.ops.object.light_add(type='AREA',location=center+Vector(pos)*size)
    light=bpy.context.object; light.data.energy=power*size*size*.22; light.data.shape='DISK'; light.data.size=size*scale; aim(light,center)

seconds=job['timeline']['seconds']; end=round(seconds*30); scene.frame_end=end

# The narrative has six blocks. Each has a separate physical assembly action;
# this is not a repeated turntable or a transformed still image.
groups={g:[o for o in objects if o['group']==g] for g in palette}
moving=[]
def key(obj,frame,location):
    obj.location=location; obj.keyframe_insert(data_path='location',frame=frame)
def at(index):
    return max(1,min(end,round(job['timeline']['chapters'][min(index,len(job['timeline']['chapters'])-1)]['start']*30)+1))
for obj in objects:
    origin=obj.location.copy(); g=obj['group']; delta=Vector((0,0,0))
    centroid=sum((obj.matrix_world@Vector(c) for c in obj.bound_box),Vector())/8
    radial=centroid-center
    if g=='panels':
        delta=Vector((radial.x,radial.y,radial.z*.3))
        if delta.length<size*.1: delta=Vector((size*.4,0,0))
        delta=delta.normalized()*size*.42
    elif g in ('gantry','toolhead') and job['episode']==1: delta=Vector((0,0,size*.2))
    elif g=='z_drive' and job['episode']==1: delta=Vector((radial.x,radial.y,0)).normalized()*size*.2 if radial.length else Vector((size*.2,0,0))
    elif g=='bed' and job['episode']==1: delta=Vector((0,-size*.18,0))
    elif g=='frame' and job['episode']==2:
        delta=radial.normalized()*size*.07 if radial.length else Vector()
    elif job['episode']>=4:
        n=job['episode']; source_path=obj['source_path'].lower()
        selected=(n==4 and g=='motors') or (n==5 and g in ('motion','z_drive')) or (n==6 and '/cw2_assembly/' in source_path) or (n==7 and '/p6_assembly' in source_path) or (n==8 and g=='bed') or (n==9 and '/electronics/' in source_path) or (n==10 and any(t in source_path for t in ('fan','blower'))) or n==12
        if selected:
            delta=(radial.normalized() if radial.length else Vector((1,0,0)))*size*(.12 if g=='frame' else .22)
    if delta.length:
        if job['episode']==1:
            first,last={'panels':(7,12),'bed':(13,17),'gantry':(17,23),'toolhead':(28,33),'z_drive':(19,23)}.get(g,(7,12))
        elif job['episode']==2: first,last=(4,8) if g=='panels' else (9,18)
        elif job['episode']==3: first,last=3,8
        else: first,last=(1,4) if job['episode']==12 else (5,14)
        key(obj,1,origin); key(obj,at(first),origin)
        key(obj,at(last),origin+delta)
        if job['episode']==12:
            restore={'frame':9,'motion':16,'motors':16,'z_drive':19,'gantry':19,'bed':22,'toolhead':26,'other':29,'panels':34}[g]
            key(obj,at(restore),origin+delta); key(obj,at(restore+3),origin)
        else: key(obj,at(len(job['timeline']['chapters'])-5),origin+delta)
        key(obj,end,origin)
        moving.append(obj)

# EP03 adds coordinated toolhead translation. Existing CAD parts move together;
# the belt geometry stays source-authentic and is not falsely stretched into a simulation.
axis_tips=[]
if job['episode'] in (3,11):
    for obj in objects:
        source_path=obj['source_path']
        if '/Gantry/' not in source_path: continue
        origin=obj.location.copy()
        on_xbeam='/X_Axis/' in source_path
        on_carriage='/X_Carriage/' in source_path
        path=[(0,0,0),(10,0,0),(14,.12,0),(18,.12,.1),(22,0,.1),(26,0,0),(28,0,0),(34,0,0),(40,0,0),(46,0,0)]
        for index,x,y in path:
            z=.16 if 34<=index<=40 else 0
            offset=Vector((x if on_carriage else 0,y if on_xbeam else 0,z))*size
            key(obj,at(index),origin+offset)
        key(obj,end,origin)
        if obj not in moving: moving.append(obj)

    # Explicit teaching arrows distinguish the Cartesian directions. They are
    # annotations, never substituted for the moving source CAD components.
    for label,axis in [('X',(1,0,0)),('Y',(0,1,0)),('Z',(0,0,1))]:
        direction=Vector(axis); start=center+Vector((-.18,-.35,-.18))*size
        bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=size*.006,depth=size*.22,
            location=start+direction*size*.11)
        shaft=bpy.context.object; shaft.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
        shaft.data.materials.append(materials['gantry']); shaft.name='Direction '+label+' (schematic)'
        bpy.ops.mesh.primitive_cone_add(vertices=12,radius1=size*.02,radius2=0,depth=size*.05,
            location=start+direction*size*.245)
        tip=bpy.context.object; tip.rotation_euler=shaft.rotation_euler; tip.data.materials.append(materials['toolhead'])
        axis_tips.append((label,tip.location+direction*size*.045))

# Fixed viewpoints cut with narration sections. Mechanical motion comes from
# CAD components; a turntable camera is not used as the motion demonstration.
camera_frames=[]
angles=[(1.6,-2.8,1.1),(2,-2.4,.8),(1.4,-2.8,1.4),(-1.6,-2.8,1.0)]
for i,section in enumerate(job['scenes']):
    f=max(1,round(section['start']*30)+1); offset=angles[i%len(angles)]
    camera_frames.append(f)
    camera.location=center+Vector(offset)*size; aim(camera,center)
    camera.keyframe_insert(data_path='location',frame=f); camera.keyframe_insert(data_path='rotation_euler',frame=f)
action=camera.animation_data.action
curves=list(action.fcurves) if hasattr(action,'fcurves') else [curve for layer in action.layers for strip in layer.strips for bag in strip.channelbags for curve in bag.fcurves]
for curve in curves:
    for point in curve.keyframe_points: point.interpolation='CONSTANT'

# Fit the full moving assembly in portrait, including exploded panel corners.
# The model, not just its initial assembled bounds, determines safe framing.
required=size*2.65; aspect=1080/1920
fit_frames=sorted(set([1,end]+[at(i) for i in range(len(job['timeline']['chapters']))]+[max(1,f-1) for f in camera_frames]))
for frame in fit_frames:
    scene.frame_set(frame); bpy.context.view_layer.update()
    inverse=camera.matrix_world.inverted()
    projected=[inverse@(obj.matrix_world@Vector(corner)) for obj in objects for corner in obj.bound_box]
    half_x=max(abs(v.x) for v in projected); half_y=max(abs(v.y) for v in projected)
    required=max(required,2*half_x/aspect*1.12,2*half_y*1.12)
camera.data.ortho_scale=required

# Camera-relative titles and component legend remain readable in portrait.
fontfile=Path('/System/Library/Fonts/PingFang.ttc')
if not fontfile.exists(): fontfile=Path('/System/Library/Fonts/STHeiti Medium.ttc')
font=bpy.data.fonts.load(str(fontfile)) if fontfile.exists() else None
emission=bpy.data.materials.new('Annotation light'); emission.use_nodes=True
nodes=emission.node_tree.nodes; nodes.clear(); shader=nodes.new('ShaderNodeEmission'); shader.inputs[0].default_value=(.7,.9,1,1)
out=nodes.new('ShaderNodeOutputMaterial'); emission.node_tree.links.new(shader.outputs[0],out.inputs[0])
def text(label,x,y,scale):
    curve=bpy.data.curves.new(label,'FONT'); curve.body=label; curve.size=scale; curve.align_x='CENTER'
    if font: curve.font=font
    obj=bpy.data.objects.new(label,curve); scene.collection.objects.link(obj); obj.parent=camera
    obj.location=(x,y,-size*4); curve.materials.append(emission)
    return obj
text('拆解一台 3D 打印机',0,required*.42,required*.028)
title=job['title']
text(f'EP{job["episode"]:02}  '+title,0,required*.375,required*.020)
text('VORON 2.4r2 · OFFICIAL CAD',0,-required*.455,required*.012)
if any(p.get('display_approximation') for p in model['parts']):
    text('局部为源CAD近似示意',0,required*.335,required*.015)
for section in job['scenes']:
    label=text(section['title'],0,-required*.34,required*.020)
    label.hide_render=True; label.keyframe_insert(data_path='hide_render',frame=1)
    label.hide_render=False; label.keyframe_insert(data_path='hide_render',frame=max(1,round(section['start']*30)+1))
    label.hide_render=True; label.keyframe_insert(data_path='hide_render',frame=round(section['end']*30)+1)
for label,position in axis_tips:
    curve=bpy.data.curves.new('Axis '+label,'FONT'); curve.body=label; curve.size=size*.055
    if font: curve.font=font
    obj=bpy.data.objects.new('Axis label '+label,curve); scene.collection.objects.link(obj)
    obj.location=position; curve.materials.append(emission)
    constraint=obj.constraints.new(type='COPY_ROTATION'); constraint.target=camera
if job['episode']>=4:
    import importlib.util
    spec=importlib.util.spec_from_file_location('archived_series_diagrams',Path(__file__).with_name('series_diagrams.py'))
    diagrams=importlib.util.module_from_spec(spec); spec.loader.exec_module(diagrams)
    diagrams.add_diagrams(job,center,size,required,camera,materials,text)

audit=[]; audit_objects=[]
for group in palette:
    audit_objects.extend([o for o in moving if o['group']==group][:3])
audit_objects.extend([o for o in moving if '/X_Carriage/' in o['source_path']][:3])
audit_objects=list(dict.fromkeys(audit_objects))
audit_frames=sorted(set([1,end]+[at(i) for i in [4,7,10,14,17,19,23,26,28,33,34,40,43,46]]))
for obj in audit_objects:
    samples=[]
    for frame in audit_frames:
        scene.frame_set(frame); samples.append({'frame':frame,'position_m':list(obj.location)})
    audit.append({'part_id':obj['part_id'],'group':obj['group'],'samples':samples})
motion=dict(source_model_sha256=job['model_sha256'],moving_parts=len(moving),
    samples=audit,parts=len(objects),bounds_m=[list(lower),list(upper)],
    camera_fit_frames=fit_frames,scene_sections=job['scenes'],
    classification='Illustrative explosion and toolhead trajectory, not belt deformation or dynamic simulation')
if not moving: raise ValueError('No mechanical component keyframes; refusing still-image production')
(folder/'motion_audit.json').write_text(json.dumps(motion,ensure_ascii=False,indent=2))
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(folder/('preview.blend' if mode=='preview' else 'scene.blend')))
frames=folder/('preview' if mode=='preview' else 'frames'); frames.mkdir(exist_ok=True)
selected=[1,round(end*.27),round(end*.5),round(end*.75),end] if mode=='preview' else range(1,end+1)
pose_cache={}; rendered=0; reused=0; existing=0; started=time.monotonic()
scene_objects=list(scene.objects)
for frame in selected:
    target=frames/f'{frame:06}.jpg'
    scene.frame_set(frame)
    pose=array('f',(value for obj in scene_objects for row in obj.matrix_world for value in row)).tobytes()
    pose+=bytes(int(obj.hide_render) for obj in scene_objects)
    key=hashlib.blake2b(pose,digest_size=20).hexdigest()
    if target.exists():
        # Only complete JPEGs are resumable.
        data=target.read_bytes()
        if len(data)>1000 and data.endswith(b'\xff\xd9'):
            pose_cache[key]=target; existing+=1
            continue
    if job['episode']<=3 and key in pose_cache:
        target.unlink(missing_ok=True)
        os.link(pose_cache[key],target); reused+=1
        continue
    scene.render.filepath=str(target)
    bpy.ops.render.render(write_still=True)
    pose_cache[key]=target; rendered+=1
(folder/f'{mode}-metrics.json').write_text(json.dumps(dict(rendered_this_run=rendered,
    reused_identical_scene_pose=reused,existing_frames=existing,wall_seconds=time.monotonic()-started,
    frame_count=len(selected),resolution=[scene.render.resolution_x*scene.render.resolution_percentage//100,scene.render.resolution_y*scene.render.resolution_percentage//100],
    engine=scene.render.engine,samples=8),indent=2))
print('SERIES_RENDER_COMPLETE',mode,flush=True)
