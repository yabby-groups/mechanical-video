"""Photo-guided cordless drill concept. Hidden geometry and every dimension inferred."""
import hashlib
import json
import math
import shutil
from pathlib import Path

VERSION = 2

def components():
    from build123d import Box, Cylinder, Cone, Polygon, Plane, Pos, Rot, extrude, fillet
    teal=(.004,.19,.23,1); rubber=(.025,.03,.034,1); steel=(.55,.61,.65,1)
    silver=(.72,.75,.76,1); copper=(.65,.27,.09,1); orange=(1,.20,.035,1)
    parts=[]
    def add(name, shape, xyz, group, delta, color, observed=False, material='metal'):
        shape.label=name
        if not shape.is_valid or shape.volume<=0 or len(shape.solids())!=1:
            raise ValueError(f'Invalid independent single solid: {name}')
        parts.append((shape,dict(name=name,position=list(xyz),group=group,explode=list(delta),color=color,
            inferred=True,evidence='visible exterior; dimensions and back surface inferred' if observed else 'hidden construction entirely inferred',material=material)))
    def cyl(r,l): return Rot(0,90,0)*Cylinder(r,l)
    def ring(r,ri,l): return cyl(r,l)-cyl(ri,l+2)
    def profile(points,width): return extrude(Plane.XZ*Polygon(*points,align=None),amount=width/2,both=True)
    # X axis points rearward, Z up, housing seam in XZ plane.
    body=cyl(29,93).translate((18,0,72))
    handle=profile([(-6,54),(26,52),(40,-50),(57,-60),(55,-69),(-4,-69),(-7,-55),(6,-45)],40)
    handle=fillet(handle.edges(),radius=2)
    outer=body+handle
    inner=cyl(26.5,95).translate((18,0,72))
    inner+=profile([(-2,49),(23,47),(35,-47),(40,-53),(2,-53),(11,-44)],34)
    shell=outer-inner
    for x in [46,53,60]:
        for side in [-1,1]:
            shell-=Pos(x,side*27,73)*Box(3,9,28)
    # Independent two half shells, no artificial single-mesh assembly.
    for side,label in [(-1,'left'),(1,'right')]:
        clip=Pos(15,side*50.2,5)*Box(220,100,260)
        half=shell & clip
        add(f'housing_{label}',half,(0,0,0),'shell',(5,side*90,18),teal,True,'plastic')
        grip=profile([(19,40),(28,30),(40,-43),(32,-53),(15,-52),(9,-38)],3)
        grip=fillet(grip.edges(),radius=.7)
        for z in range(-40,27,7):
            grip-=Pos(25,1.4,z)*Box(40,1.2,1.4)
        add(f'grip_{label}',grip,(0,side*20.8,0),'shell',(25,side*120,-12),rubber,True,'rubber')
        add(f'motor_side_panel_{label}',Box(51,2,22),(20,side*28.5,74),'shell',(15,side*120,70),rubber,True,'rubber')
    rear=cyl(29,8)-Pos(-2,0,0)*cyl(24,8)
    for i in range(8):
        a=2*math.pi*i/8
        rear-=Pos(0,25*math.sin(a),25*math.cos(a))*Box(12,3,7)
    add('vented_rear_cap',rear,(68,0,72),'shell',(105,0,52),rubber,True,'plastic')
    # Front clutch rings and chuck, scalloped ribs are integral features of each part.
    add('gearbox_nose',ring(28,18,15),(-36,0,72),'shell',(-35,0,50),rubber,True,'plastic')
    collar=ring(29,21,19)
    for i in range(20):
        a=i*2*math.pi/20
        collar-=Pos(0,29*math.sin(a),29*math.cos(a))*Rot(math.degrees(-a),0,0)*Box(14,3,3)
    add('torque_adjustment_collar',collar,(-53,0,72),'shell',(-70,0,40),silver,True)
    chuck=Rot(0,90,0)*Cone(19,25,42)
    chuck-=cyl(7,46)
    for i in range(12):
        a=i*2*math.pi/12
        chuck-=Pos(0,24*math.sin(a),24*math.cos(a))*Box(31,3,3)
    add('keyless_chuck_sleeve',chuck,(-85,0,72),'shell',(-130,0,15),rubber,True,'rubber')
    add('chuck_front_ring',ring(18,8,4),(-108,0,72),'shaft',(-160,0,15),silver,True)
    for i in range(3):
        a=i*2*math.pi/3
        add(f'chuck_jaw_{i+1}',cyl(2.5,18),(-108,5*math.sin(a),72+5*math.cos(a)),'shaft',(-177,25*math.sin(a),25*math.cos(a)),steel)
    add('trigger',profile([(-22,39),(-9,41),(-7,13),(-17,12)],22), (0,0,0),'control',(-40,-42,-20),rubber,True,'plastic')
    add('reverse_switch',Box(16,49,7),(-2,0,45),'control',(-10,58,-20),rubber,True,'plastic')
    add('top_speed_slider',Box(23,16,6),(16,0,103),'control',(0,0,65),rubber,True,'plastic')
    add('battery_interface',Box(65,50,9),(24,0,-68),'shell',(0,0,-32),teal,True,'plastic')
    battery=fillet(Box(96,60,34).edges(),radius=2)-Pos(0,0,3)*Box(90,54,34)
    add('battery_lower_shell',battery,(12,0,-91),'shell',(0,0,-110),rubber,True,'plastic')
    lid=Box(95,59,5)
    add('battery_lid',lid,(12,0,-72),'shell',(0,0,-56),rubber,True,'plastic')
    add('battery_release',Box(17,35,6),(-26,0,-69),'control',(-45,0,-65),teal,True,'plastic')
    add('battery_label_panel',Box(52,1,18),(21,-30.7,-91),'shell',(0,-28,-100),orange,True,'plastic')
    for i in range(5):
        # A hypothetical 5S pack, not a verified cell count or electrical design.
        add(f'inferred_cell_{i+1}',Rot(90,0,0)*Cylinder(8.8,48),(-24+i*18,0,-91),'battery',((i-2)*20,0,-75),(.18,.34,.50,1))
    add('battery_protection_pcb',Box(80,46,1.5),(12,0,-80),'electrical',(0,68,-80),(.035,.32,.10,1),material='plastic')
    add('speed_controller_pcb',Box(20,24,2),(16,0,-6),'electrical',(0,70,-10),(.03,.30,.10,1),material='plastic')
    # Generic motor: no claim of brushed/brushless topology from this photo.
    add('motor_can',ring(22,20,40),(37,0,72),'motor',(80,-45,0),steel)
    add('motor_stator',ring(19,12,30),(37,0,72),'motor',(80,15,0),copper)
    add('motor_rotor',cyl(10,28),(37,0,72),'motor',(80,65,0),steel)
    add('motor_shaft',cyl(3,62),(26,0,72),'shaft',(55,100,0),silver)
    for x,dx in [(59,112),(14,65)]:
        add(f'motor_bearing_{x}',ring(8,3.2,5),(x,0,72),'bearing',(dx,-15,0),silver)
    add('gearbox_housing',ring(23,21,34),(-7,0,72),'gearbox',(-10,45,35),steel)
    def gear(teeth,r,l,bore):
        pts=[]
        # Deliberately simplified tooth profile, not manufacturing involutes.
        for k in range(teeth):
            for offset,rad in [(0,r-1.4),(.22,r),(.62,r),(.84,r-1.4)]:
                a=(k+offset)*2*math.pi/teeth; pts.append((rad*math.cos(a),rad*math.sin(a)))
        g=extrude(Polygon(*pts,align=None),amount=l/2,both=True)-Cylinder(bore,l+2)
        return Rot(0,90,0)*g
    for stage,x in enumerate([1,-15],1):
        dx=-20-stage*27
        # Illustrative one/two-stage mechanism; teeth count is a concept assumption.
        teeth_void=gear(36,19.5,9,.01)
        ringgear=cyl(20.5,7)-(teeth_void+cyl(18,12))
        add(f'stage_{stage}_ring',ringgear,(x,0,72),'gear',(dx,0,80),steel)
        add(f'stage_{stage}_sun',gear(12,6,6,2),(x,0,72),'gear',(dx,-30,0),copper)
        for i in range(3):
            a=2*math.pi*i/3; y=12*math.sin(a); z=12*math.cos(a)
            add(f'stage_{stage}_planet_{i+1}',gear(12,6,6,2),(x,y,72+z),'gear',(dx,y*2,z*2),steel)
        add(f'stage_{stage}_carrier',ring(17,4,2),(x-5,0,72),'carrier',(dx-16,0,-30),copper)
    add('clutch_disc',ring(18,5,3),(-29,0,72),'clutch',(-93,0,-36),steel)
    add('clutch_spring_seat',ring(17,12,5),(-34,0,72),'clutch',(-111,0,-36),copper)
    add('output_spindle',cyl(5,36),(-48,0,72),'shaft',(-102,-45,-20),steel)
    for i,(x,z) in enumerate([(58,88),(58,55),(25,18),(31,-32),(43,-58)]):
        bolt=Rot(90,0,0)*(Cylinder(1.7,35)+Pos(0,0,18)*Cylinder(3,3))
        add(f'housing_screw_{i+1}',bolt,(x,0,z),'fastener',(0,-145,0),steel)
    return parts

def gen_step():
    from build123d import Compound, Pos
    return Compound(label='inferred_cordless_drill',children=[Pos(*p['position'])*shape for shape,p in components()])

def build(root):
    import fcntl
    from build123d import Compound, Pos, export_step, export_stl
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    with (root/'model.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        key='drill-'+hashlib.sha256(f'{VERSION}:'.encode()+Path(__file__).read_bytes()).hexdigest()[:16]
        folder=root/'models'/key; manifest=folder/'assembly.json'
        if manifest.exists():
            d=json.loads(manifest.read_text())
            if all((folder/p[f]).exists() for p in d['parts'] for f in ('step','stl')): return manifest
        folder.mkdir(parents=True,exist_ok=True); parts=components(); records=[]
        for shape,p in parts:
            p.update(step=p['name']+'.step',stl=p['name']+'.stl',volume_mm3=shape.volume,solids=len(shape.solids()))
            export_step(shape,folder/p['step']); export_stl(shape,folder/p['stl'],tolerance=.15)
            records.append(p)
        assembly=Compound(label='inferred_cordless_drill',children=[Pos(*p['position'])*shape for shape,p in parts])
        export_step(assembly,folder/'assembly.step'); shutil.copy2(__file__,folder/'assembly.py')
        data=dict(id=key,version=VERSION,product='cordless_drill',units='mm',parts=records,
            source_photo_sha256='4e23a5ea935841900ad2cc228ec50e706eab5fea7e502bb3bd44662ed6dfa17c',
            title='CORDLESS DRILL / INFERRED INTERNALS',
            dimensions_status='All dimensions estimated; exterior photo guided; hidden construction hypothetical.',
            caveat='Concept model, simplified teeth and motor, hypothetical 5S battery. Not a true teardown, electrical design, manufacturing model or simulation.',
            bounds_mm=list(assembly.bounding_box().size),
            datums={'drive_axis':'+X at Y=0 Z=72 mm','housing_seam':'XZ','battery_axis':'-Z'},
            parameters={'estimated_body_length_mm':190,'estimated_total_height_mm':213})
        manifest.write_text(json.dumps(data,indent=2)); return manifest
