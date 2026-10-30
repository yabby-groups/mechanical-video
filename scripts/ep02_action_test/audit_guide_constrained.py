"""Sample endpoint, centreline and mesh-edge errors for the source tube."""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

from guide_mesh_path import bind, deform

mesh = trimesh.load(sys.argv[1], force='mesh')
vertices = np.asarray(mesh.vertices) / 1000
centres = np.asarray(json.loads(Path(sys.argv[2]).read_text())['centres_m'])
binding = bind(vertices, centres)
edges = mesh.edges_unique
lengths = np.linalg.norm(vertices[edges[:, 0]] - vertices[edges[:, 1]], axis=1)
segments = np.linalg.norm(np.diff(centres, axis=0), axis=1)
result = {'scope': 'sampled mesh-edge and centreline checks; not collision or physical simulation',
          'vertices': len(vertices), 'poses': []}
for displacement in np.linspace(-.015, 0, 31):
    transformed, path = deform(binding, centres, float(displacement))
    ratios = np.linalg.norm(transformed[edges[:, 0]] - transformed[edges[:, 1]], axis=1) / lengths - 1
    errors = np.linalg.norm(np.diff(path, axis=0), axis=1) - segments
    result['poses'].append({'displacement_mm': float(displacement * 1000),
                            'max_abs_edge_strain': float(np.max(np.abs(ratios))),
                            'p99_abs_edge_strain': float(np.percentile(np.abs(ratios), 99)),
                            'mean_abs_edge_strain': float(np.mean(np.abs(ratios))),
                            'max_segment_error_mm': float(np.max(np.abs(errors)) * 1000),
                            'fixed_endpoint_error_mm': float(np.linalg.norm(path[-1] - centres[-1]) * 1000),
                            'moving_endpoint_error_mm': float(np.linalg.norm(path[0] - centres[0] - [displacement, 0, 0]) * 1000)})
Path(sys.argv[3]).write_text(json.dumps(result, indent=2))
print('max edge strain:', max(x['max_abs_edge_strain'] for x in result['poses']))
print('max mean edge strain:', max(x['mean_abs_edge_strain'] for x in result['poses']))
