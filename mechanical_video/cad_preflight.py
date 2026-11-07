"""Read-only OCCT diagnostics in mm. Sampled geometry, never dynamics certification."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path

from .technical_evidence import canonical, digest
from .scene_fidelity import _numeric_equal


def matrix_location(matrix):
    from build123d import Location
    from OCP.gp import gp_Trsf
    from OCP.TopLoc import TopLoc_Location
    if (not isinstance(matrix, list) or len(matrix) != 4
            or any(not isinstance(r, list) or len(r) != 4 for r in matrix)
            or any(type(x) not in (int, float) or not math.isfinite(x) for r in matrix for x in r)
            or matrix[3] != [0, 0, 0, 1]):
        raise ValueError('Expected finite rigid 4x4 matrix in mm')
    # Reject scale/shear/reflection instead of silently normalizing through gp_Trsf.
    for i in range(3):
        for j in range(3):
            if abs(sum(matrix[k][i] * matrix[k][j] for k in range(3)) - (i == j)) > 1e-7:
                raise ValueError('Non-rigid placement')
    a, b, c = matrix[:3]
    det = a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
    if det < 0:
        raise ValueError('Reflected placement')
    tr = gp_Trsf()
    tr.SetValues(*(x for r in matrix[:3] for x in r))
    return Location(TopLoc_Location(tr))


def bounds(shape):
    box = shape.bounding_box()
    return [list(box.min), list(box.max)]


def geometry(shape):
    from OCP.BRepCheck import BRepCheck_Analyzer
    solids = shape.solids()
    return {'valid': bool(solids) and BRepCheck_Analyzer(shape.wrapped).IsValid()
            and all(s.volume > 0 for s in solids),
            'solid_volumes_mm3': [s.volume for s in solids], 'bounds_mm': bounds(shape)}


def pair_measure(a, b):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from build123d import Compound
    distance = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    distance.Perform()
    if not distance.IsDone() or not distance.NbSolution():
        raise ValueError('OCCT distance failed')
    common = BRepAlgoAPI_Common(a.wrapped, b.wrapped)
    common.Build()
    if not common.IsDone():
        raise ValueError('OCCT common failed')
    overlap = Compound(common.Shape())
    volume = sum(abs(s.volume) for s in overlap.solids())
    point = lambda p: [p.X(), p.Y(), p.Z()]
    return {'distance_mm': distance.Value(), 'intersection_mm3': volume,
            'witness_mm': [point(distance.PointOnShape1(1)), point(distance.PointOnShape2(1))],
            'intersection_bounds_mm': bounds(overlap) if volume > 0 else None}


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('Expected nonnegative finite tolerance')
    return value


def mesh_measure(shape, mesh, scale, tolerance, volume_relative_tolerance=.02):
    """All-triangle volume and bounded vertex/surface sampling, not mesh equality."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Pnt
    from build123d import Compound
    scale, tolerance = number(scale), number(tolerance)
    volume_relative_tolerance = number(volume_relative_tolerance)
    if scale == 0:
        raise ValueError('Mesh scale must be positive')
    # Distance to a solid is zero for interior points. Use its actual boundary
    # faces so inward dents are not mistaken for surface agreement.
    surface = Compound(children=list(shape.faces()))
    vertices = [[x * scale for x in v] for v in mesh['vertices_world']]
    if not vertices or any(len(v) != 3 or any(not math.isfinite(x) for x in v) for v in vertices):
        raise ValueError('Invalid mesh vertices')
    triangles = mesh['triangles']
    edges, volume = {}, 0
    for tri in triangles:
        if len(tri) != 3 or any(type(i) is not int or not 0 <= i < len(vertices) for i in tri):
            raise ValueError('Invalid mesh triangle')
        a,b,c = [vertices[i] for i in tri]
        # Shift origin to reduce cancellation for far-from-origin assemblies.
        origin = vertices[0]
        a,b,c = [[v[i]-origin[i] for i in range(3)] for v in (a,b,c)]
        volume += (a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
        for i,j in zip(tri, tri[1:]+tri[:1]):
            key = tuple(sorted((i,j)))
            count, orientation = edges.get(key, (0,0))
            edges[key] = (count+1, orientation+(1 if i < j else -1))
    watertight = bool(triangles) and all(n == 2 and winding == 0 for n,winding in edges.values())
    indices = sorted({round(i*(len(vertices)-1)/min(255,len(vertices)-1)) for i in range(min(256,len(vertices)))}) if len(vertices)>1 else [0]
    worst, point = 0, vertices[0]
    for i in indices:
        p = vertices[i]
        distance = BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(*p)).Vertex(), surface.wrapped)
        distance.Perform()
        if not distance.IsDone():
            raise ValueError('Mesh surface distance failed')
        if distance.Value() > worst:
            worst, point = distance.Value(), p
    cad_volume = sum(s.volume for s in shape.solids())
    relative = abs(abs(volume)-cad_volume)/cad_volume if cad_volume > 0 else float('inf')
    return {'status': 'PASS' if watertight and worst <= tolerance and relative <= volume_relative_tolerance else 'BLOCKED',
            'watertight_oriented': watertight, 'mesh_volume_mm3': abs(volume),
            'volume_relative_error': relative, 'max_sample_surface_distance_mm': worst,
            'coordinate_mm': point, 'sampled_vertices': len(indices), 'total_vertices': len(vertices)}


def classify(measure, policy):
    """No implicit contact/press-fit whitelist; allowances are pair-specific."""
    mode = policy.get('mode', 'clearance')
    if mode not in ('clearance', 'contact', 'press_fit'):
        raise ValueError('Unknown pair intent')
    if mode != 'clearance' and not str(policy.get('reason', '')).strip():
        raise ValueError('Contact/press fit requires design evidence/reason')
    epsilon = number(policy.get('volume_tolerance_mm3', 1e-7))
    # Numerical tolerance is bounded; engineering allowances belong to press_fit.
    if epsilon > 1e-6:
        raise ValueError('Use explicit press_fit allowance, not inflated numerical tolerance')
    minimum = number(policy.get('min_gap_mm', 0))
    maximum = number(policy['max_gap_mm']) if 'max_gap_mm' in policy else None
    if maximum is not None and maximum < minimum:
        raise ValueError('Invalid gap interval')
    allowance = number(policy['max_intersection_mm3']) if mode == 'press_fit' else epsilon
    if mode == 'press_fit' and allowance <= 0:
        raise ValueError('Press fit requires positive bounded allowance')
    if measure['intersection_mm3'] > allowance:
        return 'P1', 'unexpected_interference', '核对源齿形、实例变换与装配轴距；不要用镜头遮盖交集'
    if measure['distance_mm'] < minimum:
        return 'P1', 'insufficient_clearance', '检查垫片、轴向偏移与拆解方向，恢复要求的最小间隙'
    if maximum is not None and measure['distance_mm'] > maximum:
        return 'P1', 'unexpected_gap', '核对装配基准、单位及漏装零件'
    if mode == 'contact' and measure['distance_mm'] > number(policy.get('contact_tolerance_mm', .001)):
        return 'P1', 'missing_contact', '恢复设计接触位置，核对实例坐标'
    return None


def parse_step(path):
    """Preserve hierarchy and repeated occurrences; never deduplicate by TShape hash."""
    from build123d import import_step, Location
    root = import_step(path)
    nodes, parts = [], {}
    def visit(shape, parent_world, parent):
        ident = f'n{len(nodes):05}'
        world = parent_world * shape.location
        tr = world.wrapped.Transformation()
        matrix = [[tr.Value(i, j) for j in range(1, 5)] for i in range(1, 4)] + [[0, 0, 0, 1]]
        nodes.append({'id': ident, 'name': shape.label, 'parent': parent, 'matrix_mm': matrix})
        if shape.children:
            for child in shape.children:
                visit(child, world, ident)
        else:
            local = type(shape)(shape.wrapped.Located(Location().wrapped))
            parts[ident] = (local, matrix)
    visit(root, Location(), None)
    return nodes, parts


def inspect_manifest(manifest_path):
    """Explicit part/pair/state inventory; unlisted neighbors are outside coverage."""
    import OCP
    from build123d import import_step
    path = Path(manifest_path).resolve()
    spec = json.loads(path.read_text())
    if spec.get('schema_version') != 1 or spec.get('units') != 'mm':
        raise ValueError('Expected cad preflight manifest v1, units mm')
    refs = {'manifest': {'path': str(path), 'sha256': digest(path)}}
    def source(name, relative):
        p = (path.parent / relative).resolve()
        refs[name] = {'path': str(p), 'sha256': digest(p)}
        return p
    shapes, facts, issues, nodes = {}, {}, [], []
    def issue(ids, code, repair, severity='P1', **extra):
        issues.append(dict(parts=ids, code=code, severity=severity, repair=repair, **extra))
    entries = spec.get('parts', [])
    if 'assembly_step' in spec:
        nodes, parsed = parse_step(source('assembly_step', spec['assembly_step']))
        if entries:
            raise ValueError('Use assembly_step or independent parts, not both')
        entries = [{'id': ident, 'matrix_mm': matrix} for ident, (_, matrix) in parsed.items()]
    else:
        parsed = {}
    if not entries:
        raise ValueError('Empty CAD inventory')
    for row in entries:
        ident = row['id']
        if ident in shapes:
            raise ValueError('Duplicate occurrence ID')
        raw = parsed[ident][0] if parsed else import_step(source(ident, row['step']))
        # Explicit solid selection is recorded, e.g. motor output without casing.
        if row.get('solid_selection') == 'smallest':
            raw = min(raw.solids(), key=lambda s: s.volume)
        elif row.get('solid_selection') is not None:
            raise ValueError('Unsupported solid selection')
        world = raw.moved(matrix_location(row['matrix_mm']))
        shapes[ident] = world
        facts[ident] = dict(geometry(world), matrix_mm=row['matrix_mm'], selection=row.get('solid_selection'))
        if not facts[ident]['valid']:
            issue([ident], 'invalid_solid', '独立 STEP 重导出并检查缝合、闭合与正体积', coordinate_mm=facts[ident]['bounds_mm'])
        if 'expected_matrix_mm' in row:
            matrix_location(row['expected_matrix_mm'])
            if not _numeric_equal(row['matrix_mm'], row['expected_matrix_mm'], 1e-7):
                issue([ident], 'placement_mismatch', '核对父子矩阵累积顺序与局部/世界坐标', coordinate_mm=facts[ident]['bounds_mm'])
    pairs = spec.get('pairs', [])
    if not pairs:
        raise ValueError('Explicit neighbor pair coverage required')
    measurements = []
    for pair in pairs:
        first, second = pair['parts']
        if first == second:
            raise ValueError('Self pair')
        a, b = shapes[first], shapes[second]
        # Samples apply world-space delta transforms to the rest-state shape.
        samples = pair.get('samples', [{'time': 0, 'transforms': {}}])
        if not samples:
            raise ValueError('Empty path samples')
        times = [s['time'] for s in samples]
        if any(type(t) not in (int, float) or not math.isfinite(t) or t < 0 for t in times) or any(x >= y for x, y in zip(times, times[1:])):
            raise ValueError('Sample times must increase')
        if 'samples' in pair and len(samples) < 2:
            raise ValueError('Path requires at least two samples')
        for sample in samples:
            transforms = sample.get('transforms', {})
            if set(transforms) - {first, second}:
                raise ValueError('Unknown moving part')
            moved = lambda ident, shape: shape.moved(matrix_location(transforms[ident])) if ident in transforms else shape
            measure = pair_measure(moved(first, a), moved(second, b))
            measurements.append(dict(parts=[first, second], time=sample['time'], **measure))
            failure = classify(measure, pair)
            if failure:
                severity, code, repair = failure
                issue([first, second], code, repair, severity, time=sample['time'], coordinate_mm=measure['witness_mm'], **measure)
    mesh_checks = {}
    if spec.get('scene_inventory'):
        inventory = json.loads(source('scene_inventory', spec['scene_inventory']).read_text())
        scale = number(spec['blender_to_mm'])
        tolerance = number(spec.get('mesh_tolerance_mm', .3))
        mapping = spec.get('scene_objects', {})
        if scale == 0 or set(mapping) != set(shapes):
            raise ValueError('Complete CAD to Blender mapping and positive scale required')
        for ident, name in mapping.items():
            obj = inventory['objects'].get(name)
            if obj is None or obj.get('type') != 'MESH':
                issue([ident], 'missing_blender_mesh', '恢复实例对象映射')
                continue
            scene_shape = shapes[ident]
            if 'scene_from_cad_mm' in spec:
                scene_shape = scene_shape.moved(matrix_location(spec['scene_from_cad_mm']))
            mesh_bounds = [[x * scale for x in r] for r in obj['bounds_world']]
            if not _numeric_equal(bounds(scene_shape), mesh_bounds, tolerance):
                issue([ident], 'mesh_bounds_mismatch', '检查 STL 单位、实例矩阵与导出对象；边界一致不代表拓扑一致', coordinate_mm=mesh_bounds)
            if spec.get('require_mesh_geometry', False):
                if 'cad_geometry' not in obj:
                    issue([ident], 'missing_mesh_geometry', '用 scene_fidelity.capture_scene 的 cad_objects 采集实际 evaluated mesh')
                else:
                    result = mesh_measure(scene_shape, obj['cad_geometry'], scale, tolerance,
                                          number(spec.get('mesh_volume_relative_tolerance', .02)))
                    mesh_checks[ident] = result
                    if result['status'] != 'PASS':
                        issue([ident], 'mesh_geometry_mismatch', '检查三角化、孔洞、修改器和实例映射；重新导出对应源零件', **result)
    report = {'schema_version': 1, 'status': 'BLOCKED' if issues else 'PASS', 'inputs': refs,
              'implementation_sha256': digest(__file__), 'kernel': OCP.__version__,
              'build123d': importlib.metadata.version('build123d'), 'hierarchy': nodes,
              'facts': facts, 'measurements': measurements, 'mesh_checks': mesh_checks, 'issues': issues,
              'coverage': {'pairs': [p['parts'] for p in pairs], 'blender_bounds': bool(spec.get('scene_inventory')),
                           'mesh_geometry_parts': sorted(mesh_checks)},
              'scope': 'Explicit pairs and sampled states only; optional mesh bounds, oriented volume and sampled surface distances; no continuous collision, exact mesh equivalence, dynamics or perceptual verdict.'}
    report['result_sha256'] = canonical(report)
    return report


def verify_report(report):
    """Reject stale sources/policy/implementation and altered report payloads."""
    import OCP
    payload = {k: v for k, v in report.items() if k != 'result_sha256'}
    return (report.get('status') == 'PASS' and not report.get('issues')
            and bool(report.get('facts')) and bool(report.get('measurements'))
            and report.get('result_sha256') == canonical(payload)
            and report.get('implementation_sha256') == digest(__file__)
            and report.get('kernel') == OCP.__version__
            and report.get('build123d') == importlib.metadata.version('build123d')
            and bool(report.get('inputs'))
            and all(digest(ref['path']) == ref['sha256'] for ref in report['inputs'].values()))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = inspect_manifest(args.manifest)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        report = {'status': 'INPUT_ERROR', 'reason': str(error)}
    with args.output.open('x') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'status': report['status'], 'output': str(args.output)}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
