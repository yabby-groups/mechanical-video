"""Inspect a tube centreline candidate using mesh-surface geodesic bins."""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra


def main():
    mesh = trimesh.load(sys.argv[1], force='mesh')
    vertices = np.asarray(mesh.vertices)
    edges = mesh.edges_unique
    lengths = np.linalg.norm(vertices[edges[:, 0]] - vertices[edges[:, 1]], axis=1)
    graph = coo_matrix((np.r_[lengths, lengths],
                        (np.r_[edges[:, 0], edges[:, 1]], np.r_[edges[:, 1], edges[:, 0]])),
                       shape=(len(vertices), len(vertices))).tocsr()
    start = int(np.argmin(vertices[:, 1]))
    distances = dijkstra(graph, indices=start)
    if not np.isfinite(distances).all():
        raise RuntimeError('tube mesh is not connected')
    width = 3.0
    bins = np.floor(distances / width).astype(int)
    centres, radii, counts = [], [], []
    for i in range(bins.max() + 1):
        section = vertices[bins == i]
        if len(section) < 3:
            continue
        centre = np.mean(section, axis=0)
        centres.append(centre.tolist())
        radii.append(float(np.max(np.linalg.norm(section - centre, axis=1))))
        counts.append(len(section))
    result = {'scope': 'surface-geodesic bins, not a verified physical centreline',
              'start_vertex': start, 'bin_mm': width, 'sections': len(centres),
              'radius_max_mm': max(radii), 'radius_p95_mm': float(np.percentile(radii, 95)),
              'min_vertices': min(counts), 'centres_mm': centres}
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2))
    print({k: v for k, v in result.items() if k != 'centres_mm'})


if __name__ == '__main__':
    main()
