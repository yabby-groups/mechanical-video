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
    if '/CW2_Assembly/' in p or '/P6_Assembly' in p:
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
center,size=bounds(objects)
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
scene.render.resolution_percentage=35 if mode=='preview' else 100
scene.render.fps=30; scene.frame_end=450
scene.render.image_settings.file_format='JPEG'; scene.render.image_settings.quality=95
scene.view_settings.view_transform='AgX'
spec=importlib.util.spec_from_file_location('archived_hook_motion',Path(__file__).with_name('motion.py'))
motion=importlib.util.module_from_spec(spec); spec.loader.exec_module(motion)
def pose(frame):
    t=(frame-1)/30; opening,close,down,back,scale=motion.envelopes(t)
    for o in objects: o.matrix_world=original[o.name]; o.hide_render=False
    for m in cut_mods: m.show_render=False
    for o in objects:
        path=o['source_path']; m=original[o.name].copy()
        housing='/CW2_Printed/' in path or '/CW2_hardware/' in path
        gear=path.endswith(('/Drive_Gear','/Idler_Gear','/50T_Drive_Gear'))
        if housing:
            r=centroid(o)-center
            m.translation+=Vector((1 if r.x>=0 else -1,-.1,.08))*.055*opening
        if path.endswith('/LDO-36STH20'): m.translation.y+=.035*opening
        if gear:
            axis=m.to_3x3().col[0 if path.endswith('/50T_Drive_Gear') else 1].normalized()
            pivot=centroid(o); angle=t*1.05*(1 if path.endswith('/Idler_Gear') else -1)
            m=Matrix.Translation(pivot)@Matrix.Rotation(angle,4,axis)@Matrix.Translation(-pivot)@m
        o.matrix_world=m
    filament.hide_render=False
    for i,o in enumerate(bands):
        o.hide_render=False
        # Wrap is entirely outside the macro view; no visible objects pop on/off.
        o.location=feed+Vector((0,0,((i*.008-t*.007+.055)%.11)-.055))
    target=center.lerp(gear_center,close).lerp(hot_center,down).lerp(center,back)
    offset=Vector((.12,-1,.22))
    camera.location=target+offset*.3; aim(camera,target); camera.data.ortho_scale=scale
    scene['source_model_sha256']=job['model_sha256']; scene['shot']=0
    return 0

frames=folder/('preview' if mode=='preview' else 'frames'); frames.mkdir(exist_ok=True)
sample=[16,67,126,189,258,326,387,432]
chosen=sample if mode=='preview' else range(1,451)
audit=[]; continuity=[]; previous=None
for f in chosen:
    scene.frame_set(f); index=pose(f); bpy.context.view_layer.update()
    current=dict(camera=list(camera.location),scale=camera.data.ortho_scale,visible=[o['part_id'] for o in objects if not o.hide_render])
    if previous is not None and mode!='preview':
        delta=(camera.location-Vector(previous['camera'])).length
        zoom=abs(current['scale']-previous['scale'])
        assert delta<.003 and zoom<.005 and current['visible']==previous['visible']
        continuity.append(dict(frame=f,camera_step=delta,zoom_step=zoom))
    previous=current
    if f in sample:
        audit.append(dict(frame=f,shot=index,visible_ids=[o['part_id'] for o in objects if not o.hide_render],camera_scale=camera.data.ortho_scale))
    output=frames/f'{f:06}.jpg'
    if output.exists() and output.read_bytes().endswith(b'\xff\xd9'): continue
    scene.render.filepath=str(output); bpy.ops.render.render(write_still=True)
pose(16); bpy.ops.wm.save_as_mainfile(filepath=str(folder/('preview.blend' if mode=='preview' else 'scene.blend')))
(folder/f'{mode}-audit.json').write_text(json.dumps(dict(source_model_sha256=job['model_sha256'],source_parts=len(objects),samples=audit,shots=1,hard_cuts=0,visibility_changes=0,continuity=continuity,cutaway='Disabled; original housing moves continuously',motion='Illustrative; no certified meshing physics or recorded machine sound'),indent=2))
