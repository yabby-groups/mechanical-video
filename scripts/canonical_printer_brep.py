"""Preserve source STEP/display assets; validate native BRep repair sidecars."""
import hashlib,json
from pathlib import Path
from build123d import import_step,import_brep,export_brep,Compound,Solid,Face,GeomType
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace,BRepBuilderAPI_Sewing,BRepBuilderAPI_MakeSolid,BRepBuilderAPI_MakePolygon
from OCP.BRepLib import BRepLib
from OCP.gp import gp_Pnt
root=Path(__file__).resolve().parents[1]/'series/3d-printer/master_assembly'
records=[]
for ident in ['m00078','m00079','m00784']:
    source=import_step(root/'parts'/f'{ident}.step'); faces=[]; evidence=[]
    if ident!='m00784':
        for i,face in enumerate(source.faces()):
            if not face.is_valid and face.geom_type==GeomType.PLANE:
                rebuilt=Face(BRepBuilderAPI_MakeFace(face.outer_wire().wrapped).Face())
                assert len(face.inner_wires())==0
                if face.normal_at().dot(rebuilt.normal_at())<0: rebuilt.wrapped.Reverse()
                evidence.append({'face':i,'method':'Rebuild planar face from original boundary wire','area_before':face.area,'area_after':rebuilt.area})
                assert abs(rebuilt.area-face.area)/face.area<1e-4
                face=rebuilt
            faces.append(face.wrapped)
    else:
        import trimesh
        mesh=trimesh.load(root/'parts'/f'{ident}.stl',force='mesh')
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
        for triangle in mesh.triangles:
            polygon=BRepBuilderAPI_MakePolygon()
            for vertex in triangle: polygon.Add(gp_Pnt(*vertex))
            polygon.Close(); faces.append(BRepBuilderAPI_MakeFace(polygon.Wire()).Face())
        evidence.append({'method':'Closed source-derived archived STL converted to faceted BRep','triangles':len(mesh.faces),'classification':'Approximate source-derived component; not manufacturing geometry'})
    sewing=BRepBuilderAPI_Sewing(1e-5)
    for face in faces:sewing.Add(face)
    sewing.Perform(); wrapped=BRepBuilderAPI_MakeSolid(Compound.cast(sewing.SewedShape()).wrapped).Solid();BRepLib.OrientClosedSolid_s(wrapped)
    result=Solid(wrapped);assert result.is_valid and result.volume>0,ident
    path=root/'canonical_parts'/f'{ident}.brep';export_brep(result,path)
    loaded=import_brep(path);valid=bool(loaded.solids()) and all(s.is_valid and s.volume>0 for s in loaded.solids());assert valid,ident
    records.append({'source':f'parts/{ident}.step','canonical':str(path.relative_to(root)),'format':'OpenCascade BRep','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'valid':valid,'volume_mm3':loaded.volume,'evidence':evidence})
    print('VALID_BREP',ident,loaded.volume,flush=True)
(root/'canonical-brep-validation.json').write_text(json.dumps({'passed':True,'replacements':records,'limitation':'STEP alternatives remain invalid on readback; use native BRep sidecars for these three occurrences. Source/display bytes unchanged.'},indent=2))
model=json.loads((root/'assembly.json').read_text())
replacement={r['source']:r for r in records}
for part in model['parts']:
    item=replacement.get(part['step'])
    part['cad']=item['canonical'] if item else part['step']
    part['cad_format']='brep' if item else 'step'
    if item: part['canonical_repair']=item['evidence']
model.update(version=model['version']+'-native-cad1',display_manifest='assembly.json',display_manifest_sha256=hashlib.sha256((root/'assembly.json').read_bytes()).hexdigest(),note='Source STEP remains fixed. Three native BRep sidecars avoid STEP serialization defects. Display geometry is unchanged.')
(root/'cad_assembly.json').write_text(json.dumps(model,ensure_ascii=False,indent=2))
