"""Sample the official STEP tube's circular cross sections."""
import json
import sys
from pathlib import Path

import numpy as np
from build123d import GeomType, import_step


def main():
    solid = import_step(sys.argv[1])
    faces = [face for face in solid.faces() if face.geom_type == GeomType.BSPLINE]
    if len(faces) != 2:
        raise RuntimeError('Expected the inner and outer tube surfaces')
    candidates = []
    for face in faces:
        points = np.array([tuple(face.position_at(i / 32, .5)) for i in range(32)])
        candidates.append((np.linalg.norm(points - points.mean(axis=0), axis=1).mean(), face))
    radius, outer = max(candidates, key=lambda item: item[0])
    if not 1.9 < radius < 2.1:
        raise RuntimeError(f'Unexpected outer tube radius: {radius}')
    centres, spreads = [], []
    for v in np.linspace(1, 0, 101):
        points = np.array([tuple(outer.position_at(i / 32, v)) for i in range(32)])
        center = points.mean(axis=0)
        centres.append((center / 1000).tolist())
        spreads.append(float(np.max(np.linalg.norm(points - center, axis=1))))
    data = {'scope': 'STEP cross-section centre approximation, metres; not a physical simulation',
            'outer_radius_mm': radius, 'max_cross_section_radius_mm': max(spreads),
            'centres_m': centres}
    Path(sys.argv[2]).write_text(json.dumps(data, indent=2))
    print('sections:', len(centres), 'outer radius mm:', radius, 'max radius mm:', max(spreads))


if __name__ == '__main__':
    main()
