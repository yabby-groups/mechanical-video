"""Sample tube surface crossings with the moving carriage and drag chain."""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_path
from guide_mesh_path import bind, deform

source, manifest, centres_file, output = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=source)
parts = {p['id']: p for p in json.loads(Path(manifest).read_text())['parts']}
centres = np.asarray(json.loads(Path(centres_file).read_text())['centres_m'])
objects = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('part_id') in parts]
tube = [o for o in objects if '4x3mm_PTFE_Guide_Tube' in o.get('source_path', '')]
if len(tube) != 1:
    raise RuntimeError('Expected one guide tube')
obj = tube[0]
matrix = Matrix(parts[obj['part_id']]['matrix_mm']); matrix.translation *= .001
vertices = np.array([tuple(matrix @ v.co) for v in obj.data.vertices])
binding = bind(vertices, centres)
faces = [tuple(p.vertices) for p in obj.data.polygons]
lo, hi = vertices.min(axis=0) - .02, vertices.max(axis=0) + .02
args = (.245, .1224, .035, .0949, .1411)
total = chain_path.length(*args)
samples = [total * i / 5000 for i in range(5001)]
reference = [chain_path.point(s, *args) for s in samples]
moving = []
for other in objects:
    path = other.get('source_path', '')
    is_head = ('/X_Carriage/' in path or '/CW2_Assembly/' in path or '/P6_Assembly' in path
               or parts[other['part_id']].get('group') == 'toolhead')
    is_chain = '/X_Axis/X_Cable_Chain/' in path
    if not (is_head or is_chain):
        continue
    m = Matrix(parts[other['part_id']]['matrix_mm']); m.translation *= .001
    corners = np.array([tuple(m @ Vector(c)) for c in other.bound_box])
    if np.any(corners.max(axis=0) < lo) or np.any(corners.min(axis=0) > hi):
        continue
    polygons = [tuple(p.vertices) for p in other.data.polygons]
    if not polygons:
        continue
    pivot = sum((m @ Vector(c) for c in other.bound_box), Vector()) / 8
    if is_chain:
        j = min(range(len(samples)), key=lambda i: (reference[i][0][0] - pivot.x)**2 + (reference[i][0][1] - pivot.z)**2)
        chain_info = samples[j], reference[j][1]
    else:
        chain_info = None
    moving.append((path, other, m, pivot, polygons, chain_info))

result = {'scope': 'discrete tube surface crossings with carriage and chain; no solid containment or continuous sweep',
          'candidates': len(moving), 'poses': []}
for displacement in np.linspace(-.015, 0, 16):
    transformed, _ = deform(binding, centres, float(displacement))
    low, high = transformed.min(axis=0), transformed.max(axis=0)
    tree = BVHTree.FromPolygons([Vector(v) for v in transformed], faces)
    hits = []
    for path, other, m, pivot, polygons, info in moving:
        if info:
            s, old_tangent = info
            (x, z), tangent = chain_path.point(s, *args, float(displacement))
            (x0, z0), _ = chain_path.point(s, *args)
            angle = -(math.atan2(tangent[1], tangent[0]) - math.atan2(old_tangent[1], old_tangent[0]))
            transform = Matrix.Translation(pivot + Vector((x-x0, 0, z-z0))) @ Matrix.Rotation(angle, 4, 'Y') @ Matrix.Translation(-pivot) @ m
        else:
            transform = Matrix.Translation(Vector((displacement, 0, 0))) @ m
        corners = np.array([tuple(transform @ Vector(c)) for c in other.bound_box])
        if np.any(corners.max(axis=0) < low) or np.any(corners.min(axis=0) > high):
            continue
        other_tree = BVHTree.FromPolygons([transform @ v.co for v in other.data.vertices], polygons)
        overlaps = tree.overlap(other_tree)
        if overlaps:
            hits.append({'path': path, 'surface_pairs': len(overlaps)})
    result['poses'].append({'displacement_mm': float(displacement * 1000), 'hits': hits})
Path(output).write_text(json.dumps(result, indent=2))
print('moving candidates:', len(moving), 'sampled poses:', len(result['poses']))
