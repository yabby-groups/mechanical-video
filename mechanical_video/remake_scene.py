"""Archived Blender director: source CAD, close-ups and illustrative actions."""
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

args=sys.argv[sys.argv.index('--')+1:]; folder=Path(args[0]).parent; mode=args[1]
job=json.loads(Path(args[0]).read_text())
spec=importlib.util.spec_from_file_location('remake_editorial',Path(__file__).with_name('remake_content.py'))
content=importlib.util.module_from_spec(spec); spec.loader.exec_module(content)
manifest=Path(job['manifest'])
assert hashlib.sha256(manifest.read_bytes()).hexdigest()==job['model_sha256']
model=json.loads(manifest.read_text()); lookup={p['id']:p for p in model['parts']}
assert hashlib.sha256(Path(job['source_scene']).read_bytes()).hexdigest()==job['source_scene_sha256']
bpy.ops.wm.open_mainfile(filepath=job['source_scene'])
scene=bpy.context.scene; scene.animation_data_clear()
objects=[]; original={}
for o in list(scene.objects):
    if o.get('part_id') in lookup:
        part=lookup[o['part_id']]; o.animation_data_clear(); o.parent=None
        m=Matrix(part['matrix_mm']); m.translation*=.001; o.matrix_world=m
        o.hide_render=False; original[o.name]=m.copy(); objects.append(o)
    else: bpy.data.objects.remove(o,do_unlink=True)
bpy.context.view_layer.update()

def material(name,rgb,metal=.3):
    m=bpy.data.materials.new(name); m.diffuse_color=(*rgb,1); m.use_nodes=True
    s=m.node_tree.nodes.get('Principled BSDF'); s.inputs['Base Color'].default_value=(*rgb,1)
    s.inputs['Metallic'].default_value=metal; s.inputs['Roughness'].default_value=.32
    return m
palette={g:material('v2 '+g,c) for g,c in {
    'frame':(.16,.21,.26),'z_drive':(.12,.17,.21),'gantry':(.15,.23,.27),
    'motors':(.07,.085,.10),'motion':(.42,.5,.55),'toolhead':(.065,.09,.12),
    'other':(.18,.23,.28),'panels':(.055,.08,.10),'bed':(.35,.42,.47)}.items()}
orange=material('drive / display highlight',(.9,.26,.045),.65)
cyan=material('schematic filament',(.025,.65,.85),.1)
for o in objects:
    o.data=o.data.copy(); o.data.materials.clear()
    o.data.materials.append(orange if 'Gear' in o['source_path'] else palette[o['group']])

def corners(o): return [o.matrix_world@Vector(c) for c in o.bound_box]
def bounds(items):
    points=[v for o in items for v in corners(o)]
    lo=Vector(tuple(min(v[i] for v in points) for i in range(3)))
    hi=Vector(tuple(max(v[i] for v in points) for i in range(3)))
    return (lo+hi)/2,max(hi-lo),lo,hi
def centroid(o): return sum(corners(o),Vector())/8

drive=next(o for o in objects if o['source_path'].endswith('/Drive_Gear'))
idler=next(o for o in objects if o['source_path'].endswith('/Idler_Gear'))
feed=(centroid(drive)+centroid(idler))/2
extras=[]
bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.000875,depth=.1,location=feed)
filament=bpy.context.object; filament.name='SCHEMATIC filament (assumed 1.75mm)'
filament.data.materials.append(cyan); extras.append(filament)
marks=[]
for i in range(13):
    bpy.ops.mesh.primitive_torus_add(major_radius=.00089,minor_radius=.00012,major_segments=12,minor_segments=5)
    o=bpy.context.object; o.name=f'SCHEMATIC feed band {i}'; o.data.materials.append(orange)
    marks.append(o); extras.append(o)

bed=[o for o in objects if '/Bed_Components/' in o['source_path']]
bed_center,bed_size,bed_low,bed_high=bounds(bed)
curve=bpy.data.curves.new('SCHEMATIC deposited path, not G-code','CURVE')
curve.dimensions='3D'; curve.bevel_depth=.0008; curve.bevel_resolution=1
poly=curve.splines.new('POLY'); poly.points.add(127)
trace=bpy.data.objects.new('SCHEMATIC layered path',curve); scene.collection.objects.link(trace)
curve.materials.append(orange); extras.append(trace)

bpy.ops.object.camera_add(); camera=bpy.context.object; scene.camera=camera; camera.data.type='ORTHO'
camera.data.clip_start=.001
def aim(o,target): o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
lights=[]
for offset,power in [((1,-2,3),95),((-2,-1,.4),65),((0,2,1.5),110)]:
    bpy.ops.object.light_add(type='AREA'); o=bpy.context.object; o.data.shape='DISK'
    lights.append((o,Vector(offset),power))
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.012,.022,.035,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
try: scene.render.engine='BLENDER_EEVEE_NEXT'
except TypeError: scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1080; scene.render.resolution_y=1920
scene.render.resolution_percentage=30 if mode=='preview' else 100
scene.render.fps=30; scene.frame_end=round(job['timeline']['seconds']*30)
scene.render.image_settings.file_format='JPEG'; scene.render.image_settings.quality=94
scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'

shots=job['timeline']['shots']; sets=[]; pivots=[]
for shot in shots:
    keep=[o for o in objects if content.selected(shot['area'],lookup[o['part_id']])]
    if not keep: raise ValueError(f'No source CAD for {shot["area"]}')
    sets.append(keep); pivots.append(bounds(keep)[:2])

def smooth(x):
    x=max(0,min(1,x)); return x*x*(3-2*x)
def pose(index,u,fit=None):
    shot=shots[index]; area=shot['area']; action=shot['action']; keep=sets[index]
    center,size=pivots[index]; elapsed=u*(shot['end']-shot['start'])
    amount=smooth((u-.04)/.78)
    opening=1-amount if action=='assemble' else amount
    for o in objects:
        o.hide_render=True; o.matrix_world=original[o.name]
    for o in extras: o.hide_render=True
    for o in keep:
        o.hide_render=False; p=o['source_path']; m=original[o.name].copy()
        radial=centroid(o)-center
        direction=radial.normalized() if radial.length>1e-5 else Vector((1,0,0))
        if action=='peel':
            if o['group']=='panels': m.translation+=direction*size*.35*amount
            if o['group']=='panels' and u>.85: o.hide_render=True
        elif action in ('split','explode','assemble','pulse','heat'):
            if area in ('cw2','feed','toolhead'):
                if '/CW2_Printed/' in p or '/Stealthburner_Assembly/' in p:
                    m.translation+=Vector((1 if radial.x>=0 else -1,-.2,.1))*size*.48*opening
                elif '/CW2_hardware/' in p: m.translation+=Vector((size*.5,0,size*.2))*opening
            else:
                m.translation+=direction*size*(.22 if area=='whole' else .16)*opening
        elif action=='lift':
            if '/Gantry/' in p: m.translation.z+=.055*amount
        elif action=='travel':
            if '/X_Axis/' in p: m.translation.y+=.035*math.sin(amount*math.pi)
            if '/X_Carriage/' in p: m.translation.x+=.045*(2*amount-1)
        elif action in ('feed','loose','retract'):
            housing='/CW2_Printed/' in p or '/CW2_hardware/' in p
            if housing:
                m.translation+=Vector((1 if radial.x>=0 else -1,0,.1))*size*.7*amount
                if u>.3: o.hide_render=True
            if p.endswith('/LDO-36STH20') or 'Spring_Assembly' in p:
                if u>.3: o.hide_render=True
            if p.endswith(('/Drive_Gear','/Idler_Gear','/50T_Drive_Gear')):
                axis=m.to_3x3().col[0 if p.endswith('/50T_Drive_Gear') else 1].normalized()
                pivot=centroid(o); reverse=-1 if action=='retract' else 1
                angle=elapsed*.65*reverse*(1 if p.endswith('/Idler_Gear') else -1)
                m=Matrix.Translation(pivot)@Matrix.Rotation(angle,4,axis)@Matrix.Translation(-pivot)@m
                if action=='loose' and p.endswith('/Idler_Gear'): m.translation.x-=.004*amount
        o.matrix_world=m
    if action in ('feed','loose','retract'):
        filament.hide_render=False
        for i,o in enumerate(marks):
            o.hide_render=False
            feed_t=min(elapsed,2) if action=='loose' else elapsed
            sign=-1 if action=='retract' else 1
            o.location=feed+Vector((0,0,((i*.008-feed_t*.006*sign+.05)%.1)-.05))
    if action=='layer':
        trace.hide_render=False; side=.07
        path=[(-1,-1),(1,-1),(1,1),(-1,1),(-1,-1)]
        for i,point in enumerate(poly.points):
            q=min(i/127,amount)*8; layer=min(1,int(q//4)); f=q%4; edge=min(3,int(f)); v=f-edge
            x=path[edge][0]*(1-v)+path[edge+1][0]*v
            y=path[edge][1]*(1-v)+path[edge+1][1]*v
            point.co=(bed_center.x+x*side/2,bed_center.y+y*side/2,bed_high.z+.001+layer*.0015,1)
        for o in keep:
            if '/X_Carriage/' in o['source_path']:
                m=original[o.name].copy(); m.translation.x+=x*side/2; m.translation.y+=y*side/2; o.matrix_world=m
    bpy.context.view_layer.update()
    visible=[o for o in keep if not o.hide_render]+[o for o in extras if not o.hide_render]
    focus,extent,_,_=bounds(visible)
    angle=-.18+index*.035+u*.06
    offset=Vector((math.sin(angle)*2.4,-2.8,1.05))
    if area in ('electronics','controller','bed','bed_detail','frame_top'):
        offset=Vector((.8,-1.5,2.8))
    camera.location=focus+offset*max(extent,.05)
    aim(camera,focus)
    bpy.context.view_layer.update()
    inverse=camera.matrix_world.inverted()
    projected=[inverse@p for o in visible for p in corners(o)]
    needed=max(max(abs(p.x) for p in projected)*2/(1080/1920),max(abs(p.y) for p in projected)*2)*1.18
    camera.data.ortho_scale=max(needed,fit or 0)
    for light,offset,power in lights:
        light.location=focus+offset*extent; light.data.energy=power*extent*extent
        light.data.size=extent*1.8; aim(light,focus)
    scene['source_model_sha256']=job['model_sha256']
    scene['episode']=job['episode']; scene['shot']=index
    return visible,needed

fits=[]
for i in range(len(shots)):
    fits.append(max(pose(i,u)[1] for u in (0,.25,.5,.75,1)))
samples=[]; preview_frames=[]
for i,s in enumerate(shots):
    preview_frames.extend([round((s['start']+(s['end']-s['start'])*u)*30)+1 for u in (.12,.7)])
preview_frames=[min(scene.frame_end,f) for f in preview_frames]
selected=preview_frames if mode=='preview' else range(1,scene.frame_end+1)
directory=folder/('preview' if mode=='preview' else 'frames'); directory.mkdir(exist_ok=True)
current=-1
for frame in selected:
    t=(frame-1)/30
    index=next((i for i,s in enumerate(shots) if s['start']<=t<s['end']),len(shots)-1)
    s=shots[index]; u=(t-s['start'])/(s['end']-s['start'])
    macro=s['action'] in ('feed','loose','retract') and u>.3
    scene.frame_set(frame); visible,needed=pose(index,u,None if macro else fits[index])
    if frame in preview_frames:
        samples.append(dict(frame=frame,shot=index,visible_parts=len(visible),camera_scale=camera.data.ortho_scale,required_scale=needed,source_positions=[dict(id=o['part_id'],position=list(o.location)) for o in sets[index] if not o.hide_render and o.get('part_id')][:120]))
        for o in objects:
            o.keyframe_insert(data_path='location',frame=frame)
            o.keyframe_insert(data_path='rotation_euler',frame=frame)
            o.keyframe_insert(data_path='hide_render',frame=frame)
        camera.keyframe_insert(data_path='location',frame=frame); camera.keyframe_insert(data_path='rotation_euler',frame=frame)
        camera.data.keyframe_insert(data_path='ortho_scale',frame=frame)
    target=directory/f'{frame:06}.jpg'
    if target.exists() and target.stat().st_size>1000 and target.read_bytes().endswith(b'\xff\xd9'): continue
    scene.render.filepath=str(target); bpy.ops.render.render(write_still=True)
assert len(samples)==16
assert len({s['shot'] for s in samples})==8
report=dict(passed=True,source_model_sha256=job['model_sha256'],shots=len(shots),source_occurrences=len(objects),samples=samples,preview_frames=preview_frames,classification='Illustrative source CAD disassembly and motion; filament, layers, displacement, color and rotation are schematic; not manufacturing or dynamic simulation')
(folder/f'{mode}-audit.json').write_text(json.dumps(report,indent=2))
scene.frame_set(1); pose(0,0,fits[0])
bpy.ops.wm.save_as_mainfile(filepath=str(folder/('preview.blend' if mode=='preview' else 'scene.blend')))
print('REMAKE_RENDER_COMPLETE',mode,flush=True)
