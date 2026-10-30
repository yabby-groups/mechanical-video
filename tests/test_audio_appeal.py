import unittest
import json
import tempfile
from pathlib import Path

from mechanical_video.audio_appeal import WEIGHTS, appeal_gate, delivery_gate
from mechanical_video.audio_direction import create


class AudioAppealTest(unittest.TestCase):
    def test_direction_preserves_voice_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'timeline.json'
            source.write_text(json.dumps({'model': 'qwen3-tts-flash', 'voice': 'Kai', 'events': [
                {'text': '热端', 'start': 0, 'end': 1}]}))
            output = root / 'direction.json'
            result = create(source, output)
            self.assertEqual(result['voice'], 'Kai')
            self.assertEqual(result['segments'][0]['key_terms'], ['热端'])
            self.assertIsNone(result['segments'][0]['sync_point'])
            with self.assertRaises(FileExistsError):
                create(source, output)
    def test_missing_evidence_blocks_pass(self):
        dims = {k: {'score': 90, 'evidence': ['audio'], 'rationale': 'reviewed'} for k in WEIGHTS}
        self.assertEqual(appeal_gate(dims), ('PASS', 90))
        dims['emotion']['evidence'] = []
        self.assertEqual(appeal_gate(dims), ('NEEDS_REVIEW', None))

    def test_delivery_requires_matching_audio_and_both_gates(self):
        technical = {'audio_sha256': 'a', 'status': 'PASS', 'total': 90}
        appeal = {'audio_sha256': 'a', 'status': 'PASS', 'total': 85}
        self.assertEqual(delivery_gate(technical, appeal), 'PASS')
        technical['status'] = 'NEEDS_REVIEW'
        self.assertEqual(delivery_gate(technical, appeal), 'NEEDS_REVIEW')
        appeal['audio_sha256'] = 'b'
        with self.assertRaises(ValueError):
            delivery_gate(technical, appeal)
