import importlib.util
import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / 'scripts/ep01_narration_revision/motion.py'
spec = importlib.util.spec_from_file_location('ep01_deposition_motion', SOURCE)
motion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(motion)


class DepositionTest(unittest.TestCase):
    def test_path_retains_every_corner_and_returns_to_start(self):
        for layer, (path, _, _, fractions) in enumerate(motion.PATHS):
            self.assertEqual(path[0], path[-1])
            for fraction, expected in zip(fractions, path):
                actual = motion.deposition_point(fraction, layer)
                for value, target in zip(actual, expected):
                    self.assertAlmostEqual(value, target, places=9)

    def test_layer_and_lift_order(self):
        self.assertEqual(motion.deposition(42), 0)
        self.assertEqual(motion.deposition(72), 1)
        self.assertEqual(motion.deposition(76), 1)
        self.assertEqual(motion.deposition(86), 2)
        self.assertEqual(motion.state(72)['lift'], 0)
        self.assertAlmostEqual(motion.state(76)['lift'], .0015)


if __name__ == '__main__':
    unittest.main()
