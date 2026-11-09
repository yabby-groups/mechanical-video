import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from mechanical_video.video_qa import WEIGHTS, audio_score, gate
from mechanical_video.audio_qa import WEIGHTS as AUDIO_WEIGHTS
from mechanical_video.video_qa import inspect


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
        self.assertEqual(gate(dict.fromkeys(WEIGHTS), [{'severity': 'P1'}])[0], 'REWORK')

    def inspect_fixture(self, profile, audio=False, decode_error=False):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        media = root / 'test.mp4'
        media.write_bytes(b'mock media')
        streams = [{'codec_type': 'video', 'codec_name': 'h264', 'width': 1080, 'height': 1920}]
        if audio:
            streams.append({'codec_type': 'audio', 'codec_name': 'aac'})
        commands = []
        def run(command):
            commands.append(command)
            stdout = json.dumps({'streams': streams, 'format': {'duration': '3.433'}}) if command[0] == 'ffprobe' else ''
            code = 1 if decode_error and command[0] == 'ffmpeg' and '-vf' not in command and '-frames:v' not in command else 0
            if '-frames:v' in command:
                Path(command[-1]).write_bytes(b'frame fixture')
            return subprocess.CompletedProcess(command, code, stdout, '')
        with patch('mechanical_video.video_qa.run', side_effect=run):
            report = inspect(media, root / 'qa', profile=profile)
        return report, commands

    def test_local_profiles_do_not_report_formal_duration_or_optional_audio(self):
        silent, commands = self.inspect_fixture('local-silent')
        self.assertEqual(silent['issues'], [])
        self.assertFalse(silent['formal_acceptance'])
        self.assertEqual(silent['profile'], 'local-silent')
        self.assertFalse(any('-af' in c for c in commands))
        local, _ = self.inspect_fixture('local-av', audio=True)
        self.assertEqual(local['issues'], [])

    def test_short_formal_media_still_requires_review_and_stream_decode_checks(self):
        formal, _ = self.inspect_fixture('formal', audio=True)
        self.assertEqual(formal['status'], 'NEEDS_REVIEW')
        self.assertNotIn('duration', [i['category'] for i in formal['issues']])
        self.assertFalse(formal['formal_acceptance'])
        missing, _ = self.inspect_fixture('local-av')
        self.assertEqual(missing['status'], 'FAIL')
        broken, _ = self.inspect_fixture('local-silent', decode_error=True)
        self.assertEqual(broken['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
