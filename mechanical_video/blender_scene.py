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
is_drill=data.get('product')=='cordless_drill'
story=job.get('storyboard')
for part in data['parts']:
    bpy.ops.wm.stl_import(filepath=str(manifest.parent/part['stl']))
    ob=bpy.context.object; ob.name=part['name']; ob.location=Vector(part['position'])/100
    ob['inferred']=part['inferred']; ob['part_group']=part['group']
    mat=bpy.data.materials.new(part['name']); mat.diffuse_color=part['color']; mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=part['color']; bs.inputs['Metallic'].default_value=.7 if part.get('material','metal')=='metal' else 0; bs.inputs['Roughness'].default_value=.38 if part.get('material') in ('rubber','plastic') else .27
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
    if enabled and not story:
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
# Long-form shots use measured narration offsets and explicit independent part tracks.
if story:
    def film_frame(seconds): return max(1,min(end,round(seconds*30)+1))
    for ob,part in zip(objects,data['parts']):
        base=Vector(part['position'])/100
        for seconds,offset in story['tracks_mm'][ob.name]:
            ob.location=base+Vector(offset)/100
            ob.keyframe_insert(data_path='location',frame=film_frame(seconds))
        for i,chapter in enumerate(story['chapters']):
            first=film_frame(chapter['start'])
            last=film_frame(chapter['end'])-1 if i<len(story['chapters'])-1 else end
            ob.hide_render=ob.name not in chapter['visible_parts']
            ob.keyframe_insert(data_path='hide_render',frame=first)
            ob.keyframe_insert(data_path='hide_render',frame=last)
    s.frame_set(1); bpy.context.view_layer.update()
# Ground below all exploded components.
floor_z=min((min((ob.matrix_world@Vector(c)).z for c in ob.bound_box)+min(0,p['explode'][2]/100) for ob,p in zip(objects,data['parts'])),default=-1.1)-.15 if is_drill else -1.2
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,floor_z)); ground=bpy.context.object
mat=bpy.data.materials.new('Midnight stage'); mat.diffuse_color=(.018,.025,.04,1); mat.use_nodes=True; mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.018,.025,.04,1); ground.data.materials.append(mat)
for loc,power,size in [((3,-4,6),1700,5),((-4,-1,3),1200,4),((1,4,5),2200,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc); light=bpy.context.object; light.data.energy=power; light.data.shape='DISK'; light.data.size=size
    light.rotation_euler=(Vector((0,0,.3))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(); cam=bpy.context.object; s.camera=cam; cam.data.type='ORTHO'
cam.data.ortho_scale=(6.5 if template in ('explode','assembly','shell','internals','explanation') else 4.0) if job['width']>=job['height'] else 3.6
if template=='closeup': cam.data.ortho_scale=1
if not story:
    for f in range(1,end+1):
        angle=(-1.3 if is_drill else -.9)+(2*math.pi if template=='overview' else .45)*(f-1)/max(1,end-1)
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
else:
    aspect=job['width']/job['height']; shot_scales=[]
    lookup={ob.name:ob for ob in objects}
    for i,chapter in enumerate(story['chapters']):
        first=film_frame(chapter['start'])
        last=film_frame(chapter['end'])-1 if i<len(story['chapters'])-1 else end
        samples=sorted({first,(first+last)//2,last})
        points=[]
        for frame in samples:
            s.frame_set(frame); bpy.context.view_layer.update()
            points.extend(lookup[name].matrix_world@Vector(c) for name in chapter['visible_parts'] for c in lookup[name].bound_box)
        low=Vector(tuple(min(p[k] for p in points) for k in range(3)))
        high=Vector(tuple(max(p[k] for p in points) for k in range(3)))
        center=(low+high)/2
        cam.location=center+Vector((2.6,-5.0,2.5))
        cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        bpy.context.view_layer.update(); inverse=cam.matrix_world.inverted()
        # Reserve space above and below for chapter titles and Chinese subtitles.
        scale=max(1.8,max(max(abs((inverse@p).x)*2.3,abs((inverse@p).y)*aspect*3.1) for p in points))
        shot_scales.append(scale)
        for frame,angle in [(first,-.06),(last,.06)]:
            direction=Vector((2.6*math.cos(angle)-(-5)*math.sin(angle),2.6*math.sin(angle)+(-5)*math.cos(angle),2.5))
            cam.location=center+direction
            cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
            cam.data.ortho_scale=scale
            cam.keyframe_insert(data_path='location',frame=frame)
            cam.keyframe_insert(data_path='rotation_euler',frame=frame)
            cam.data.keyframe_insert(data_path='ortho_scale',frame=frame)
    # Explicit hard cuts between chapters, a gentle drift within each shot.
    for action_owner in [cam,cam.data]:
        action=action_owner.animation_data.action
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:
                            frame=round(key.co.x)
                            key.interpolation='CONSTANT' if any(frame==film_frame(c['end'])-1 for c in story['chapters'][:-1]) else 'LINEAR'
    (out/'camera.json').write_text(json.dumps({'projection':'orthographic','shot_scales':shot_scales,'chapters':len(story['chapters']),'engine':s.render.engine,'fps':30,'frame_end':end},indent=2))
    s.frame_set(1); bpy.context.view_layer.update()
# Camera-facing title, embedded in the scene and all rendered frames.
bpy.ops.object.text_add(); title=bpy.context.object; title.name='Video title'; title.parent=cam
aspect=job['width']/job['height']; title.location=(-cam.data.ortho_scale*min(1,aspect)*.45,cam.data.ortho_scale/max(1,aspect)*.41,-2)
title.data.body=template.upper()+' / '+data.get('title','PLANETARY 3.67:1')+'\nINFERRED EDUCATIONAL STRUCTURE'; title.data.size=cam.data.ortho_scale*min(1,aspect)*.016; title.data.extrude=0
m=bpy.data.materials.new('Title'); m.use_nodes=True; bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(.8,.92,1,1); bs.inputs['Emission Color'].default_value=(.8,.92,1,1); bs.inputs['Emission Strength'].default_value=1; title.data.materials.append(m)
if story:
    for index,chapter in enumerate(story['chapters']):
        phase=title.copy(); phase.data=title.data.copy(); bpy.context.collection.objects.link(phase)
        scale=shot_scales[index]
        phase.location=(-scale*.45,scale/aspect*.41,-2)
        phase.data.body=chapter['title']+'\nPHOTO-GUIDED / INFERRED INTERNALS'
        phase.data.size=scale*.018
        for i,c in enumerate(story['chapters']):
            first=film_frame(c['start']); last=film_frame(c['end'])-1 if i<len(story['chapters'])-1 else end
            phase.hide_render=i!=index
            phase.keyframe_insert(data_path='hide_render',frame=first)
            phase.keyframe_insert(data_path='hide_render',frame=last)
    title.hide_render=True
elif template=='explanation':
    # Bake text visibility switches into the saved scene for reproducible playback.
    for index,text in enumerate((['01 / PHOTO-GUIDED EXTERIOR','02 / HYPOTHETICAL MOTOR, GEARS AND BATTERY','03 / INDEPENDENT PARTS - INFERRED INTERNALS'] if is_drill else ['01 / HOUSING AND FASTENERS','02 / SUN, PLANETS AND CARRIER','03 / EXPLODED ASSEMBLY - 3.67:1'])):
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
