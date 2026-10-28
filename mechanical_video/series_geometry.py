"""Explicit faceted fallback for defective vendor solids in the official STEP.

This is a documented display approximation, never a replacement manufacturing
model. Original analytic input remains archived unchanged.
"""
def repair_periodic_meshing(source):
    """Rebuild unmeshable rectangular periodic faces on their exact surfaces."""
    from build123d import Face, Compound, Solid, GeomType
    from OCP.BRep import BRep_Tool
    from OCP.BRepTools import BRepTools
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
    from OCP.BRepLib import BRepLib
    faces=[]; evidence=[]
    for index,face in enumerate(source.faces()):
        try:
            face.tessellate(.025,.2)
            faces.append(face.wrapped)
        except AttributeError:
            if face.geom_type not in (GeomType.CONE,GeomType.CYLINDER,GeomType.TORUS,GeomType.SPHERE): raise
            uv=BRepTools.UVBounds_s(face.wrapped)
            rebuilt=Face(BRepBuilderAPI_MakeFace(BRep_Tool.Surface_s(face.wrapped),*uv,1e-7).Face())
            if not rebuilt.is_valid or abs(rebuilt.area-face.area)>max(1e-6,face.area*1e-8):
                raise ValueError('Periodic-face reconstruction changed its trimmed area')
            if face.normal_at().dot(rebuilt.normal_at())<0: rebuilt.wrapped.Reverse()
            rebuilt.tessellate(.025,.2)
            faces.append(rebuilt.wrapped)
            evidence.append(dict(face=index,type=str(face.geom_type),uv_bounds=list(uv),
                original_area_mm2=face.area,rebuilt_area_mm2=rebuilt.area,
                method='Same analytic surface and original UV bounds, normals preserved'))
    if not evidence: return source,[]
    sewing=BRepBuilderAPI_Sewing(1e-6)
    for face in faces: sewing.Add(face)
    sewing.Perform()
    shell=Compound.cast(sewing.SewedShape()).wrapped
    result=BRepBuilderAPI_MakeSolid(shell).Solid()
    BRepLib.OrientClosedSolid_s(result)
    # Sewing changes shared edges; discard pre-sewing face triangulations so
    # one assembly-wide meshing pass uses matching boundary discretization.
    BRepTools.Clean_s(result)
    return Solid(result),evidence


def faceted_solid(source, tolerance=.025):
    import trimesh
    from build123d import Solid, Compound
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
    from OCP.BRepLib import BRepLib
    from OCP.gp import gp_Pnt
    from OCP.TopoDS import TopoDS
    meshing_repairs=[]
    try:
        vertices, triangles=source.tessellate(tolerance,.2)
    except AttributeError:
        source,meshing_repairs=repair_periodic_meshing(source)
        vertices,triangles=source.tessellate(tolerance,.2)
    mesh=trimesh.Trimesh(vertices=[list(v) for v in vertices],faces=triangles,process=True)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:
        raise ValueError('Source CAD tessellation is not a closed consistently oriented positive-volume mesh')
    # The volume integral of an invalid/self-intersecting analytic face is not
    # a reference volume (and can change on STEP round-trip). Instead require
    # convergence against a finer tessellation of the same source boundaries.
    fine_vertices,fine_triangles=source.tessellate(.01,.1)
    reference=trimesh.Trimesh(vertices=[list(v) for v in fine_vertices],faces=fine_triangles,process=True)
    if not reference.is_watertight or reference.volume<=0: raise ValueError('Fine source mesh is not a closed positive-volume reference')
    relative=abs(mesh.volume-reference.volume)/reference.volume
    if relative>.01: raise ValueError('Faceted component fails 1 percent volume convergence against finer source tessellation')
    sewing=BRepBuilderAPI_Sewing(1e-5)
    for triangle in mesh.triangles:
        polygon=BRepBuilderAPI_MakePolygon()
        for vertex in triangle: polygon.Add(gp_Pnt(*vertex))
        polygon.Close()
        sewing.Add(BRepBuilderAPI_MakeFace(polygon.Wire()).Face())
    sewing.Perform()
    shell=Compound.cast(sewing.SewedShape()).wrapped
    wrapped=BRepBuilderAPI_MakeSolid(shell).Solid()
    BRepLib.OrientClosedSolid_s(wrapped)
    result=Solid(wrapped)
    if not result.is_valid or result.volume<=0: raise ValueError('Faceted BRep failed independent solid validation')
    return result,dict(method='Source-CAD triangulation converted to a closed faceted BRep',
        tolerance_mm=tolerance,angular_tolerance_radians=.2,triangles=len(mesh.faces),
        original_volume_mm3=source.volume,faceted_volume_mm3=result.volume,
        fine_reference_volume_mm3=float(reference.volume),relative_volume_convergence=float(relative),
        exact_surface_meshing_repairs=meshing_repairs,
        invalid_source_volume_note='Original invalid BRep volume is diagnostic only, not a reliable manufacturing reference',
        classification='Approximate source-derived display geometry; not analytic manufacturing CAD')
