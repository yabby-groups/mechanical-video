"""Executed by Blender, independently of the CAD Python environment."""
import bpy
import sys
import json
import math
from pathlib import Path
from mathutils import Vector
job=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text())
manifest=Path(job['manifest']); data=json.loads(manifest.read_text())
out=Path(job['directory']); out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
s=bpy.context.scene
# Blender 4+ Eevee enum can be dynamic; explicit engine is supported by installed Blender.
if job.get('engine')=='cycles': s.render.engine='CYCLES'
else:
    try: s.render.engine='BLENDER_EEVEE_NEXT'
    except TypeError: s.render.engine='BLENDER_EEVEE'
if s.render.engine=='CYCLES':
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='METAL'; prefs.get_devices()
    for d in prefs.devices: d.use=d.type=='METAL'
    if not any(d.use and d.type=='METAL' for d in prefs.devices):
        raise RuntimeError('No Metal device available; refusing CPU fallback')
    s.cycles.device='GPU'; s.cycles.samples=16
    (out/'hardware.json').write_text(json.dumps({'engine':'CYCLES','backend':'METAL','device':'GPU','selected_devices':[{'name':d.name,'type':d.type} for d in prefs.devices if d.use],'samples':s.cycles.samples},indent=2))
if hasattr(s,'eevee') and hasattr(s.eevee,'taa_render_samples'): s.eevee.taa_render_samples=32 if max(job['width'],job['height'])>=1920 else 8
s.render.resolution_x=job['width']; s.render.resolution_y=job['height']; s.render.resolution_percentage=100
s.render.fps=30; s.frame_end=int(job['seconds']*30)
s.render.image_settings.file_format='PNG'; s.render.filepath=str(out/'frames'/'')+'/'
s.render.film_transparent=False
s.world.color=(0.12,0.12,0.12)
s.view_settings.view_transform='AgX'
objects=[]; template=job['template']; end=s.frame_end
for part in data['parts']:
    bpy.ops.wm.stl_import(filepath=str(manifest.parent/part['stl']))
    ob=bpy.context.object; ob.name=part['name']; ob.location=Vector(part['position'])/100
    ob['inferred']=part['inferred']; ob['part_group']=part['group']
    mat=bpy.data.materials.new(part['name']); mat.diffuse_color=part['color']; mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=part['color']; bs.inputs['Metallic'].default_value=.7; bs.inputs['Roughness'].default_value=.27
    # STL dimensions are mm: normalize mesh into scene meters-like units.
    for v in ob.data.vertices: v.co/=100
    ob.data.materials.append(mat)
    bevel=ob.modifiers.new('Machined edges','BEVEL'); bevel.width=.003; bevel.segments=2
    base=ob.location.copy(); delta=Vector(part['explode'])/100
    enabled=template in ('explode','assembly','explanation','internals','shell')
    if template=='shell': enabled=part['group'] in ('shell','fastener')
    if template=='internals': enabled=part['group']!='shell'; ob.hide_render=part['group']=='shell'
    if template in ('gears','working'): ob.hide_render=part['group'] in ('shell','fastener') or (template=='gears' and part['group']!='gear')
    if template=='closeup': ob.hide_render=part['name']!='sun_gear'
    if template=='transparent' and part['group']=='shell':
        bs.inputs['Transmission Weight'].default_value=.9; bs.inputs['Alpha'].default_value=.15
        mat.surface_render_method='DITHERED'
    if enabled:
        poses=[(1,1 if template=='assembly' else 0),(int(end*.8),0 if template=='assembly' else 1),(end,0 if template=='assembly' else 1)]
        if template=='explode':
            start,finish=1,int(end*.28)
            if part['group'] not in ('shell','fastener'):
                order={'sun_gear':0,'planet_1':1,'planet_2':2,'planet_3':3}.get(part['name'],4)
                start=int(end*(.28+order*.085)); finish=min(int(end*.86),start+int(end*.20))
            poses=[(1,0),(max(2,start),0),(finish,1),(end,1)]
        for frame,amount in poses:
            ob.location=base+delta*amount; ob.keyframe_insert(data_path='location',frame=frame)
    if template in ('gears','working') and part['group']=='gear':
        # Fixed ring: carrier=sun/(1+Nr/Ns), planet spin from external mesh.
        ns,np,nr=18,15,48; turns=2*math.pi*2
        for frame in range(1,end+1):
            t=turns*(frame-1)/max(1,end-1)
            carrier=t/(1+nr/ns)
            if part['name']=='sun_gear': ob.rotation_euler.z=t
            else:
                i=int(part['name'][-1])-1; a=i*2*math.pi/3+carrier
                r=math.hypot(base.x,base.y); ob.location=(r*math.cos(a),r*math.sin(a),base.z)
                ob.rotation_euler.z=carrier-(t-carrier)*ns/np
                ob.keyframe_insert(data_path='location',frame=frame)
            ob.keyframe_insert(data_path='rotation_euler',frame=frame)
    if template=='working' and part['group'] in ('shaft','carrier','pin'):
        for frame in range(1,end+1):
            t=4*math.pi*(frame-1)/max(1,end-1)
            angle=t if part['name']=='input_shaft' else t/(1+48/18)
            ob.rotation_euler.z=angle; ob.keyframe_insert(data_path='rotation_euler',frame=frame)
            if part['group']=='pin':
                a=math.atan2(base.y,base.x)+angle; r=math.hypot(base.x,base.y)
                ob.location=(r*math.cos(a),r*math.sin(a),base.z); ob.keyframe_insert(data_path='location',frame=frame)
    objects.append(ob)
# Ground below all exploded components.
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-1.2)); ground=bpy.context.object
mat=bpy.data.materials.new('Midnight stage'); mat.diffuse_color=(.018,.025,.04,1); mat.use_nodes=True; mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.018,.025,.04,1); ground.data.materials.append(mat)
for loc,power,size in [((3,-4,6),1700,5),((-4,-1,3),1200,4),((1,4,5),2200,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc); light=bpy.context.object; light.data.energy=power; light.data.shape='DISK'; light.data.size=size
    light.rotation_euler=(Vector((0,0,.3))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(); cam=bpy.context.object; s.camera=cam; cam.data.type='ORTHO'
cam.data.ortho_scale=(6.5 if template in ('explode','assembly','shell','internals','explanation') else 4.0) if job['width']>=job['height'] else 3.6
if template=='closeup': cam.data.ortho_scale=1
for f in range(1,end+1):
    angle=-.9+(2*math.pi if template=='overview' else .45)*(f-1)/max(1,end-1)
    cam.location=(4*math.cos(angle),4*math.sin(angle),3.1)
    target=Vector((0,0,.4 if template in ('explode','assembly','shell','internals','explanation') else 0))
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.keyframe_insert(data_path='location',frame=f); cam.keyframe_insert(data_path='rotation_euler',frame=f)
# Fit all visible mechanical bounding boxes at representative animation poses.
# This excludes the floor and annotations and prevents exploded parts being cropped.
required=cam.data.ortho_scale
aspect=job['width']/job['height']
for f in [1,max(1,int(end*.4)),max(1,int(end*.8)),end]:
    s.frame_set(f); bpy.context.view_layer.update()
    inverse=cam.matrix_world.inverted()
    for ob in objects:
        if ob.hide_render: continue
        for corner in ob.bound_box:
            q=inverse @ ob.matrix_world @ Vector(corner)
            required=max(required,abs(q.x)*2.25/min(1,aspect),abs(q.y)*max(1,aspect)*2.25)
cam.data.ortho_scale=required
(out/'camera.json').write_text(json.dumps({'projection':'orthographic','scale':required,'aspect':aspect,'fit_frames':[1,int(end*.4),int(end*.8),end],'engine':s.render.engine,'fps':30,'frame_end':end},indent=2))
# Camera-facing title, embedded in the scene and all rendered frames.
bpy.ops.object.text_add(); title=bpy.context.object; title.name='Video title'; title.parent=cam
aspect=job['width']/job['height']; title.location=(-cam.data.ortho_scale*min(1,aspect)*.45,cam.data.ortho_scale/max(1,aspect)*.41,-2)
title.data.body=template.upper()+' / PLANETARY 3.67:1\nINFERRED EDUCATIONAL STRUCTURE'; title.data.size=cam.data.ortho_scale*min(1,aspect)*.016; title.data.extrude=0
m=bpy.data.materials.new('Title'); m.use_nodes=True; bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(.8,.92,1,1); bs.inputs['Emission Color'].default_value=(.8,.92,1,1); bs.inputs['Emission Strength'].default_value=1; title.data.materials.append(m)
if template=='explanation':
    # Bake text visibility switches into the saved scene for reproducible playback.
    for index,text in enumerate(['01 / HOUSING AND FASTENERS','02 / SUN, PLANETS AND CARRIER','03 / EXPLODED ASSEMBLY - 3.67:1']):
        phase=title.copy(); phase.data=title.data.copy(); bpy.context.collection.objects.link(phase)
        phase.data.body=text+'\nINFERRED EDUCATIONAL STRUCTURE'
        for frame in [1,int(end/3)+1,int(2*end/3)+1,end]:
            phase.hide_render=(min(2,int((frame-1)*3/end))!=index); phase.keyframe_insert(data_path='hide_render',frame=frame)
    title.hide_render=True
s.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
frames=out/'frames'; frames.mkdir(exist_ok=True)
# Resume complete PNG frames rather than restarting animation.
for frame in range(1,end+1):
    target=frames/f'{frame:04d}.png'
    if target.exists() and target.stat().st_size>100: continue
    s.frame_set(frame); s.render.filepath=str(target); bpy.ops.render.render(write_still=True)
