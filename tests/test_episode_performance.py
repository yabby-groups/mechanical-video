import unittest

from mechanical_video.episode_performance import compare, connect, record_snapshot


def record(video, platform='example', duration=100, actual=None):
    return {'episode_id': video, 'video_version': video, 'platform': platform,
            'duration_seconds': duration, 'title': 'Title', 'cover_version': 'cover1',
            'subjective_prediction': {'audience_score': 88, 'basis': 'Opening composition'},
            'actual': actual}


def observation(plays=100, window='first 7 days'):
    return {'source': 'export.csv', 'observed_at': '2026-10-30',
            'measurement_window': window, 'metrics': {'plays': plays, 'completion_rate': .5}}


class PerformanceTest(unittest.TestCase):
    def setUp(self):
        self.db = connect(':memory:')

    def tearDown(self):
        self.db.close()

    def test_prediction_is_not_actual_and_rate_validation(self):
        ident = record_snapshot(self.db, record('a'))
        self.assertEqual(compare(self.db, ident, 'plays')['status'], 'NO_ACTUAL_DATA')
        bad = record('b', actual=observation())
        bad['actual']['metrics']['completion_rate'] = 50
        with self.assertRaises(ValueError):
            record_snapshot(self.db, bad)

    def test_comparison_filters_and_deduplicates_snapshots(self):
        target = record_snapshot(self.db, record('a', actual=observation(100)))
        record_snapshot(self.db, record('b', duration=105, actual=observation(20)))
        record_snapshot(self.db, record('b', duration=105, actual=observation(40)))
        record_snapshot(self.db, record('c', platform='other', actual=observation(900)))
        record_snapshot(self.db, record('d', duration=130, actual=observation(900)))
        record_snapshot(self.db, record('e', actual=observation(900, 'first 30 days')))
        result = compare(self.db, target, 'plays')
        self.assertEqual(result['peer_count'], 1)
        self.assertEqual(result['peer_median'], 40)
        self.assertEqual(result['difference_from_median'], 60)
        latest = observation()
        latest['metrics'] = {'likes': 1}
        record_snapshot(self.db, record('b', duration=105, actual=latest))
        self.assertEqual(compare(self.db, target, 'plays')['status'], 'NO_COMPARABLE_PEERS')


if __name__ == '__main__':
    unittest.main()
