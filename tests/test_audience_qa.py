import tempfile
import unittest
from pathlib import Path
import subprocess

from mechanical_video.audience_qa import WEIGHTS, delivery_gate, gate, inspect, shot_at


class AudienceQATest(unittest.TestCase):
    def test_delivery_requires_both_gates_for_same_video(self):
        technical = {'sha256': 'a', 'status': 'PASS', 'total': 90}
        audience = {'video_sha256': 'a', 'status': 'PASS', 'total': 85}
        self.assertEqual(delivery_gate(technical, audience), 'PASS')
        technical['status'] = 'REWORK'
        self.assertEqual(delivery_gate(technical, audience), 'REWORK_TECHNICAL')
        technical['status'] = 'NEEDS_REVIEW'
        self.assertEqual(delivery_gate(technical, audience), 'NEEDS_REVIEW')
        audience['video_sha256'] = 'b'
        with self.assertRaises(ValueError):
            delivery_gate(technical, audience)
    def test_gate_requires_evidence_and_complete_media(self):
        dimensions = {key: {'score': 90, 'evidence': ['frame'], 'rationale': 'observed'} for key in WEIGHTS}
        coverage = dict.fromkeys(('video', 'audio', 'captions', 'continuity'), True)
        self.assertEqual(gate(dimensions, coverage), ('PASS', 90.0))
        coverage['audio'] = False
        self.assertEqual(gate(dimensions, coverage), ('NEEDS_REVIEW', None))
        coverage['audio'] = True
        dimensions['opening']['score'] = float('nan')
        self.assertEqual(gate(dimensions, coverage), ('NEEDS_REVIEW', None))

    def test_timeline_boundary(self):
        shots = [{'start': 0, 'end': 1}, {'start': 1, 'end': 2, 'shot_id': 'second'}]
        self.assertEqual(shot_at(shots, 1), 'second')
        self.assertIsNone(shot_at(shots, 2))

    def test_sampled_video_remains_unverified(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / 'input.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=red:s=128x128:r=10:d=2',
                            '-c:v', 'libx264', str(video)], check=True)
            report = inspect(video, root / 'review')
            self.assertEqual(report['status'], 'NEEDS_REVIEW')
            self.assertIsNone(report['total'])
            self.assertTrue(all(Path(frame['path']).exists() for frame in report['frames']))
            with self.assertRaises(FileExistsError):
                inspect(video, root / 'review')


if __name__ == '__main__':
    unittest.main()
