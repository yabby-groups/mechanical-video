"""EP02 source-CAD panel reveal; positions are illustrative."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

job=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text())
folder=Path(job['folder']); mode=job['mode']
parts={p['id']:p for p in job['parts']}
bpy.ops.wm.open_mainfile(filepath=job['source_scene'])
scene=bpy.context.scene; scene.animation_data_clear(); objects=[]; originals={}
for obj in list(scene.objects):
    if obj.get('part_id') not in parts:
        bpy.data.objects.remove(obj,do_unlink=True); continue
    obj.animation_data_clear(); obj.parent=None
    m=Matrix(parts[obj['part_id']]['matrix_mm']); m.translation*=.001
    obj.matrix_world=m; originals[obj.name]=m.copy(); objects.append(obj)
bpy.context.view_layer.update()
def bounds(items):
    points=[o.matrix_world@Vector(c) for o in items for c in o.bound_box]
    lo=Vector([min(p[i] for p in points) for i in range(3)])
    hi=Vector([max(p[i] for p in points) for i in range(3)])
    return (lo+hi)/2,hi-lo
center,extent=bounds(objects)
frame=[o for o in objects if '/Frame/' in o.get('source_path','')]
frame_center,frame_extent=bounds(frame)
panels=[]
for o in objects:
    p=o.get('source_path','')
    if '/Panels/Transparent_Panels/' in p and (p.endswith('/SOLID') and p.count('/')==5 or p.endswith('/Foam_Tape__3mm_')):
        panels.append(o)
if len(panels)<4: raise RuntimeError('Panel selection incomplete')
def mat(name,color,metal=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*color,1); bs.inputs['Metallic'].default_value=metal
    return m
steel=mat('frame steel',(.34,.4,.43),.65); dark=mat('mechanism',(.08,.11,.12),.25); panelmat=mat('panel illustrative',(.13,.34,.37),.25); accent=mat('connection emphasis',(.68,.25,.07),.5)
for o in objects:
    o.data=o.data.copy(); o.data.materials.clear(); p=o.get('source_path','')
    o.data.materials.append(panelmat if o in panels else accent if '/Frame/' in p and ('Corner' in p or 'M5x' in p) else steel if '/Frame/' in p else dark)
bpy.ops.object.camera_add(); camera=bpy.context.object; scene.camera=camera; camera.data.type='ORTHO'; camera.data.clip_start=.001
def aim(o,target): o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
lights=[]
for offset in ((1,-2,3),(-2,-1,1),(0,2,2)):
    bpy.ops.object.light_add(type='AREA'); o=bpy.context.object; o.data.shape='DISK'; o.data.size=1.5; o.data.energy=150; o.location=center+Vector(offset); aim(o,center); lights.append(o)
scene.world.use_nodes=True; scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.012,.017,.019,1)
try: scene.render.engine='BLENDER_EEVEE_NEXT'
except TypeError: scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1080; scene.render.resolution_y=1920; scene.render.resolution_percentage=25 if mode in ('keyframes','preview') else 100
scene.eevee.taa_render_samples=16 if mode!='production' else 32
scene.render.fps=30; scene.frame_end=job['frames']; scene.render.image_settings.file_format='JPEG'; scene.render.image_settings.quality=92
diagram=mat('schematic force indicator',(.9,.35,.03),.1)
curve=bpy.data.curves.new('schematic force arrow','CURVE'); curve.dimensions='3D'; curve.bevel_depth=.004; curve.bevel_resolution=3
line=curve.splines.new('POLY'); line.points.add(2)
arrow=bpy.data.objects.new('schematic force arrow',curve); scene.collection.objects.link(arrow); curve.materials.append(diagram)
def ease(t,a,b):
    x=max(0,min(1,(t-a)/(b-a))); return x*x*(3-2*x)
def pose(t):
    opening=ease(t,0,11)*(1-ease(t,job['duration']-16,job['duration']-3))
    for o in panels:
        m=originals[o.name].copy(); p=o['source_path']; group=p.split('/')[4]
        if group=='Top_Panel': delta=Vector((0,0,.12))
        elif 'Front_Door' in group: delta=Vector((-.06 if 'Left' in group else .06,-.14,0))
        else:
            loc=sum((m@Vector(c) for c in o.bound_box),Vector())/8
            delta=Vector((.13 if loc.x>frame_center.x else -.13,0,0))
        m.translation+=delta*opening; o.matrix_world=m
    # A continuous camera move follows the panel reveal into the upper frame.
    near=ease(t,8,25)*(1-ease(t,57,75))
    travel=ease(t,46,57)
    detail=frame_center+Vector((frame_extent.x*(.32-.48*travel),-frame_extent.y*.30,frame_extent.z*.35))
    target=center.lerp(detail,near)
    scale=max(extent)*2.65*(1-near)+max(frame_extent)*1.05*near
    camera.location=target+Vector((1,-2,1.2)).normalized()*max(extent)*2.5
    aim(camera,target); camera.data.ortho_scale=scale
    force_start=job['events'][3]['start']; force_end=job['events'][3]['end']
    strength=ease(t,force_start+3,force_start+5)*(1-ease(t,force_end-2,force_end))
    sway=.008*strength*math.sin((t-force_start)*math.pi*1.1)
    for o in frame:
        m=originals[o.name].copy()
        # Affine shear is an exaggerated diagram, not a physical simulation.
        shear=Matrix.Identity(4); shear[0][2]=sway/max(frame_extent.z,.001)
        m=Matrix.Translation(frame_center) @ shear @ Matrix.Translation(-frame_center) @ m
        o.matrix_world=m
    arrow.hide_render=not (force_start<=t<=force_end)
    base=frame_center+Vector((frame_extent.x*.28,-frame_extent.y*.32,frame_extent.z*.32))+Vector((.08,-.16,.10))
    pulse=.025*math.sin((t-force_start)*math.pi*1.4)
    for p,offset in zip(line.points,((-.06,0,0),(.03+pulse,0,0),(.012+pulse,0,.015))):
        p.co=(*tuple(base+Vector(offset)),1)
    return opening
out=folder/('keyframes' if mode=='keyframes' else 'preview' if mode=='preview' else 'frames'); out.mkdir(exist_ok=True)
chosen=job['samples'] if mode=='keyframes' else range(1,job['frames']+1,3 if mode=='preview' else 1)
audit=[]
for f in chosen:
    scene.frame_set(f); opening=pose((f-1)/30); bpy.context.view_layer.update()
    target=out/f'{f:06}.jpg'
    if not target.exists() or not target.read_bytes().endswith(b'\xff\xd9'):
        scene.render.filepath=str(target); bpy.ops.render.render(write_still=True)
    if f in job['samples']: audit.append(dict(frame=f,opening=opening,camera=list(camera.location),scale=camera.data.ortho_scale))
pose(0); bpy.ops.wm.save_as_mainfile(filepath=str(folder/('preview.blend' if mode!='production' else 'scene.blend')))
(folder/f'{mode}-audit.json').write_text(json.dumps(dict(source_model_sha256=job['model_sha256'],panel_paths=[o['source_path'] for o in panels],samples=audit,scope='Illustrative disassembly, not physical simulation'),indent=2))
