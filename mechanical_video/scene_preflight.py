"""Evaluate the actual Blender pose before rendering; no render calls.

Geometric projection/occlusion/connection tests are not perceptual acceptance.
"""
import json
import math
from pathlib import Path
from .scene_fidelity import canonical, file_ref


def local_anchor(obj, ref):
    """Resolve an evaluated vertex or polygon center, copying before release."""
    key = 'face_index' if 'face_index' in ref else 'vertex_index'
    if key not in ref:
        return tuple(ref['point'])
    index = ref[key]
    if type(index) is not int or index < 0 or obj.type != 'MESH':
        raise ValueError('Invalid evaluated surface index')
    mesh = obj.to_mesh()
    try:
        elements = mesh.polygons if key == 'face_index' else mesh.vertices
        if index >= len(elements):
            raise ValueError('Evaluated surface index outside mesh')
        return tuple(elements[index].center if key == 'face_index' else elements[index].co)
    finally:
        obj.to_mesh_clear()


def validate_policy(policy):
    if policy.get('schema_version') != 1:
        raise ValueError('Expected scene preflight policy v1')
    if policy.get('pose_mode') not in ('renderer_callback', 'saved_animation'):
        raise ValueError('Declare actual pose evaluation mode')
    requirements = policy.get('requirements')
    if not isinstance(requirements, list) or not requirements:
        raise ValueError('Missing required mechanism windows')
    ids = []
    number = lambda x: type(x) in (int, float) and math.isfinite(x)
    def valid_anchor(ref):
        if not ref.get('object'):
            return False
        indices = [key for key in ('vertex_index', 'face_index') if key in ref]
        if indices:
            return len(indices) == 1 and type(ref[indices[0]]) is int and ref[indices[0]] >= 0
        point = ref.get('point')
        return isinstance(point, list) and len(point) == 3 and all(number(v) for v in point)
    for row in requirements:
        rid = row['id']
        interval = row['frames']
        if (not isinstance(rid, str) or not rid or rid in ids or not isinstance(interval, list)
                or len(interval) != 2 or not all(type(f) is int for f in interval)
                or not 0 <= interval[0] < interval[1]):
            raise ValueError('Invalid requirement ID/frame interval')
        ids.append(rid)
        if not row.get('targets') or not row.get('connections'):
            raise ValueError('Required visible targets and source connection anchors missing')
        if not isinstance(row.get('motion_object'), str) or not number(row.get('min_motion')) or row['min_motion'] <= 0:
            raise ValueError('Actual required state change missing')
        for target in row['targets']:
            if (not target.get('object') or not number(target.get('min_pixels')) or target['min_pixels'] <= 0
                    or not number(target.get('tolerance')) or target['tolerance'] <= 0):
                raise ValueError('Missing screen-size or surface tolerance')
            if not valid_anchor(target):
                raise ValueError('Target needs a local surface anchor')
        for connection in row['connections']:
            if not number(connection.get('max_distance')) or connection['max_distance'] < 0:
                raise ValueError('Invalid source connection tolerance')
            for endpoint in ('a', 'b'):
                anchor = connection[endpoint]
                if not valid_anchor(anchor):
                    raise ValueError('Invalid local connection anchor')
    return requirements


def audit(scene, policy_path, source, renderer, output, pose=None):
    """Call after scene construction, before FIRST render, using SAME pose callback.

    All integer frames of each required window are evaluated. No bpy render,
    save, provider or external process is called. Restore the original frame/pose.
    """
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from bpy_extras.object_utils import world_to_camera_view
    policy_path, output = Path(policy_path), Path(output)
    policy = json.loads(policy_path.read_text())
    requirements = validate_policy(policy)
    if policy['pose_mode'] != ('renderer_callback' if pose is not None else 'saved_animation'):
        raise ValueError('Pose callback does not match frozen policy')
    if output.exists():
        raise ValueError('Preflight output must be new')
    if not scene.camera or scene.camera.data.type not in ('PERSP', 'ORTHO'):
        raise ValueError('Missing/unsupported camera')
    if scene.render.use_border or any(o.is_instancer for o in scene.objects):
        raise ValueError('Render borders/instancers need a dedicated preflight')
    inputs = {k:file_ref(v) for k,v in dict(policy=policy_path, source=source, renderer=renderer).items()}
    old_frame = scene.frame_current
    failures, coverage, positions = [], {r['id']:[] for r in requirements}, {r['id']:[] for r in requirements}
    width = scene.render.resolution_x * scene.render.resolution_percentage / 100
    height = scene.render.resolution_y * scene.render.resolution_percentage / 100
    def fail(rid, frame, reason):
        failures.append(dict(requirement=rid, frame=frame, reason=reason))
    def visible(obj):
        # Conservative: collection visibility and object render flags matter.
        def walk(collection, hidden=False):
            hidden = hidden or collection.hide_render
            if not hidden and obj.name in collection.objects:
                return True
            return any(walk(child, hidden) for child in collection.children)
        return not obj.hide_render and walk(scene.collection)
    try:
        for frame in sorted({f for r in requirements for f in range(r['frames'][0], r['frames'][1]+1)}):
            scene.frame_set(frame)
            if pose is not None:
                pose(frame)
            bpy.context.view_layer.update()
            graph = bpy.context.evaluated_depsgraph_get()
            camera = scene.camera.evaluated_get(graph)
            # Use evaluated meshes so constraints/modifiers/custom poses count.
            evaluated, trees, bounds = {}, {}, {}
            for obj in scene.objects:
                evaluated[obj.name] = obj.evaluated_get(graph)
                if obj.type != 'MESH' or not visible(obj):
                    continue
                ev = evaluated[obj.name]
                mesh = ev.to_mesh()
                try:
                    vertices = [ev.matrix_world @ v.co for v in mesh.vertices]
                    if vertices and mesh.polygons:
                        trees[obj.name] = BVHTree.FromPolygons(vertices, [list(p.vertices) for p in mesh.polygons], all_triangles=False)
                        bounds[obj.name] = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
                finally:
                    ev.to_mesh_clear()
            for row in requirements:
                rid = row['id']
                if not row['frames'][0] <= frame <= row['frames'][1]:
                    continue
                coverage[rid].append(frame)
                try:
                    moving = evaluated[row['motion_object']]
                    positions[rid].append([list(moving.matrix_world @ Vector(c)) for c in moving.bound_box])
                    def anchor(ref):
                        obj = evaluated[ref['object']]
                        return obj.matrix_world @ Vector(local_anchor(obj, ref))
                    for connection in row['connections']:
                        if (anchor(connection['a']) - anchor(connection['b'])).length > connection['max_distance']:
                            fail(rid, frame, 'disconnected: '+connection['a']['object']+' -> '+connection['b']['object'])
                    for target in row['targets']:
                        name = target['object']
                        if name not in trees:
                            fail(rid, frame, 'missing/hidden/nonmesh target: '+name)
                            continue
                        points = [world_to_camera_view(scene, camera, v) for v in bounds[name]]
                        if any(not all(math.isfinite(c) for c in p) or p.z < camera.data.clip_start or p.z > camera.data.clip_end or not 0 <= p.x <= 1 or not 0 <= p.y <= 1 for p in points):
                            fail(rid, frame, 'outside camera/clipping: '+name)
                        if min((max(p.x for p in points)-min(p.x for p in points))*width,
                               (max(p.y for p in points)-min(p.y for p in points))*height) < target['min_pixels']:
                            fail(rid, frame, 'target too small: '+name)
                        point = anchor(target)
                        if camera.data.type == 'ORTHO':
                            forward = camera.matrix_world.to_quaternion() @ Vector((0,0,-1))
                            depth = world_to_camera_view(scene, camera, point).z
                            origin = point - forward * depth
                        else:
                            origin = camera.matrix_world.translation
                        direction = point - origin
                        distance = direction.length
                        if not math.isfinite(distance) or distance <= 0:
                            fail(rid, frame, 'invalid target ray: '+name)
                            continue
                        hits = []
                        for other, tree in trees.items():
                            hit, _, _, travel = tree.ray_cast(origin, direction.normalized(), distance + target['tolerance'])
                            if hit is not None:
                                hits.append((travel, other))
                        nearest = min(hits) if hits else None
                        if nearest is None or nearest[1] != name or abs(nearest[0]-distance) > target['tolerance']:
                            fail(rid, frame, 'surface anchor occluded/not on visible surface: '+name)
                except (KeyError, TypeError, AttributeError, ValueError):
                    fail(rid, frame, 'missing/invalid evaluated mechanism')
        for row in requirements:
            samples = positions[row['id']]
            displacement = max(((Vector(b)-Vector(a)).length for pose_points in samples for a,b in zip(samples[0], pose_points)), default=0) if samples else 0
            if displacement < row['min_motion']:
                fail(row['id'], None, 'required motion absent')
        if any(file_ref(ref['path']) != ref for ref in inputs.values()):
            failures.append(dict(reason='inputs changed during audit'))
    finally:
        scene.frame_set(old_frame)
        if pose is not None:
            pose(old_frame)
        bpy.context.view_layer.update()
    report = dict(schema_version=1, kind='evaluated-pre-render-scene', inputs=inputs,
                  implementation_sha256=file_ref(__file__)['sha256'], policy=policy,
                  pose_mode='renderer_callback' if pose is not None else 'saved_animation',
                  coverage=coverage, status='BLOCKED' if failures else 'PASS', failures=failures,
                  render_called=False, scope='All specified integer frames; geometric anchors/projection only, no perception, material appearance or exact solid collision verdict.')
    report['result_sha256'] = canonical(report)
    with output.open('x') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return report


def verify(report, assets, required_ids):
    """Revalidate inputs, implementation, frame coverage and requirement identity."""
    try:
        requirements = validate_policy(report['policy'])
        expected = {r['id']:list(range(r['frames'][0],r['frames'][1]+1)) for r in requirements}
        digests = {v['sha256'] for v in assets.values()}
        return (report['kind'] == 'evaluated-pre-render-scene' and report['schema_version'] == 1
                and set(report['inputs']) == {'source','renderer','policy'}
                and report['status'] == 'PASS' and report['failures'] == [] and report['render_called'] is False
                and report['implementation_sha256'] == file_ref(__file__)['sha256']
                and report['pose_mode'] == report['policy']['pose_mode']
                and set(expected) == set(required_ids) and report['coverage'] == expected
                and report['inputs']['policy']['sha256'] == canonical_file_policy(report)
                and all(file_ref(v['path']) == v and v['sha256'] in digests for v in report['inputs'].values())
                and report['result_sha256'] == canonical({k:v for k,v in report.items() if k!='result_sha256'}))
    except (KeyError, OSError, ValueError, TypeError, AttributeError):
        return False


def canonical_file_policy(report):
    # Also bind parsed policy contents; a hash alone is not parsed provenance.
    ref = report['inputs']['policy']
    return ref['sha256'] if json.loads(Path(ref['path']).read_text()) == report['policy'] else None
