import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/ep02_action_test'))
from guide_mesh_path import bind, deform


class EP02ContinuityTest(unittest.TestCase):
    def test_constrained_tube_keeps_anchors_and_segment_lengths(self):
        data = json.loads((ROOT / 'scripts/ep02_action_test/guide_centres.json').read_text())
        centres = np.asarray(data['centres_m'])
        vertices = centres + np.array((.001, 0, 0))
        binding = bind(vertices, centres)
        output, path = deform(binding, centres, -.015)
        np.testing.assert_allclose(path[0], centres[0] + [-.015, 0, 0], atol=1e-8)
        np.testing.assert_allclose(path[25:], centres[25:], atol=1e-8)
        np.testing.assert_allclose(np.linalg.norm(np.diff(path, axis=0), axis=1),
                                   np.linalg.norm(np.diff(centres, axis=0), axis=1), atol=1e-8)
        self.assertTrue(np.isfinite(output).all())

    def test_periodic_motion_position_and_velocity_match(self):
        duration = 107
        cycles = round(duration / 6.3)
        omega = 2 * math.pi * cycles / duration
        position = lambda t: -.0075 + .0075 * math.sin(omega * t)
        velocity = lambda t: .0075 * omega * math.cos(omega * t)
        self.assertAlmostEqual(position(0), position(duration), places=12)
        self.assertAlmostEqual(velocity(0), velocity(duration), places=12)
        self.assertGreater(abs(velocity(0)), .001)


if __name__ == '__main__':
    unittest.main()
