import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from mechanical_video.production_handoff import evaluate, phase_event


class HandoffTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        (self.base / 'input.mp4').write_bytes(b'fixture')
        self.ref = {'path': 'input.mp4', 'sha256': hashlib.sha256(b'fixture').hexdigest()}
        self.task = {'state': 'pending', 'owner': 'qa', 'producer': 'visual', 'role': 'video_qa',
                     'goal': 'local proof', 'scope': 'fixed version', 'inputs': {'media': self.ref},
                     'outputs': ['qa/v1'], 'checks': {'decode': 'local', 'motion': 'playback'},
                     'capabilities': {'local': {'available': True, 'method': 'ffmpeg'},
                                      'playback': {'available': False, 'question': 'Is motion continuous?',
                                                   'next_reviewer': 'human playback reviewer'}},
                     'completion_events': ['completed', 'failed', 'stage_changed']}
        self.record = {'production_handoffs': {'new': self.task}}

    def test_fixed_ready_input_with_perceptual_gap_can_proceed(self):
        before = copy.deepcopy(self.record)
        result = evaluate(self.record, self.base, 'new')
        self.assertEqual(result['status'], 'READY')
        self.assertEqual(result['ready_checks'], ['decode'])
        self.assertEqual(result['deferred_checks'], ['motion'])
        self.assertEqual(before, self.record)

    def test_stale_missing_input_and_overlapping_writer_block(self):
        (self.base / 'input.mp4').write_bytes(b'new version')
        self.assertEqual(evaluate(self.record, self.base, 'new')['status'], 'BLOCKED')
        (self.base / 'input.mp4').write_bytes(b'fixture')
        self.record['production_handoffs']['active'] = dict(self.task, state='running', outputs=['qa'])
        self.assertEqual(evaluate(self.record, self.base, 'new')['status'], 'BLOCKED')

    def test_completed_same_input_and_capability_is_reused(self):
        self.record['production_handoffs']['previous'] = dict(self.task, state='completed', results=[self.ref])
        result = evaluate(self.record, self.base, 'new')
        self.assertEqual(result['status'], 'REUSE')
        self.task['scope'] = 'new review question'
        self.assertEqual(evaluate(self.record, self.base, 'new')['status'], 'READY')

    def test_missing_playback_alone_does_not_spawn(self):
        self.task['checks'] = {'motion': 'playback'}
        self.assertEqual(evaluate(self.record, self.base, 'new')['status'], 'CAPABILITY_GAP')

    def test_input_output_overlap_and_producer_self_review_block(self):
        self.task['outputs'] = ['input.mp4']
        self.assertEqual(evaluate(self.record, self.base, 'new')['status'], 'BLOCKED')
        self.task['outputs'] = ['qa/new']
        self.task['owner'] = 'visual'
        self.assertEqual(evaluate(self.record, self.base, 'new')['status'], 'BLOCKED')

    def test_phase_event_is_explicit_and_timezone_qualified(self):
        marker = phase_event('visual', 'start', 'thread-id')
        self.assertEqual(marker['type'], 'phase_start')
        self.assertTrue(marker['timestamp'].endswith('+00:00'))


if __name__ == '__main__':
    unittest.main()
