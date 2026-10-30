"""Sample the official tube mesh and check a constrained centreline fit."""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guide_path import solve

source, manifest, output = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=source)
parts = {p['id']: p for p in json.loads(Path(manifest).read_text())['parts']}
objects = [o for o in bpy.context.scene.objects if '4x3mm_PTFE_Guide_Tube' in o.get('source_path', '')]
if len(objects) != 1:
    raise RuntimeError(f'Expected one tube, got {len(objects)}')
obj = objects[0]
matrix = Matrix(parts[obj['part_id']]['matrix_mm'])
matrix.translation *= .001
vertices = np.array([tuple(matrix @ v.co) for v in obj.data.vertices])
edges = np.linspace(vertices[:, 1].min(), vertices[:, 1].max(), 42)
centres = []
counts = []
spreads = []
for low, high in zip(edges[:-1], edges[1:]):
    sample = vertices[(vertices[:, 1] >= low) & (vertices[:, 1] <= high)]
    if len(sample) == 0:
        raise RuntimeError('empty cross section; y is not a suitable path parameter')
    centres.append(sample.mean(axis=0))
    counts.append(len(sample))
    spreads.append(float(np.max(np.linalg.norm(sample[:, [0, 2]] - sample[:, [0, 2]].mean(axis=0), axis=1))))
centres = np.array(centres)
lengths = np.linalg.norm(np.diff(centres, axis=0), axis=1)
result = {'scope': 'binned centreline approximation; not a physical or collision simulation',
          'sections': len(centres), 'minimum_vertices_per_section': min(counts),
          'maximum_section_radius_mm': max(spreads) * 1000,
          'source_length_mm': lengths.sum() * 1000, 'poses': []}
for displacement in np.linspace(-.04, .04, 41):
    try:
        path = solve(centres, (displacement, 0, 0))
        errors = np.linalg.norm(np.diff(path, axis=0), axis=1) - lengths
        result['poses'].append({'displacement_mm': displacement * 1000,
                                'max_segment_error_mm': max(abs(errors)) * 1000,
                                'endpoint_error_mm': float(np.linalg.norm(path[-1] - centres[-1]) * 1000)})
    except (ValueError, RuntimeError) as exc:
        result['poses'].append({'displacement_mm': displacement * 1000, 'error': str(exc)})
Path(output).write_text(json.dumps(result, indent=2))
