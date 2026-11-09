import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from mechanical_video.perceptual_review import QUESTIONS, MODALITIES, digest, finalize, full_coverage, prepare, validate
from mechanical_video.audience_qa import WEIGHTS, delivery_gate
from mechanical_video.video_qa import WEIGHTS as VIDEO_WEIGHTS, gate as video_gate


class PerceptualReviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = self.root / 'observations.txt'
        self.evidence.write_text('Synthetic reviewer fixture, NOT an actual film assessment')

    def review(self, media_hash='a', duration=10):
        ref = str(self.evidence)
        return {'media_sha256': media_hash, 'duration': duration,
                'reviewer': {'id': 'independent-reviewer', 'independent': True,
                             'method': 'realtime_av_playback', 'tool': 'fixture-player', 'completed_at': '2026-11-09T10:00:00+08:00'},
                'evidence': [{'path': ref, 'sha256': digest(self.evidence)}],
                'coverage': {key: {'observed': True, 'ranges': [[0, duration]], 'notes': 'fixture full coverage', 'evidence': ref} for key in MODALITIES},
                'answers': {key: {'time': 1, 'observation': 'fixture observation', 'verdict': 'clear', 'evidence': ref} for key in QUESTIONS},
                'dimensions': {key: {'score': 90, 'time': 1, 'evidence': [ref], 'rationale': 'fixture'} for key in WEIGHTS}, 'issues': []}

    def test_full_coverage_rejects_gaps_nonfinite_and_boolean(self):
        self.assertTrue(full_coverage([[5, 10], [0, 5]], 10))
        for ranges in [[], [[0, 4], [5, 10]], [[0, float('nan')]], [[False, 10]], [[0, 11]]]:
            self.assertFalse(full_coverage(ranges, 10))

    def test_stale_hash_producer_and_stills_cannot_pass(self):
        good = self.review()
        self.assertEqual(validate(good, 'a', 10, ['producer'])['status'], 'COMPLETE')
        for modify in [lambda r: r.update(media_sha256='old'),
                       lambda r: r['reviewer'].update(id='producer'),
                       lambda r: r['reviewer'].update(method='sampled_stills'),
                       lambda r: r['coverage']['audio'].update(observed=False),
                       lambda r: r['coverage']['continuity'].update(ranges=[[0, 4], [5, 10]]),
                       lambda r: r['answers']['first_cause'].update(time=99)]:
            review = copy.deepcopy(good); modify(review)
            self.assertEqual(validate(review, 'a', 10, ['producer'])['status'], 'NEEDS_REVIEW')
        self.evidence.write_text('changed evidence')
        self.assertEqual(validate(good, 'a', 10, ['producer'])['status'], 'NEEDS_REVIEW')

    def test_comprehension_failure_and_known_issue_cannot_be_scored_away(self):
        r = self.review();r['answers']['first_cause']['verdict'] = 'unclear'
        self.assertEqual(validate(r, 'a', 10, ['producer'])['status'], 'REWORK')
        r = self.review();r['issues'] = [{'issue_id': 'P1-A', 'description': 'fixture', 'severity': 'P1', 'status': 'open'}]
        self.assertEqual(validate(r, 'a', 10, ['producer'])['status'], 'REWORK')

    def test_delivery_does_not_trust_pass_labels_or_totals(self):
        tech = {'sha256': 'a', 'status': 'PASS', 'total': 90, 'duration': 10,
                'scores': dict.fromkeys(VIDEO_WEIGHTS, 90), 'issues': [],
                'producer_ids': ['producer'], 'perceptual_review': self.review()}
        aud = {'video_sha256': 'a', 'status': 'PASS', 'total': 90, 'duration': 10,
               'dimensions': self.review()['dimensions'], 'coverage': dict.fromkeys(MODALITIES, True),
               'producer_ids': ['producer'], 'perceptual_review': self.review()}
        self.assertEqual(delivery_gate(tech, aud), 'PASS')
        forged = copy.deepcopy(aud);forged.pop('perceptual_review')
        self.assertEqual(delivery_gate(tech, forged), 'NEEDS_REVIEW')
        forged = copy.deepcopy(aud);forged['dimensions']['opening']['score'] = None
        self.assertEqual(delivery_gate(tech, forged), 'NEEDS_REVIEW')
        forged = copy.deepcopy(tech);forged['scores'] = {}
        self.assertEqual(delivery_gate(forged, aud), 'NEEDS_REVIEW')
        forged = copy.deepcopy(tech);forged['scores']['technical'] = float('nan')
        self.assertEqual(delivery_gate(forged, aud), 'NEEDS_REVIEW')
        self.assertEqual(video_gate({}, [])[0], 'NEEDS_REVIEW')

    def test_real_media_packet_and_review_import_remain_separate(self):
        video = self.root / 'fixture.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=red:s=128x128:r=10:d=2',
                        '-f', 'lavfi', '-i', 'sine=frequency=400:duration=2', '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(video)], check=True)
        packet = self.root / 'packet'
        task = prepare(video, packet, ['producer'])
        self.assertEqual(task['status'], 'NEEDS_REVIEW')
        self.assertEqual(digest(packet / 'media.mp4'), digest(video))
        template = json.loads((packet / 'review-template.json').read_text())
        self.assertEqual(validate(template, task['media_sha256'], task['duration'], ['producer'])['status'], 'NEEDS_REVIEW')
        with self.assertRaises(FileExistsError): prepare(video, packet, ['producer'])
        review = self.review(task['media_sha256'], task['duration'])
        review['answers'] = {k: dict(v, time=0.5) for k, v in review['answers'].items()}
        review_path = self.root / 'review.json';review_path.write_text(json.dumps(review))
        base = self.root / 'base.json';base.write_text(json.dumps({'video_sha256': task['media_sha256'], 'duration': task['duration'], 'status': 'NEEDS_REVIEW'}))
        output = self.root / 'imported.json'
        result = finalize(review_path, packet / 'task.json', base, output, 'audience')
        self.assertEqual(result['status'], 'PASS')
        self.assertFalse(result['formal_acceptance'])
        self.assertEqual(json.loads(base.read_text())['status'], 'NEEDS_REVIEW')
        with self.assertRaises(FileExistsError): finalize(review_path, packet / 'task.json', base, output, 'audience')
        review['answers']['first_cause']['verdict'] = 'unclear'
        review_path.write_text(json.dumps(review))
        failed = finalize(review_path, packet / 'task.json', base, self.root / 'failed.json', 'audience')
        self.assertEqual(failed['status'], 'REWORK')
        self.assertIsNone(failed['total'])
        self.assertFalse(failed['formal_acceptance'])



if __name__ == '__main__':
    unittest.main()
