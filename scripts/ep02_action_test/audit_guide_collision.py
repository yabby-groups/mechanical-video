"""Sample tube mesh surface crossings with nearby stationary source objects."""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guide_mesh_path import bind, deform

source, manifest, centres_file, output = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=source)
parts = {p['id']: p for p in json.loads(Path(manifest).read_text())['parts']}
centres = np.asarray(json.loads(Path(centres_file).read_text())['centres_m'])
tube = [o for o in bpy.context.scene.objects if '4x3mm_PTFE_Guide_Tube' in o.get('source_path', '')]
if len(tube) != 1:
    raise RuntimeError('Expected one guide tube')
obj = tube[0]
matrix = Matrix(parts[obj['part_id']]['matrix_mm']); matrix.translation *= .001
vertices = np.array([tuple(matrix @ v.co) for v in obj.data.vertices])
binding = bind(vertices, centres)
faces = [tuple(p.vertices) for p in obj.data.polygons]
lo, hi = vertices.min(axis=0) - .02, vertices.max(axis=0) + .02
candidates = []
for other in bpy.context.scene.objects:
    path = other.get('source_path', '')
    if other.type != 'MESH' or other.get('part_id') not in parts or other == obj or '/X_Axis/X_Carriage/' in path or '/X_Cable_Chain/' in path:
        continue
    m = Matrix(parts[other['part_id']]['matrix_mm']); m.translation *= .001
    bounds = np.array([tuple(m @ Vector(c)) for c in other.bound_box])
    low, high = bounds.min(axis=0), bounds.max(axis=0)
    if np.any(high < lo) or np.any(low > hi):
        continue
    polygons = [tuple(p.vertices) for p in other.data.polygons]
    if polygons:
        candidates.append((path, low, high, BVHTree.FromPolygons([m @ v.co for v in other.data.vertices], polygons)))
result = {'scope': 'discrete surface crossings with stationary objects; excludes carriage, chain, solid containment and continuous sweep',
          'candidates': len(candidates), 'poses': []}
for displacement in np.linspace(-.015, 0, 16):
    transformed, _ = deform(binding, centres, float(displacement))
    low, high = transformed.min(axis=0), transformed.max(axis=0)
    tree = BVHTree.FromPolygons([Vector(v) for v in transformed], faces)
    hits = []
    for path, a, b, fixed in candidates:
        if np.any(b < low) or np.any(a > high):
            continue
        overlaps = tree.overlap(fixed)
        if overlaps:
            hits.append({'path': path, 'surface_pairs': len(overlaps)})
    result['poses'].append({'displacement_mm': float(displacement * 1000), 'hits': hits})
Path(output).write_text(json.dumps(result, indent=2))
print('stationary candidates:', len(candidates), 'sampled poses:', len(result['poses']))
