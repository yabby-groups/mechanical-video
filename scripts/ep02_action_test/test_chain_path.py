import math
import unittest

from chain_path import length, point


class ChainPathTest(unittest.TestCase):
    def test_length_and_endpoints_across_travel(self):
        args = (.245, .1224, .035, .0949, .1411)
        baseline = length(*args)
        for delta in (-.04, 0, .04):
            self.assertAlmostEqual(length(*args, delta), baseline)
            self.assertEqual(point(0, *args, delta)[0], (.245, .0949))
            end, _ = point(baseline, *args, delta)
            self.assertAlmostEqual(end[0], .1224 + delta)
            self.assertAlmostEqual(end[1], .1411)
        for i in range(81):
            point(baseline, *args, -.04 + i * .001)

    def test_centreline_is_continuous(self):
        args = (.245, .1224, .035, .0949, .1411)
        total = length(*args)
        points = [point(total * i / 1000, *args)[0] for i in range(1001)]
        self.assertLess(max(math.dist(a, b) for a, b in zip(points, points[1:])), total / 999)

    def test_rejects_invalid_geometry(self):
        with self.assertRaises(ValueError):
            length(.245, .1224, .035, .1411, .0949)
        with self.assertRaises(ValueError):
            length(.245, .1224, .035, .0949, .1411, -.2)


if __name__ == '__main__':
    unittest.main()
