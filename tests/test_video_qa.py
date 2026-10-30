import unittest

from mechanical_video.video_qa import WEIGHTS, audio_score, gate
from mechanical_video.audio_qa import WEIGHTS as AUDIO_WEIGHTS


class QualityGateTest(unittest.TestCase):
    def test_audio_score_requires_matching_evidence_and_all_dimensions(self):
        report = {'audio_sha256': 'a', 'status': 'PASS', 'scores': dict.fromkeys(AUDIO_WEIGHTS, 90), 'total': 90, 'issues': []}
        self.assertEqual(audio_score(report, 'a'), 90)
        with self.assertRaises(ValueError):
            audio_score(report, 'different')
        report['scores']['subtitle_sync'] = None
        self.assertIsNone(audio_score(report, 'a'))
        report['scores']['subtitle_sync'] = 90
        report['issues'] = [{'severity': 'P1'}]
        self.assertIsNone(audio_score(report, 'a'))
    def test_missing_evidence_cannot_pass(self):
        scores = dict.fromkeys(WEIGHTS, 100)
        scores['mechanical'] = None
        self.assertEqual(gate(scores, [])[0], 'NEEDS_REVIEW')

    def test_thresholds_and_critical_issues(self):
        scores = dict.fromkeys(WEIGHTS, 100)
        self.assertEqual(gate(scores, [])[0], 'PASS')
        scores['mechanical'] = 79
        self.assertEqual(gate(scores, [])[0], 'REWORK')
        self.assertEqual(gate(scores, [{'severity': 'P0'}])[0], 'FAIL')
        self.assertEqual(gate(dict.fromkeys(WEIGHTS, 100), [{'severity': 'P1'}])[0], 'REWORK')


if __name__ == '__main__':
    unittest.main()
