"""One continuous reveal/feed/tracking move; unchanged CW2/Revo source geometry."""
import importlib.util
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

args=sys.argv[sys.argv.index('--')+1:]; job=json.loads(Path(args[0]).read_text()); mode=args[1]
folder=Path(job['folder']); parts={p['id']:p for p in job['parts']}
bpy.ops.wm.open_mainfile(filepath=job['source_scene'])
scene=bpy.context.scene; scene.animation_data_clear(); objects=[]; original={}
for o in list(scene.objects):
    p=o.get('source_path','')
    if o.get('part_id') in parts:
        o.animation_data_clear(); o.parent=None
        m=Matrix(parts[o['part_id']]['matrix_mm']); m.translation*=.001; o.matrix_world=m
        original[o.name]=m.copy(); objects.append(o)
    else: bpy.data.objects.remove(o,do_unlink=True)
bpy.context.view_layer.update()
def centroid(o): return sum((o.matrix_world@Vector(c) for c in o.bound_box),Vector())/8
def bounds(items):
    points=[o.matrix_world@Vector(c) for o in items for c in o.bound_box]
    lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    return (lo+hi)/2,max(hi-lo)
all_center,all_size=bounds(objects)
local=[o for o in objects if '/CW2_Assembly/' in o['source_path'] or '/P6_Assembly' in o['source_path']]
center,size=bounds(local)
bed_parts=[o for o in objects if o['group']=='bed']
bed_center,bed_size=bounds(bed_parts)
bed_top=max((o.matrix_world@Vector(c)).z for o in bed_parts for c in o.bound_box)
drive=next(o for o in objects if o['source_path'].endswith('/Drive_Gear'))
idler=next(o for o in objects if o['source_path'].endswith('/Idler_Gear'))
big=next(o for o in objects if o['source_path'].endswith('/50T_Drive_Gear'))
feed=(centroid(drive)+centroid(idler))/2
gear_center=feed.copy()
hotend=[o for o in objects if '/P6_Assembly' in o['source_path']]
hot_center,hot_size=bounds(hotend)

def mat(name,color,metal,rough=.3):
    m=bpy.data.materials.new(name); m.use_nodes=True
    s=m.node_tree.nodes.get('Principled BSDF'); s.inputs['Base Color'].default_value=(*color,1)
    s.inputs['Metallic'].default_value=metal; s.inputs['Roughness'].default_value=rough
    return m
shell=mat('graphite shell',(.035,.055,.072),.3)
copper=mat('copper display emphasis',(.68,.21,.045),.7,.24)
steel=mat('brushed display steel',(.36,.43,.49),.8,.28)
blue=mat('schematic feed',(.02,.45,.65),.3,.25)
for o in objects:
    o.data=o.data.copy(); o.data.materials.clear(); p=o['source_path']
    o.data.materials.append(copper if 'Gear' in p else shell if '/CW2_Printed/' in p else steel)

bpy.ops.mesh.primitive_cube_add(size=1)
cutter=bpy.context.object; cutter.name='DISPLAY CUTAWAY plane volume'; cutter.scale=(.5,.5,.5); cutter.hide_render=True
cut_mods=[]
for o in objects:
    if '/CW2_Printed/' in o['source_path']:
        m=o.modifiers.new('Source housing cutaway (display only)','BOOLEAN'); m.operation='DIFFERENCE'; m.object=cutter
        try: m.solver='FLOAT'
        except TypeError: m.solver='FAST'
        cut_mods.append(m)

bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.000875,depth=.11,location=feed)
filament=bpy.context.object; filament.name='SCHEMATIC filament 1.75mm assumed'; filament.data.materials.append(blue)
bands=[]
for i in range(15):
    bpy.ops.mesh.primitive_torus_add(major_radius=.00088,minor_radius=.00011,major_segments=16,minor_segments=6)
    o=bpy.context.object; o.data.materials.append(steel); bands.append(o)

bpy.ops.object.camera_add(); camera=bpy.context.object; scene.camera=camera
camera.data.type='ORTHO'; camera.data.clip_start=.001
def aim(o,target): o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
lights=[]
for offset,power in [((1,-2,3),.7),((-2,-1,.5),.45),((0,2,1),.85)]:
    bpy.ops.object.light_add(type='AREA'); o=bpy.context.object; o.data.shape='DISK'; o.data.size=.15; o.data.energy=power
    o.location=center+Vector(offset)*.1; aim(o,center); lights.append(o)
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.006,.012,.018,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
try: scene.render.engine='BLENDER_EEVEE_NEXT'
except TypeError: scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1080; scene.render.resolution_y=1920
scene.render.resolution_percentage=25 if mode=='preview' else 100
scene.eevee.taa_render_samples=16 if mode=='preview' else 32
scene.render.fps=30; scene.frame_end=3000
scene.render.image_settings.file_format='JPEG'; scene.render.image_settings.quality=95
scene.view_settings.view_transform='AgX'
spec=importlib.util.spec_from_file_location('archived_hook_motion',Path(__file__).with_name('motion.py'))
motion=importlib.util.module_from_spec(spec); spec.loader.exec_module(motion)
# Persistent source geometry: no visibility switches or assembly resets.
nozzle_bottom=min((o.matrix_world@Vector(c)).z for o in hotend for c in o.bound_box)
z_drop=bed_top+.002-nozzle_bottom
# A progressively drawn path is schematic and stays on the fixed bed.
curve=bpy.data.curves.new('Illustrative deposition, not G-code','CURVE')
curve.dimensions='3D'; curve.bevel_depth=.0009; curve.bevel_resolution=1
poly=curve.splines.new('POLY'); poly.points.add(256)
trace=bpy.data.objects.new('SCHEMATIC deposition',curve); scene.collection.objects.link(trace)
curve.materials.append(copper)

def pose(frame):
    t=(frame-1)/30; s=motion.state(t); opening=s['open']
    shift=Vector((s['x'],s['y'],z_drop*s['bed']+s['lift']))
    if 72<t<90:
        q=motion.ease(t,73,87)*12; u=q%4; edge=min(3,int(u)); v=u-edge
        corners=[(-1,-1),(1,-1),(1,1),(-1,1),(-1,-1)]
        px=corners[edge][0]*(1-v)+corners[edge+1][0]*v
        py=corners[edge][1]*(1-v)+corners[edge+1][1]*v
        blend=motion.ease(t,72,73)*(1-motion.ease(t,87,90))
        shift.x+=px*.025*blend; shift.y+=py*.025*blend
    for o in objects:
        path=o['source_path']; m=original[o.name].copy()
        housing='/CW2_Printed/' in path or '/CW2_hardware/' in path
        if housing:
            r=m.translation-center
            m.translation+=Vector((1 if r.x>=0 else -1,-.1,.08))*.055*opening
        if 'Stealthburner' in path or ('SB_TOOLHEAD' in path and '/P6_Assembly' not in path): m.translation+=Vector((.14,-.015,.025))*opening
        if path.endswith('/LDO-36STH20'): m.translation.y+=.035*opening
        gear=path.endswith(('/Drive_Gear','/Idler_Gear','/50T_Drive_Gear'))
        if gear:
            axis=m.to_3x3().col[0 if path.endswith('/50T_Drive_Gear') else 1].normalized()
            pivot=sum((original[o.name]@Vector(c) for c in o.bound_box),Vector())/8
            angle=t*1.05*(1 if path.endswith('/Idler_Gear') else -1)
            m=Matrix.Translation(pivot)@Matrix.Rotation(angle,4,axis)@Matrix.Translation(-pivot)@m
        # Hierarchical illustrative X carriage / Y beam / Z gantry movement.
        is_head='/X_Carriage/' in path or '/CW2_Assembly/' in path or '/P6_Assembly' in path or o['group']=='toolhead'
        if '/Gantry/' in path or is_head or o['group']=='gantry':
            m.translation.z+=shift.z
            if '/X_Axis/' in path or is_head: m.translation.y+=shift.y
            if is_head: m.translation.x+=shift.x
        if o['group']=='panels':
            r=original[o.name].translation-all_center
            m.translation.x+=(1 if r.x>=0 else -1)*1.0*(1-motion.ease(t,90,100))
        o.matrix_world=m; o.hide_render=False
    filament.location=feed+shift
    for i,o in enumerate(bands):
        # Feed indicators pass out of the ends outside the focused working zone.
        o.location=feed+shift+Vector((0,0,((i*.008-t*.007+.055)%.11)-.055))
    target=center.lerp(gear_center,s['macro']).lerp(hot_center,s['down'])+shift
    target=target.lerp(Vector((hot_center.x,hot_center.y,bed_top+.025)),s['bed']*.45)
    target=target.lerp(all_center,s['wide']*.65).lerp(all_center,s['whole'])
    scale=(.28*(1-s['macro'])+.075*s['macro'])*(1-s['down'])+.13*s['down']
    scale=scale*(1-s['bed'])+.30*s['bed']
    scale=scale*(1-s['wide'])+all_size*1.25*s['wide']
    scale=scale*(1-s['whole'])+all_size*1.95*s['whole']
    camera.location=target+Vector((.12,-1,.22))*(.3*(1-s['wide'])+all_size*2*s['wide'])
    aim(camera,target); camera.data.ortho_scale=scale
    for light in lights:
        offset=(Vector((1,-2,3)) if light==lights[0] else Vector((-2,-1,.5)) if light==lights[1] else Vector((0,2,1)))
        span=max(.15,scale*.75); light.location=target+offset*span
        light.data.size=span; light.data.energy=70*span*span; aim(light,target)
    progress=motion.ease(t,73,87)
    for i,p in enumerate(poly.points):
        q=min(i/256,progress)*12; layer=min(2,int(q//4)); u=q%4; edge=min(3,int(u)); v=u-edge
        path=[(-1,-1),(1,-1),(1,1),(-1,1),(-1,-1)]
        x=path[edge][0]*(1-v)+path[edge+1][0]*v
        y=path[edge][1]*(1-v)+path[edge+1][1]*v
        p.co=(hot_center.x+x*.025,hot_center.y+y*.025,bed_top+.001+layer*.0015,1)
    scene['source_model_sha256']=job['model_sha256']; scene['shot']=0
    return 0

frames=folder/('preview' if mode=='preview' else 'frames'); frames.mkdir(exist_ok=True)
sample=[1,91,360,720,1080,1440,1740,2040,2400,2700,2999]
chosen=range(1,3001,4) if mode=='preview' else range(1,3001)
audit=[]; continuity=[]; previous=None
for f in chosen:
    scene.frame_set(f); index=pose(f); bpy.context.view_layer.update()
    current=dict(camera=list(camera.location),positions={o.name:list(o.matrix_world.translation) for o in objects},scale=camera.data.ortho_scale,visible=[o['part_id'] for o in objects if not o.hide_render])
    if previous is not None :
        delta=(camera.location-Vector(previous['camera'])).length
        zoom=abs(current['scale']-previous['scale'])
        assert delta<.03 and zoom<.04 and current['visible']==previous['visible']
        part_step=max((o.matrix_world.translation-Vector(previous['positions'][o.name])).length for o in objects)
        assert part_step<.03
        continuity.append(dict(frame=f,camera_step=delta,zoom_step=zoom,part_step=part_step))
    previous=current
    if f in sample:
        audit.append(dict(frame=f,shot=index,visible_ids=[o['part_id'] for o in objects if not o.hide_render],camera_scale=camera.data.ortho_scale))
    output=frames/f'{f:06}.jpg'
    if output.exists() and output.read_bytes().endswith(b'\xff\xd9'): continue
    scene.render.filepath=str(output); bpy.ops.render.render(write_still=True)
pose(16); bpy.ops.wm.save_as_mainfile(filepath=str(folder/('preview.blend' if mode=='preview' else 'scene.blend')))
(folder/'source-paths.json').write_text(json.dumps({o.name:o['source_path'] for o in objects},indent=2))
(folder/f'{mode}-audit.json').write_text(json.dumps(dict(source_model_sha256=job['model_sha256'],source_parts=len(objects),samples=audit,shots=1,hard_cuts=0,visibility_changes=0,continuity=continuity,cutaway='Disabled; original housing moves continuously',motion='Illustrative; no certified meshing physics or recorded machine sound'),indent=2))
