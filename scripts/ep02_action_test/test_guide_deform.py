import unittest

from guide_deform import displacement_weight


class GuideDeformTest(unittest.TestCase):
    def test_endpoints_and_monotonic_weights(self):
        weights = [displacement_weight(i / 100, 0, 1) for i in range(101)]
        self.assertEqual(weights[0], 1)
        self.assertEqual(weights[-1], 0)
        self.assertTrue(all(a >= b for a, b in zip(weights, weights[1:])))

    def test_rejects_degenerate_extent(self):
        with self.assertRaises(ValueError):
            displacement_weight(1, 1, 1)


if __name__ == '__main__':
    unittest.main()
