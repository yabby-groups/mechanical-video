"""Measure mesh edge stretch under the illustrative guide-tube deformation."""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guide_deform import displacement_weight

source, manifest, output = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=source)
parts = {p['id']: p for p in json.loads(Path(manifest).read_text())['parts']}
objects = [o for o in bpy.context.scene.objects if '4x3mm_PTFE_Guide_Tube' in o.get('source_path', '')]
if len(objects) != 1:
    raise RuntimeError(f'Expected one guide tube, got {len(objects)}')
obj = objects[0]
matrix = Matrix(parts[obj['part_id']]['matrix_mm'])
matrix.translation *= .001
source_vertices = [matrix @ v.co for v in obj.data.vertices]
low = min(v.y for v in source_vertices)
high = max(v.y for v in source_vertices)
edges = [(e.vertices[0], e.vertices[1]) for e in obj.data.edges]
lengths = [(source_vertices[a]-source_vertices[b]).length for a, b in edges]
result = {'scope': 'mesh-edge stretch, not centreline length or physical deformation', 'vertices': len(source_vertices), 'edges': len(edges), 'poses': []}
for displacement in (i*.002 for i in range(-20, 21)):
    vertices = [v.copy() for v in source_vertices]
    for v in vertices:
        v.x += displacement * displacement_weight(v.y, low, high)
    ratios = [((vertices[a]-vertices[b]).length / original)-1
              for (a,b), original in zip(edges, lengths) if original > 1e-9]
    result['poses'].append({'displacement_mm': displacement*1000,
                            'max_abs_edge_strain': max(abs(r) for r in ratios),
                            'mean_abs_edge_strain': sum(abs(r) for r in ratios)/len(ratios)})
Path(output).write_text(json.dumps(result, indent=2))
