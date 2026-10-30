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
filament_radius=.000875
feed_speed=.0025
spec=importlib.util.spec_from_file_location('archived_feed_kinematics',Path(__file__).with_name('gear_kinematics.py'))
kinematics=importlib.util.module_from_spec(spec); spec.loader.exec_module(kinematics)
def source_axis(o,index): return tuple(original[o.name].to_3x3().col[index].normalized())
drive_motion=kinematics.feed_gear(tuple(centroid(drive)),source_axis(drive,1),tuple(feed),filament_radius,feed_speed)
idler_motion=kinematics.feed_gear(tuple(centroid(idler)),source_axis(idler,1),tuple(feed),filament_radius,feed_speed)
big_motion=kinematics.coaxial_gear(tuple(centroid(big)),source_axis(big,0),tuple(centroid(drive)),drive_motion)
tooth_frequency=kinematics.tooth_cycle_frequency(big_motion['rate_rad_s'],50,15)
gear_motion={drive.name:drive_motion,idler.name:idler_motion,big.name:big_motion}
(folder/'gear-kinematics.json').write_text(json.dumps(dict(
    source_model_sha256=job['model_sha256'],feed_axis_world=(0,0,-1),feed_speed_m_s=feed_speed,
    filament_radius_m=filament_radius,drive=drive_motion,idler=idler_motion,large_gear=big_motion,
    large_gear_teeth=50,large_gear_tooth_cycles_hz=tooth_frequency,preview_sample_fps=15,
    scope='Illustrative no-slip contact with assumed filament radius; not a physical simulation'),indent=2))

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

filament_curve=bpy.data.curves.new('SCHEMATIC filament, assumed 1.75mm','CURVE')
filament_curve.dimensions='3D'; filament_curve.bevel_depth=filament_radius; filament_curve.bevel_resolution=3
filament_line=filament_curve.splines.new('POLY'); filament_line.points.add(64)
filament=bpy.data.objects.new('SCHEMATIC filament',filament_curve); scene.collection.objects.link(filament)
filament_curve.materials.append(blue)
marker=mat('SCHEMATIC high-contrast feed markers',(.36,.43,.49),.8,.28)
marker_shader=marker.node_tree.nodes.get('Principled BSDF')
marker_shader.inputs['Emission Color'].default_value=(.15,.85,1.0,1)
bands=[]
for i in range(15):
    bpy.ops.mesh.primitive_torus_add(major_radius=.00088,minor_radius=.00011,major_segments=16,minor_segments=6)
    o=bpy.context.object; o.data.materials.append(marker); bands.append(o)

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
scene.render.resolution_percentage=50
scene.render.film_transparent=False
scene.eevee.taa_render_samples=16
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
polys=[]
for layer in range(2):
    poly=curve.splines.new('POLY'); poly.points.add(len(motion.PATHS[layer][0])-1); polys.append(poly)
trace=bpy.data.objects.new('SCHEMATIC deposition',curve); scene.collection.objects.link(trace)
curve.materials.append(mat('SCHEMATIC printed polymer',(.02,.45,.65),0,.55))
# Continuous schematic melt bridge: guide filament -> nozzle -> active bead.
bridge_curve=bpy.data.curves.new('SCHEMATIC continuous extrusion bridge','CURVE')
bridge_curve.dimensions='3D'; bridge_curve.bevel_depth=.00072; bridge_curve.bevel_resolution=2
bridge_line=bridge_curve.splines.new('POLY'); bridge_line.points.add(2)
bridge=bpy.data.objects.new('SCHEMATIC continuous extrusion bridge',bridge_curve); scene.collection.objects.link(bridge)
bridge_curve.materials.append(curve.materials[0])
heat=mat('SCHEMATIC heat-zone highlight',(.65,.08,.008),.2)
heat_shader=heat.node_tree.nodes.get('Principled BSDF')
heat_shader.inputs['Emission Color'].default_value=(1,.08,.005,1)
bpy.ops.mesh.primitive_torus_add(major_radius=.007,minor_radius=.0006,major_segments=32,minor_segments=8)
heat_ring=bpy.context.object; heat_ring.name='SCHEMATIC heat-zone indicator'
heat_ring.data.materials.append(heat)

def pose(frame):
    t=(frame-1)/30; s=motion.state(t); opening=s['open']
    shift=Vector((s['x'],s['y'],z_drop*s['bed']+s['lift']))
    if 53<t<90:
        q=motion.deposition(t)
        layer=0 if q<=1 else 1
        px,py=motion.deposition_point(q-layer,layer)
        blend=motion.ease(t,53,55)*(1-motion.ease(t,86,90))
        shift.x+=px*.025*blend; shift.y+=py*.025*blend
    for o in objects:
        path=o['source_path']; m=original[o.name].copy()
        housing='/CW2_Printed/' in path or '/CW2_hardware/' in path
        if housing:
            r=m.translation-center
            m.translation+=Vector((1 if r.x>=0 else -1,-.1,.08))*.055*opening
        if 'Stealthburner' in path or ('SB_TOOLHEAD' in path and '/P6_Assembly' not in path): m.translation+=Vector((.14,-.015,.025))*opening
        if path.endswith('/LDO-36STH20'): m.translation.y+=.035*opening
        if o.name in gear_motion:
            axis=Vector(gear_motion[o.name]['axis'])
            pivot=sum((original[o.name]@Vector(c) for c in o.bound_box),Vector())/8
            angle=t*gear_motion[o.name]['rate_rad_s']
            m=Matrix.Translation(pivot)@Matrix.Rotation(angle,4,axis)@Matrix.Translation(-pivot)@m
        # Hierarchical illustrative X carriage / Y beam / Z gantry movement.
        is_head='/X_Carriage/' in path or '/CW2_Assembly/' in path or '/P6_Assembly' in path or o['group']=='toolhead' or '4x3mm_PTFE_Guide_Tube' in path
        if '/Gantry/' in path or is_head or o['group']=='gantry':
            m.translation.z+=shift.z
            if '/X_Axis/' in path or is_head: m.translation.y+=shift.y
            if is_head: m.translation.x+=shift.x
        if o['group']=='panels':
            r=original[o.name].translation-all_center
            m.translation.x+=(1 if r.x>=0 else -1)*1.0
        o.matrix_world=m; o.hide_render=False
    filament.location=feed+shift
    bending=0
    def bend(z):
        u=max(0,min(1,(-z-.004)/.045))
        return .009*math.sin(math.pi*u)*bending
    for i,p in enumerate(filament_line.points):
        z=-.055+.11*i/64
        p.co=(bend(z),0,z,1)
    heat_ring.location=Vector((feed.x,feed.y,nozzle_bottom+.004))+shift
    heat_shader.inputs['Emission Strength'].default_value=2*motion.ease(t,30,34)*(1-motion.ease(t,90,99.966667))
    for i,o in enumerate(bands):
        # Feed indicators pass out of the ends outside the focused working zone.
        z=((i*.008-t*feed_speed+.055)%.11)-.055
        o.location=feed+shift+Vector((bend(z),0,z))
    target=center.lerp(gear_center,s['macro']).lerp(hot_center,s['down'])+shift
    target=target.lerp(Vector((hot_center.x,hot_center.y,bed_top+.025)),s['bed']*.45)
    target=target.lerp(all_center,s['wide']*.50)
    target=target.lerp(Vector((feed.x+shift.x,feed.y+shift.y,bed_top+.025)),s['detail'])
    target=target.lerp(all_center,s['whole'])
    focus=motion.ease(t,6,12)*(1-motion.ease(t,21,27))
    guide=motion.ease(t,23,27)*(1-motion.ease(t,27,34))
    target+=Vector((0,0,-.005))*guide
    emphasis=motion.ease(t,5,9)*(1-motion.ease(t,27,34))
    marker_shader.inputs['Emission Strength'].default_value=.75*emphasis
    marker_shader.inputs['Base Color'].default_value=tuple(a+(b-a)*emphasis for a,b in zip((.36,.43,.49,1),(.15,.85,1.,1)))
    scale=(.28*(1-s['macro'])+.075*s['macro'])*(1-s['down'])+.13*s['down']
    scale=scale*(1-s['bed'])+.30*s['bed']
    scale=scale*(1-s['wide'])+all_size*.85*s['wide']
    scale=scale*(1-s['detail'])+.24*s['detail']
    scale=scale*(1-s['whole'])+all_size*1.95*s['whole']
    scale*=1-.18*focus
    camera.location=target+Vector((.12,-1,.22))*(.3*(1-s['wide'])+all_size*2*s['wide'])
    aim(camera,target); camera.data.ortho_scale=scale
    for light in lights:
        offset=(Vector((1,-2,3)) if light==lights[0] else Vector((-2,-1,.5)) if light==lights[1] else Vector((0,2,1)))
        span=max(.15,scale*.75); light.location=target+offset*span
        light.data.size=span; light.data.energy=70*span*span; aim(light,target)
    progress=motion.deposition(t)*(1-motion.ease(t,86,90))
    active_layer=0 if progress<=1 else 1
    active_x,active_y=motion.deposition_point(progress-active_layer,active_layer)
    nozzle_point=Vector((feed.x,feed.y,nozzle_bottom))+shift
    bead_point=Vector((feed.x+active_x*.025,feed.y+active_y*.025,bed_top+.001+active_layer*.0015))
    bridge_line.points[0].co=(feed.x+shift.x,feed.y+shift.y,nozzle_point.z+.045,1)
    bridge_line.points[1].co=(*nozzle_point,1)
    bridge_line.points[2].co=(*bead_point,1)
    bridge.hide_render=not (53<t<90 and progress>0)
    for layer,poly in enumerate(polys):
        layer_progress=max(0,min(1,progress-layer))
        for p,fraction in zip(poly.points,motion.PATHS[layer][3]):
            x,y=motion.deposition_point(min(fraction,layer_progress),layer)
            p.co=(feed.x+x*.025,feed.y+y*.025,bed_top+.001+layer*.0015,1)
    scene['source_model_sha256']=job['model_sha256']; scene['shot']=0
    return 0

frames=folder/('keyframes' if mode=='keyframes' else 'frames'); frames.mkdir(exist_ok=True)
sample=job['keyframes']
chosen=job['keyframes'] if mode=='keyframes' else range(1,job['end_frame']+1)
audit=[]; continuity=[]; gear_continuity=[]; previous=None
for f in chosen:
    scene.frame_set(f); index=pose(f); bpy.context.view_layer.update()
    current=dict(frame=f,camera=list(camera.location),positions={o.name:list(o.matrix_world.translation) for o in objects},scale=camera.data.ortho_scale,visible=[o['part_id'] for o in objects if not o.hide_render],rotations={o.name:o.matrix_world.to_quaternion() for o in (drive,idler,big)},band_z=bands[0].location.z-(feed.z+z_drop*motion.state((f-1)/30)['bed']+motion.state((f-1)/30)['lift']))
    if previous is not None and mode!='keyframes':
        delta=(camera.location-Vector(previous['camera'])).length
        zoom=abs(current['scale']-previous['scale'])
        assert delta<.03 and zoom<.04 and current['visible']==previous['visible']
        part_step=max((o.matrix_world.translation-Vector(previous['positions'][o.name])).length for o in objects)
        assert part_step<.03
        continuity.append(dict(frame=f,camera_step=delta,zoom_step=zoom,part_step=part_step))
        dt=(f-previous['frame'])/30
        observed={}
        for gear in (drive,idler,big):
            q=current['rotations'][gear.name] @ previous['rotations'][gear.name].inverted()
            q.normalize()
            if q.w<0: q.negate()
            axis,angle=q.to_axis_angle()
            observed[gear.name]=axis*(angle/dt)
        velocities={}
        for gear in (drive,idler):
            v=observed[gear.name].cross(Vector(gear_motion[gear.name]['contact_vector_m']))
            assert abs(v.z+feed_speed)<.00002 and abs(v.x)<.00002 and abs(v.y)<.00002
            velocities[gear.name]=list(v)
        shaft_error=(observed[drive.name]-observed[big.name]).length
        assert shaft_error<.01
        marker_delta=(current['band_z']-previous['band_z']+.055)%.11-.055
        marker_speed=marker_delta/dt
        assert abs(marker_speed+feed_speed)<.00002
        gear_continuity.append(dict(frame=f,drive_contact_m_s=velocities[drive.name],idler_contact_m_s=velocities[idler.name],shaft_angular_error_rad_s=shaft_error,filament_marker_speed_m_s=marker_speed))
    previous=current
    if f in sample:
        audit.append(dict(frame=f,shot=index,visible_ids=[o['part_id'] for o in objects if not o.hide_render],camera_scale=camera.data.ortho_scale))
    output=frames/f'{f:06}.jpg'
    if output.exists() and output.read_bytes().endswith(b'\xff\xd9'): continue
    scene.render.filepath=str(output); bpy.ops.render.render(write_still=True)
pose(1); bpy.ops.wm.save_as_mainfile(filepath=str(folder/(mode+'.blend')))
(folder/'source-paths.json').write_text(json.dumps({o.name:o['source_path'] for o in objects},indent=2))
(folder/f'{mode}-audit.json').write_text(json.dumps(dict(source_model_sha256=job['model_sha256'],source_parts=len(objects),samples=audit,shots=1,hard_cuts=0,visibility_changes=0,continuity=continuity,gear_continuity=gear_continuity,cutaway='Disabled; original housing moves continuously',motion='Illustrative; no certified meshing physics or recorded machine sound'),indent=2))
