import unittest
import numpy as np
from guide_path import solve


class GuidePathTest(unittest.TestCase):
    def test_endpoints_and_segment_lengths(self):
        t = np.linspace(0, 1, 41)
        source = np.column_stack((0.2 * np.sin(np.pi * t), t, 0.1 * np.sin(np.pi * t)))
        for shift in (-0.04, 0.04):
            result = solve(source, (shift, 0, 0))
            np.testing.assert_allclose(result[0], source[0] + (shift, 0, 0), atol=1e-8)
            np.testing.assert_allclose(result[-1], source[-1], atol=1e-8)
            np.testing.assert_allclose(np.linalg.norm(np.diff(result, axis=0), axis=1),
                                       np.linalg.norm(np.diff(source, axis=0), axis=1), atol=1e-8)

    def test_unreachable_endpoints(self):
        with self.assertRaises(ValueError):
            solve([[0, 0, 0], [0, 1, 0], [0, 2, 0]], (4, 0, 0))


if __name__ == '__main__':
    unittest.main()
