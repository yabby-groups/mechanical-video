"""EP02 source-CAD panel reveal; positions are illustrative."""
import json, math, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_path
from guide_mesh_path import bind, deform

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
head=[o for o in objects if '/X_Carriage/' in o.get('source_path','') or '/CW2_Assembly/' in o.get('source_path','') or '/P6_Assembly' in o.get('source_path','') or parts[o['part_id']].get('group')=='toolhead']
if not head: raise RuntimeError('Toolhead selection incomplete')
head_center,_=bounds(head)
bed=[o for o in objects if o.get('source_path','').endswith('/10in_Bed/Flex_Sheet')]
if len(bed)!=1: raise RuntimeError('Print surface selection incomplete')
bed_center,bed_extent=bounds(bed)
chain=[o for o in objects if '/X_Axis/X_Cable_Chain/' in o.get('source_path','')]
guide=[o for o in objects if '4x3mm_PTFE_Guide_Tube' in o.get('source_path','')]
if len(guide)!=1: raise RuntimeError('Expected one source guide tube')
guide_centres=np.asarray(json.loads((Path(__file__).resolve().parent/'guide_centres.json').read_text())['centres_m'])
guide_original={o.name:[v.co.copy() for v in o.data.vertices] for o in guide}
guide_bindings={}
for o in guide:
    source=np.array([tuple(originals[o.name]@v) for v in guide_original[o.name]])
    guide_bindings[o.name]=bind(source,guide_centres)
chain_args=(.245,.1224,.035,.0949,.1411)
chain_length=chain_path.length(*chain_args)
chain_samples=[chain_length*i/5000 for i in range(5001)]
chain_points=[chain_path.point(s,*chain_args) for s in chain_samples]
chain_reference={}
for obj in chain:
    pivot=sum((originals[obj.name]@Vector(c) for c in obj.bound_box),Vector())/8
    index=min(range(len(chain_points)),key=lambda i:(chain_points[i][0][0]-pivot.x)**2+(chain_points[i][0][1]-pivot.z)**2)
    chain_reference[obj.name]=(pivot,chain_samples[index],chain_points[index][1])
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
steel=mat('frame steel',(.34,.4,.43),.65); dark=mat('mechanism',(.08,.11,.12),.25); panelmat=mat('panel illustrative',(.13,.34,.37),.25); accent=mat('connection emphasis',(.68,.25,.07),.5); headmat=mat('toolhead highlight',(.13,.38,.42),.3)
railmat=mat('rail emphasis',(.34,.4,.43),.65); beammat=mat('beam emphasis',(.34,.4,.43),.65)
for o in objects:
    o.data=o.data.copy(); o.data.materials.clear(); p=o.get('source_path','')
    o.data.materials.append(panelmat if o in panels else headmat if o in head else railmat if '/MGN12_rail__1_/SOLID' in p else beammat if p.endswith('/HFSB5-20-330/SOLID') else accent if '/Frame/' in p and ('Corner' in p or 'M5x' in p) else steel if '/Frame/' in p else dark)
bpy.ops.object.camera_add(); camera=bpy.context.object; scene.camera=camera; camera.data.type='ORTHO'; camera.data.clip_start=.001
def aim(o,target): o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
lights=[]
for offset in ((1,-2,3),(-2,-1,1),(0,2,2)):
    bpy.ops.object.light_add(type='AREA'); o=bpy.context.object; o.data.shape='DISK'; o.data.size=1.5; o.data.energy=150; o.location=center+Vector(offset); aim(o,center); lights.append(o)
bpy.ops.object.light_add(type='AREA'); interior=bpy.context.object
interior.data.size=.3; interior.data.energy=3
interior.location=head_center+Vector((.05,-.12,.04)); aim(interior,head_center)
scene.world.use_nodes=True; scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.012,.017,.019,1)
try: scene.render.engine='BLENDER_EEVEE_NEXT'
except TypeError: scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1080; scene.render.resolution_y=1920; scene.render.resolution_percentage=50 if mode=='keyframes' else 25 if mode=='preview' else 100
scene.eevee.taa_render_samples=16 if mode!='production' else 32
scene.render.fps=30; scene.frame_end=job['frames']; scene.render.image_settings.file_format='JPEG'; scene.render.image_settings.quality=92
diagram=mat('schematic force indicator',(.9,.35,.03),.1)
curve=bpy.data.curves.new('schematic force arrow','CURVE'); curve.dimensions='3D'; curve.bevel_depth=.004; curve.bevel_resolution=3
line=curve.splines.new('POLY'); line.points.add(2)
arrow=bpy.data.objects.new('schematic force arrow',curve); scene.collection.objects.link(arrow); curve.materials.append(diagram)
strands=[]
for i in range(3):
    c=bpy.data.curves.new(f'illustrative layer {i}','CURVE'); c.dimensions='3D'; c.bevel_depth=.0015; c.bevel_resolution=3
    s=c.splines.new('POLY'); s.points.add(1)
    for point,dx in zip(s.points,(-.025,.025)):
        point.co=(head_center.x+dx+i*.003,head_center.y,bed_center.z+bed_extent.z/2+.002+i*.003,1)
    o=bpy.data.objects.new(f'illustrative layer {i}',c); scene.collection.objects.link(o); c.materials.append(diagram); strands.append(o)
def ease(t,a,b):
    x=max(0,min(1,(t-a)/(b-a))); return x*x*(3-2*x)
def smooth_return(t,a,b):
    x=max(0,min(1,(t-a)/(b-a))); return x*x*x*(10+x*(-15+6*x))
def pose(t):
    events=job['events']
    for o in objects:
        o.matrix_world=originals[o.name]
    opening=(ease(t,events[14]['start'],events[14]['end']+2)
             *(1-.35*ease(t,events[40]['start'],events[46]['end']))
             *(1-(smooth_return(t,events[47]['start'],job['duration']-.1) if job['duration'] > 36
                  else ease(t,events[47]['start'],events[48]['end']))))
    # Integer cycle count makes position and velocity continuous across the loop.
    cycles=max(1,round(job['duration']/6.3))
    movement=-.0075+.0075*math.sin(2*math.pi*cycles*t/job['duration'])
    for material, start, end in ((railmat,events[11]['start'],events[13]['start']),
                                 (beammat,events[12]['start'],events[14]['start']),
                                 (steel,events[35]['start'],events[40]['start'])):
        emphasis=ease(t,start,start+.6)*(1-ease(t,end,end+.6))
        color=tuple(a*(1-emphasis)+b*emphasis for a,b in zip((.34,.4,.43),(.8,.25,.04)))
        material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1)
    for o in head:
        m=originals[o.name].copy(); m.translation.x+=movement; o.matrix_world=m
    for o in chain:
        pivot,s,old_tangent=chain_reference[o.name]
        (x,z), tangent=chain_path.point(s,*chain_args,movement)
        (x0,z0),_=chain_path.point(s,*chain_args)
        angle=-(math.atan2(tangent[1],tangent[0])-math.atan2(old_tangent[1],old_tangent[0]))
        shift=Vector((x-x0,0,z-z0))
        o.matrix_world=Matrix.Translation(pivot+shift)@Matrix.Rotation(angle,4,'Y')@Matrix.Translation(-pivot)@originals[o.name]
    for o in guide:
        original=originals[o.name]; inverse=original.inverted()
        world,_=deform(guide_bindings[o.name],guide_centres,movement)
        rotation=np.asarray(inverse.to_3x3()); translation=np.asarray(inverse.translation)
        local=world@rotation.T+translation
        o.data.vertices.foreach_set('co',local.astype(np.float32).ravel())
        o.data.update()
    for o in panels:
        m=originals[o.name].copy(); p=o['source_path']; group=p.split('/')[4]
        if group=='Top_Panel': delta=Vector((0,0,.4))
        elif 'Front_Door' in group: delta=Vector((-.55 if 'Left' in group else .55,-.4,0))
        else:
            loc=sum((m@Vector(c) for c in o.bound_box),Vector())/8
            delta=Vector((.55 if loc.x>frame_center.x else -.55,0,0))
        m.translation+=delta*opening; o.matrix_world=m
    # A continuous camera move follows the panel reveal into the upper frame.
    close=1
    corner=0
    detail=frame_center+Vector((frame_extent.x*.32,-frame_extent.y*.30,frame_extent.z*.35))
    rail_reveal=.75*ease(t,3,7)*(1-ease(t,8,10.5))+ease(t,13,18)
    target=center.lerp(head_center,close).lerp(detail,corner)+Vector((.025*rail_reveal,0,-.055))
    scale=max(extent)*1.75*(1-close)+max(frame_extent)*.57*close
    scale+=max(frame_extent)*.10*ease(t,17,20)
    scale=scale*(1-corner)+max(frame_extent)*.95*corner
    reveal=ease(t,events[14]['start'],events[16]['start']+1)
    target=target.lerp(center,reveal)
    scale=scale*(1-reveal)+max(extent)*2.15*reveal
    connection=ease(t,events[19]['start'],events[21]['start'])*(1-ease(t,events[33]['start'],events[36]['start']))
    target=target.lerp(detail,connection)
    scale=scale*(1-connection)+max(extent)*1.0*connection
    printing=ease(t,events[25]['start'],events[27]['start'])*(1-ease(t,events[33]['start'],events[36]['start']))
    print_target=head_center.lerp(Vector((head_center.x,head_center.y,bed_center.z)),.4)
    target=target.lerp(print_target,printing)
    scale=scale*(1-printing)+max(extent)*.8*printing
    panel_view=ease(t,events[39]['start'],events[43]['start'])*(1-ease(t,events[46]['start'],events[48]['start']))
    target=target.lerp(center+Vector((0,0,.04)),panel_view)
    scale=scale*(1-panel_view)+max(extent)*2.15*panel_view
    returning=smooth_return(t,events[47]['start'],events[-1]['end']) if job['duration'] > 36 else 0
    target=target.lerp(head_center+Vector((0,0,-.055)),returning)
    scale=scale*(1-returning)+max(frame_extent)*.57*returning
    reveal*=1-returning
    interior_camera=target+Vector((.5,-1,.45)).normalized()*.12
    outside_camera=target+Vector((1,-2,1.2)).normalized()*max(extent)*2.5
    camera.location=interior_camera.lerp(outside_camera,reveal)
    aim(camera,target); camera.data.ortho_scale=scale
    force_start=events[21]['start']; force_end=events[34]['end']
    strength=ease(t,force_start+3,force_start+5)*(1-ease(t,force_end-2,force_end))
    sway=.008*strength*math.sin((t-force_start)*math.pi*1.1)
    if strength:
        # Apply the same illustrative shear to the entire assembly to preserve joints.
        shear=Matrix.Identity(4); shear[0][2]=sway/max(frame_extent.z,.001)
        transform=Matrix.Translation(frame_center) @ shear @ Matrix.Translation(-frame_center)
        for o in objects:
            o.matrix_world=transform @ o.matrix_world
    arrow.hide_render=not (force_start<=t<=force_end)
    for i,o in enumerate(strands):
        start=events[29]['start']+i*.5
        amount=ease(t,start,start+.8)*(1-ease(t,events[33]['end'],events[35]['start']))
        o.data.bevel_factor_end=amount
        o.hide_render=amount<=0
        o.matrix_world=transform if strength else Matrix.Identity(4)
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
