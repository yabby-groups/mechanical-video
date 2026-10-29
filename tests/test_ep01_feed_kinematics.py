import unittest

from scripts.ep01_gear_corrected.gear_kinematics import coaxial_gear, feed_gear, scale, tooth_cycle_frequency


class FeedKinematicsTest(unittest.TestCase):
    def test_contact_motion_and_shared_shaft_follow_downward_feed(self):
        center = (0., 0., 0.)
        left = feed_gear((-.004267, 0., 0.), (0., -1., 0.), center, .000875, .007)
        right = feed_gear((.004267, 0., 0.), (0., -1., 0.), center, .000875, .007)
        for gear in (left, right):
            self.assertAlmostEqual(gear['contact_velocity_m_s'][2], -.007)
            self.assertAlmostEqual(gear['contact_velocity_m_s'][0], 0.)
        self.assertLess(left['rate_rad_s']*right['rate_rad_s'], 0.)
        large = coaxial_gear((.004267, .0048, 0.), (0., 1., 0.), (.004267, 0., 0.), right)
        for actual, expected in zip(scale(large['axis'], large['rate_rad_s']),
                                    scale(right['axis'], right['rate_rad_s'])):
            self.assertAlmostEqual(actual, expected)

    def test_reversing_a_local_axis_preserves_world_motion(self):
        positive = feed_gear((.004267, 0., 0.), (0., 1., 0.), (0., 0., 0.), .000875, .007)
        negative = feed_gear((.004267, 0., 0.), (0., -1., 0.), (0., 0., 0.), .000875, .007)
        self.assertAlmostEqual(positive['rate_rad_s'], -negative['rate_rad_s'])
        self.assertEqual(positive['contact_velocity_m_s'], negative['contact_velocity_m_s'])

    def test_invalid_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            feed_gear((0., 0., 0.), (0., 1., 0.), (0., 0., 0.), .000875, .007)
        with self.assertRaises(ValueError):
            feed_gear((.004, 0., 0.), (1., 0., 0.), (0., 0., 0.), .000875, .007)
        gear = feed_gear((.004, 0., 0.), (0., 1., 0.), (0., 0., 0.), .000875, .007)
        with self.assertRaises(ValueError):
            coaxial_gear((.02, 0., 0.), (0., 1., 0.), (.004, 0., 0.), gear)

    def test_tooth_pattern_does_not_reverse_at_preview_rate(self):
        slow = feed_gear((.004267, 0., 0.), (0., 1., 0.), (0., 0., 0.), .000875, .0025)
        self.assertLess(tooth_cycle_frequency(slow['rate_rad_s'], 50, 15.), 6.)
        with self.assertRaises(ValueError):
            tooth_cycle_frequency(slow['rate_rad_s'], 50, 7.5)
        fast = feed_gear((.004267, 0., 0.), (0., 1., 0.), (0., 0., 0.), .000875, .007)
        with self.assertRaises(ValueError):
            tooth_cycle_frequency(fast['rate_rad_s'], 50, 7.5)
        with self.assertRaises(ValueError):
            tooth_cycle_frequency(fast['rate_rad_s'], 50, 30.)


if __name__ == '__main__':
    unittest.main()
