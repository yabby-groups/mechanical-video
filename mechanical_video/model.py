import hashlib
import json
import math
from pathlib import Path

VERSION = 7

def _build(root: Path, params=None):
    from build123d import Cylinder, Polygon, extrude, export_stl, export_step, Compound, Pos, Rot
    params = params or {}
    module = float(params.get('module', 2))
    if not 0.5 <= module <= 5:
        raise ValueError('module must be between 0.5 and 5 mm')
    params = {} if module == 2 else {'module': module}
    key = hashlib.sha256(json.dumps([VERSION, params], sort_keys=True).encode()).hexdigest()[:16]
    folder = root / 'models' / key
    manifest = folder / 'assembly.json'
    if manifest.exists():
        data = json.loads(manifest.read_text())
        if all((folder / p['stl']).exists() and (folder / p['step']).exists() for p in data['parts']):
            return manifest
    folder.mkdir(parents=True, exist_ok=True)
    scale = module / 2
    parts, shapes = [], []
    def add(name, shape, xyz, group, explode, color, inferred=True):
        if not shape.is_valid or shape.volume <= 0:
            raise ValueError(f'Invalid solid: {name}')
        export_stl(shape, folder / f'{name}.stl', tolerance=0.12)
        export_step(shape, folder / f'{name}.step')
        parts.append(dict(name=name, stl=f'{name}.stl', step=f'{name}.step', position=xyz,
                          group=group, explode=explode, color=color, inferred=inferred,
                          volume_mm3=shape.volume, solids=len(shape.solids())))
        shapes.append(Pos(*xyz) * shape)
    def cyl(r,h): return Cylinder(r*scale,h*scale)
    def ring(ro,ri,h): return cyl(ro,h)-cyl(ri,h+2)
    def gear(n,h,bore=3,internal=False):
        # Involute flank sampled from base circle; 20-degree pressure angle.
        rp=n*module/2; rb=rp*math.cos(math.radians(20)); ra=rp+module; rf=rp-1.25*module
        if internal: ra=rp+1.25*module; rf=rp-module
        invp=math.tan(math.acos(rb/rp))-math.acos(rb/rp)
        pts=[]
        for k in range(n):
            center=k*2*math.pi/n
            pts.append((rf*math.cos(center-math.pi/n),rf*math.sin(center-math.pi/n)))
            for side, radii in [(-1,[max(rb,rf),rp,ra]),(1,[ra,rp,max(rb,rf)])]:
                for r in radii:
                    alpha=math.acos(min(1,rb/r)); inv=math.tan(alpha)-alpha
                    angle=center+side*((math.pi/(2*n)-invp+inv if internal else math.pi/(2*n)+invp-inv))
                    pts.append((r*math.cos(angle),r*math.sin(angle)))
            pts.append((rf*math.cos(center+math.pi/n),rf*math.sin(center+math.pi/n)))
        solid=extrude(Polygon(*pts,align=None),amount=h*scale)
        solid=Pos(0,0,-h*scale/2)*solid
        return solid-cyl(bore,h+2) if bore else solid
    steel=[0.45,0.56,0.68,1]; gold=[0.9,0.48,0.09,1]; blue=[0.04,0.19,0.34,1]
    add('rear_cover',ring(53,6,5),[0,0,-15*scale],'shell',[0,0,-65*scale],blue)
    # Internal teeth: subtract a 48-tooth involute outline from an outer cylinder.
    cutter=gear(48,18,0,internal=True).scale(1.06)
    add('ring_gear',cyl(55,14)-cutter,[0,0,0],'shell',[0,0,-30*scale],steel)
    add('sun_gear',gear(18,10,4),[0,0,0],'gear',[0,0,35*scale],gold)
    for i in range(3):
        a=2*math.pi*i/3; x=33*scale*math.cos(a); y=33*scale*math.sin(a)
        planet=gear(15,10,3).scale(0.97)
        add(f'planet_{i+1}',planet,[x,y,0],'gear',[x*.85,y*.85,52*scale],steel)
        add(f'planet_pin_{i+1}',cyl(2.8,17),[x,y,4*scale],'pin',[x*.85,y*.85,78*scale],gold)
    carrier=ring(40,7,4)
    for i in range(3):
        a=i*2*math.pi/3
        carrier=carrier-Pos(33*scale*math.cos(a),33*scale*math.sin(a),0)*cyl(3,8)
    add('carrier',carrier,[0,0,11*scale],'carrier',[0,0,100*scale],gold)
    add('output_shaft',cyl(6,27),[0,0,26*scale],'shaft',[0,0,125*scale],steel)
    add('input_shaft',cyl(3.8,26),[0,0,-10*scale],'shaft',[0,0,-90*scale],steel)
    add('front_cover',ring(53,7,5),[0,0,17*scale],'shell',[0,0,150*scale],blue)
    for i in range(4):
        a=math.pi/4+i*math.pi/2
        add(f'cover_bolt_{i+1}',cyl(2,7)+Pos(0,0,4*scale)*cyl(3.5,2),
            [47*scale*math.cos(a),47*scale*math.sin(a),21*scale], 'fastener',[0,0,175*scale],steel)
    export_step(Compound(children=shapes),folder/'assembly.step')
    data=dict(version=VERSION,id=key,units='mm',product='planetary_reducer',parameters=params,
              gear_teeth=dict(sun=18,planet=15,ring=48),ratio=1+48/18,
              caveat='Educational inferred construction; not manufacturing-certified. All internals inferred unless independently evidenced.',parts=parts)
    manifest.write_text(json.dumps(data,indent=2))
    return manifest


def build(root: Path, params=None):
    """Serialize CAD work as well as rendering on memory-constrained hosts."""
    import fcntl
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    with (root/'model.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return _build(root,params)
