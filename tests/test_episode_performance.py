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

    def test_observed_retention_engagement_and_attribution_are_preserved(self):
        actual = observation(2448)
        actual['media_type'] = 'video'
        actual['metrics'] = {'retention_5s': .5172, 'retention_9s': .3216,
                             'retention_18s': .1586, 'retention_27s': .1035,
                             'skip_2s_rate': .224, 'like_rate': .0061,
                             'share_rate': .0004, 'comment_rate': 0,
                             'save_rate': .0033, 'attributed_followers': 4}
        ident = record_snapshot(self.db, record('measured', actual=actual))
        self.assertEqual(compare(self.db, ident, 'retention_9s')['target'], .3216)
        for metric, value in [('share_rate', 4), ('retention_5s', 51.72),
                              ('attributed_followers', 4.5), ('attributed_followers', -1)]:
            with self.subTest(metric=metric, value=value):
                invalid = observation()
                invalid['metrics'] = {metric: value}
                with self.assertRaises(ValueError):
                    record_snapshot(self.db, record('invalid', actual=invalid))

    def test_media_type_must_match_and_unknown_is_not_assumed_video(self):
        actual = observation(2448)
        actual['media_type'] = 'video'
        target = record_snapshot(self.db, record('target', actual=actual))
        image = observation(360)
        image['media_type'] = 'image_post'
        record_snapshot(self.db, record('image', actual=image))
        record_snapshot(self.db, record('legacy', actual=observation(900)))
        self.assertEqual(compare(self.db, target, 'plays')['status'], 'NO_COMPARABLE_PEERS')
        peer = observation(2000)
        peer['media_type'] = 'video'
        record_snapshot(self.db, record('video', actual=peer))
        result = compare(self.db, target, 'plays')
        self.assertEqual(result['peer_count'], 1)
        self.assertEqual(result['peer_median'], 2000)
        self.assertEqual(result['media_type'], 'video')
        with self.assertRaises(ValueError):
            record_snapshot(self.db, record('invalid', actual={**actual, 'media_type': 'unknown'}))


if __name__ == '__main__':
    unittest.main()
