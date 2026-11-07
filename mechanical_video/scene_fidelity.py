"""Rest-state scene preservation, not motion, collision or perceptual acceptance.

Call capture_scene in the renderer after dependency evaluation, before applying
episode motion. No bpy import at module load: comparisons work outside Blender.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def file_ref(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        return {'path': str(path), 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def node_signature(owner):
    """Record shader topology, defaults and image content, not just material names."""
    tree = owner if hasattr(owner, 'nodes') else getattr(owner, 'node_tree', None)
    nodes = []
    if tree:
        for node in tree.nodes:
            values = []
            for socket in list(node.inputs) + list(node.outputs):
                value = getattr(socket, 'default_value', None)
                if isinstance(value, (str, int, float, bool)) or value is None:
                    values.append(value)
                else:
                    try:
                        values.append(list(value))
                    except TypeError:
                        values.append(getattr(value, 'name', None))
            image = getattr(node, 'image', None)
            # Hash evaluated pixels: also covers packed/generated images.
            image_hash = None
            if image:
                h = hashlib.sha256()
                for pixel in image.pixels:
                    h.update(struct.pack('<f', pixel))
                image_hash = h.hexdigest()
            nested = getattr(node, 'node_tree', None)
            attributes = {}
            for prop in node.bl_rna.properties:
                if prop.identifier in ('rna_type', 'name', 'label', 'location', 'width', 'height', 'select', 'dimensions'):
                    continue
                if prop.type in ('BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'):
                    value = getattr(node, prop.identifier)
                    attributes[prop.identifier] = (sorted(value) if isinstance(value, set) else
                                                   list(value) if getattr(prop, 'is_array', False) else value)
            ramp = getattr(node, 'color_ramp', None)
            if ramp:
                attributes['color_ramp'] = {'interpolation': ramp.interpolation,
                                            'elements': [[e.position, list(e.color)] for e in ramp.elements]}
            nodes.append({'name': node.name, 'type': node.bl_idname, 'inputs': values,
                          'attributes': attributes, 'image': image_hash,
                          'group': node_signature(nested) if nested else None})
        links = sorted((l.from_node.name, l.from_socket.identifier,
                        l.to_node.name, l.to_socket.identifier) for l in tree.links)
    else:
        links = []
    return canonical({'nodes': nodes, 'links': links,
                      'color': list(getattr(owner, 'diffuse_color', getattr(owner, 'color', []))),
                      'surface': [getattr(owner, k, None) for k in ('roughness', 'metallic', 'surface_render_method')],
                      'use_nodes': getattr(owner, 'use_nodes', False)})


def capture_scene(scene, source, renderer, cad_objects=()):
    """Capture the actual evaluated rest state in the current Blender process.

    Caller sets the intended baseline/rest frame first. Does not open, save or
    render a blend. Includes support meshes without requiring part_id tags.
    """
    import bpy
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    objects = {}
    for obj in scene.objects:
        evaluated = obj.evaluated_get(graph)
        row = {'type': obj.type, 'matrix_world': [list(r) for r in evaluated.matrix_world],
               'visibility': {'hide_render': obj.hide_render,
                              'hide_viewport': obj.hide_viewport,
                              'visible': obj.visible_get()},
               'appearance_sha256': canonical([node_signature(s.material) if s.material else None
                                               for s in obj.material_slots])}
        if hasattr(obj, 'color'):
            row['object_color'] = list(obj.color)
        if obj.type == 'MESH':
            mesh = evaluated.to_mesh()
            try:
                h = hashlib.sha256()
                for vertex in mesh.vertices:
                    h.update(struct.pack('<3d', *vertex.co))
                for polygon in mesh.polygons:
                    h.update(struct.pack('<I', len(polygon.vertices)))
                    h.update(struct.pack('<' + 'I' * len(polygon.vertices), *polygon.vertices))
                    h.update(struct.pack('<I?', polygon.material_index, polygon.use_smooth))
                row['geometry_sha256'] = h.hexdigest()
                points = [evaluated.matrix_world @ v.co for v in mesh.vertices]
                row['bounds_world'] = [[min(p[i] for p in points) for i in range(3)],
                                       [max(p[i] for p in points) for i in range(3)]] if points else []
                if obj.name in cad_objects:
                    # Opt-in local mechanism evidence; avoid duplicating whole
                    # printer meshes in ordinary scene inventories.
                    mesh.calc_loop_triangles()
                    row['cad_geometry'] = {
                        'vertices_world': [list(p) for p in points],
                        'triangles': [list(t.vertices) for t in mesh.loop_triangles]}
            finally:
                evaluated.to_mesh_clear()
        data = evaluated.data
        if obj.type in ('CAMERA', 'LIGHT', 'FONT', 'CURVE'):
            attrs = ('type', 'lens', 'ortho_scale', 'clip_start', 'clip_end', 'energy',
                     'color', 'size', 'body', 'align_x', 'align_y', 'bevel_depth', 'resolution_u')
            details = {}
            for key in attrs:
                if hasattr(data, key):
                    value = getattr(data, key)
                    details[key] = value if isinstance(value, (str, int, float, bool)) else list(value)
            if obj.type == 'CURVE':
                details['splines'] = [{'type': s.type, 'cyclic': s.use_cyclic_u,
                                       'points': [list(p.co) for p in s.points],
                                       'bezier': [[list(p.co), list(p.handle_left), list(p.handle_right)]
                                                  for p in s.bezier_points]} for s in data.splines]
            row['data_sha256'] = canonical(details)
        objects[obj.name] = row
    render = scene.render
    def collection_state(collection):
        return {'name': collection.name, 'hide_render': collection.hide_render,
                'hide_viewport': collection.hide_viewport,
                'objects': sorted(o.name for o in collection.objects),
                'children': [collection_state(c) for c in sorted(collection.children, key=lambda c: c.name)]}
    missing = set(cad_objects) - {name for name, row in objects.items() if row['type'] == 'MESH'}
    if missing:
        raise ValueError('Missing CAD mesh objects: ' + ', '.join(sorted(missing)))
    return {'schema_version': 1, 'capture': 'evaluated-rest-state',
            **({'cad_frame': {'presentation_shift_m': list(scene.get('presentation_shift_m'))
                             if scene.get('presentation_shift_m') is not None else None}}
               if cad_objects and hasattr(scene, 'get') else {}),
            'source': file_ref(source), 'renderer': file_ref(renderer),
            'implementation_sha256': file_ref(__file__)['sha256'],
            'unit_scale': scene.unit_settings.scale_length,
            'scene': {'camera': scene.camera.name if scene.camera else None,
                      'world': node_signature(scene.world) if scene.world else None,
                      'engine': render.engine, 'resolution': [render.resolution_x, render.resolution_y,
                                                             render.resolution_percentage],
                      'fps': [render.fps, render.fps_base],
                      'color_management': [scene.view_settings.view_transform,
                                           scene.view_settings.look, scene.view_settings.exposure,
                                           scene.view_settings.gamma],
                      'collections': collection_state(scene.collection)},
            'objects': objects}


def write_inventory(path, scene, source, renderer, cad_objects=()):
    """Exclusive output: never overwrite a baseline or an archived inventory."""
    inventory = capture_scene(scene, source, renderer, cad_objects=cad_objects)
    with Path(path).open('x') as stream:
        json.dump(inventory, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return inventory


def _numeric_equal(a, b, tolerance):
    if not isinstance(a, list) or not isinstance(b, list) or len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if isinstance(x, list) or isinstance(y, list):
            if not _numeric_equal(x, y, tolerance):
                return False
        elif (not isinstance(x, (int, float)) or isinstance(x, bool)
              or not isinstance(y, (int, float)) or isinstance(y, bool)
              or not math.isfinite(x) or not math.isfinite(y) or abs(x - y) > tolerance):
            return False
    return True


def compare(baseline, current, policy=None):
    """Explicit, hashed before/after exceptions; no broad moving-object whitelist."""
    policy = policy if policy is not None else {'schema_version': 1, 'changes': []}
    for inventory in (baseline, current):
        if (inventory.get('schema_version') != 1 or inventory.get('capture') != 'evaluated-rest-state'
                or not isinstance(inventory.get('objects'), dict) or not inventory['objects']
                or not isinstance(inventory.get('scene'), dict) or not inventory['scene']):
            raise ValueError('Invalid scene inventory')
        canonical(inventory)  # Reject NaN/Infinity anywhere, including matrices.
        for row in inventory['objects'].values():
            if not isinstance(row, dict) or not all(k in row for k in ('type', 'matrix_world', 'visibility', 'appearance_sha256')):
                raise ValueError('Incomplete object inventory')
            if row['type'] == 'MESH' and not all(k in row for k in ('geometry_sha256', 'bounds_world')):
                raise ValueError('Incomplete mesh inventory')
        if not isinstance(inventory.get('implementation_sha256'), str):
            raise ValueError('Missing capture implementation')
    if policy.get('schema_version') != 1 or not isinstance(policy.get('changes'), list):
        raise ValueError('Invalid scene change policy')
    exceptions = {}
    for change in policy['changes']:
        key = (change['object'], change['field'])
        if key in exceptions or not isinstance(change.get('reason'), str) or not change['reason'].strip():
            raise ValueError('Duplicate or unexplained scene exception')
        exceptions[key] = change
    scale = baseline.get('unit_scale')
    if not isinstance(scale, (int, float)) or isinstance(scale, bool) or not math.isfinite(scale) or scale <= 0:
        raise ValueError('Invalid scene unit scale')
    # 0.001 mm translation/bounds roundoff; linear matrix entries use 1e-7.
    tolerance = .000001 / scale
    issues, used = [], set()

    def check(name, field, before, after, equal=None):
        if equal is None:
            equal = before == after
        if equal:
            return
        key = (name, field)
        exception = exceptions.get(key)
        if (exception and exception.get('before_sha256') == canonical(before)
                and exception.get('after_sha256') == canonical(after)):
            used.add(key)
        else:
            issues.append({'object': name, 'field': field, 'before_sha256': canonical(before),
                           'after_sha256': canonical(after)})
    check('$inventory', 'unit_scale', scale, current.get('unit_scale'))
    check('$inventory', 'implementation_sha256', baseline['implementation_sha256'], current['implementation_sha256'])
    check('$inventory', 'source_sha256', baseline.get('source', {}).get('sha256'), current.get('source', {}).get('sha256'))
    for key in sorted(set(baseline['scene']) | set(current['scene'])):
        check('$scene', key, baseline['scene'].get(key), current['scene'].get(key))
    for name in sorted(set(baseline['objects']) | set(current['objects'])):
        before, after = baseline['objects'].get(name), current['objects'].get(name)
        if before is None or after is None:
            check(name, '$object', before, after)
            continue
        for field in sorted(set(before) | set(after)):
            a, b = before.get(field), after.get(field)
            equal = None
            if field == 'bounds_world':
                equal = _numeric_equal(a, b, tolerance)
            elif field == 'matrix_world':
                equal = (_numeric_equal(a, b, tolerance) and len(a) == len(b) == 4
                         and all(len(r) == 4 for r in a + b)
                         and all(abs(a[i][j] - b[i][j]) <= 1e-7
                                 for i in range(4) for j in range(4) if j != 3))
            check(name, field, a, b, equal)
    unused = sorted(set(exceptions) - used)
    return {'schema_version': 1, 'status': 'BLOCKED' if issues or unused else 'PASS',
            'baseline_sha256': canonical(baseline), 'current_sha256': canonical(current),
            'policy_sha256': canonical(policy), 'translation_tolerance_mm': .001,
            'issues': issues, 'unused_exceptions': [list(k) for k in unused],
            'scope': 'Evaluated rest-state preservation only; independent A/B, motion and media QA required.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('current', type=Path)
    parser.add_argument('--policy', type=Path)
    args = parser.parse_args(argv)
    try:
        result = compare(json.loads(args.baseline.read_text()), json.loads(args.current.read_text()),
                         json.loads(args.policy.read_text()) if args.policy else None)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print(json.dumps({'status': 'INPUT_ERROR', 'reasons': ['Invalid inventory or policy']}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
