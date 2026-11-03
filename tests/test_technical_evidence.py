import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from mechanical_video import technical_evidence as evidence
from mechanical_video import video_qa, audio_qa


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class TechnicalEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        cls.media = cls.base / 'short.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=160x120:rate=10:duration=1',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1', '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(cls.media)], check=True)
        cls.script = cls.base / 'script.txt'
        cls.script.write_text('temporary synthetic test')
        cls.subtitles = cls.base / 'subtitles.json'
        cls.subtitles.write_text(json.dumps([{'start': 0, 'end': .5, 'text': '临时测试'}]))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(dir=self.base)
        self.addCleanup(self.tempdir.cleanup)
        self.output = Path(self.tempdir.name)
        self.deps = {'script': self.script, 'subtitles': self.subtitles}

    def collect(self, **kwargs):
        return evidence.collect(self.media, self.output / 'cache', self.deps, **kwargs)

    def test_real_probe_decode_subtitles_and_hit(self):
        report = self.collect()
        self.assertTrue(all(c['status'] == 'PASS' for c in report['checks'].values()))
        second = self.collect()
        self.assertEqual(set(second['reused']), set(report['checks']))
        self.assertIsNone(report['perceptual_scores'])

    def test_dependency_and_parameter_invalidation_is_per_item(self):
        self.collect()
        before = self.script.read_text()
        self.script.write_text('changed')
        try:
            second = self.collect()
            self.assertIn('decode', second['reused'])
            with self.assertRaises(ValueError):
                evidence.load(self.output / 'cache/technical-evidence.json', self.media, ['probe'], {'script': self.script})
        finally:
            self.script.write_text(before)
        third = self.collect(parameters={'frame_fractions': [.2, .8]})
        self.assertIn('decode', third['reused'])
        self.assertNotIn('frames', third['reused'])

    def test_corrupt_failed_missing_artifacts_not_reused(self):
        report = self.collect()
        path = self.output / 'cache/technical-evidence.json'
        report['checks']['decode']['result']['returncode'] = 1
        report['checks']['audio_decode']['status'] = 'FAIL'
        Path(report['checks']['frames']['result']['frames'][0]['path']).unlink()
        path.write_text(json.dumps(report))
        with self.assertRaises(ValueError):
            evidence.load(path, self.media, ['decode'])
        result = self.collect()
        self.assertNotIn('decode', result['reused'])
        self.assertNotIn('audio_decode', result['reused'])
        self.assertNotIn('frames', result['reused'])
        self.assertIn('probe', result['reused'])

    def test_changed_media_not_accepted(self):
        self.collect()
        other = self.output / 'changed.mp4'
        other.write_bytes(self.media.read_bytes() + b'changed')
        with self.assertRaises(ValueError):
            evidence.load(self.output / 'cache/technical-evidence.json', other, ['probe'])

    def test_subtitle_constraints(self):
        self.collect()
        original = self.subtitles.read_text()
        try:
            for text in ('x' * 21, 'two\nlines'):
                self.subtitles.write_text(json.dumps([{'start': 0, 'end': .5, 'text': text}]))
                report = self.collect()
                self.assertEqual(report['checks']['subtitles']['status'], 'FAIL')
                self.assertIn('decode', report['reused'])
        finally:
            self.subtitles.write_text(original)

    def test_qa_reuse_preserves_independent_boundary(self):
        self.collect()
        path = self.output / 'cache/technical-evidence.json'
        # After version checks no expensive probe/decode/scan should be invoked again.
        original = subprocess.run
        def only_versions(command, **kwargs):
            self.assertEqual(command[-1], '-version', command)
            return original(command, **kwargs)
        with patch('mechanical_video.technical_evidence.subprocess.run', side_effect=only_versions):
            video = video_qa.inspect(self.media, self.output / 'video', technical_evidence=path)
            audio = audio_qa.inspect(self.media, self.script, self.output / 'audio', technical_evidence=path)
        self.assertEqual(video['status'], 'REWORK')  # Known formal duration/resolution failures remain failures.
        self.assertEqual(audio['status'], 'NEEDS_REVIEW')
        self.assertTrue(all(score is None for score in audio['scores'].values()))
        self.assertEqual(audio['asr']['status'], 'not_requested')
        self.assertTrue(video['decode_passed'])
        self.assertIsNone(video['scores']['mechanical'])

    def test_tool_version_change_and_corrupt_manifest(self):
        self.collect()
        original_versions = evidence.versions()
        with patch.object(evidence, 'versions', return_value=dict(original_versions, ffmpeg='changed-version')):
            changed = self.collect()
        self.assertEqual(changed['reused'], [])
        path = self.output / 'cache/technical-evidence.json'
        path.write_text('[]')
        with self.assertRaises(ValueError):
            evidence.load(path, self.media, ['decode'])
        rebuilt = self.collect()
        self.assertEqual(rebuilt['reused'], [])

    def test_partial_loading_only_reexecutes_stale_checks(self):
        report = self.collect(parameters={'frame_fractions': [.2, .8]})
        path = self.output / 'cache/technical-evidence.json'
        # Inherited parameters now work; unrelated missing dependencies leave decode reusable.
        loaded = evidence.load(path, self.media, ['decode', 'frames'], partial=True)
        self.assertEqual(loaded['_validated_checks'], ['decode', 'frames'])
        Path(report['checks']['frames']['result']['frames'][0]['path']).unlink()
        report['dependency_paths']['script'] = str(self.output / 'missing-script')
        path.write_text(json.dumps(report))
        loaded = evidence.load(path, self.media, ['decode', 'frames'], partial=True)
        self.assertEqual(loaded['_validated_checks'], ['decode'])
        self.assertIn('identity.dependencies', loaded['_mismatches'])
        self.assertTrue(any('frames' in x for x in loaded['_mismatches']))
        command = loaded['checks']['decode']['result']['command']
        with patch('mechanical_video.technical_evidence.subprocess.run') as execute:
            self.assertEqual(evidence.evidence_runner(loaded)(command).returncode, 0)
            execute.assert_not_called()
        with self.assertRaises(ValueError):
            evidence.load(path, self.media, ['decode'])

    def test_timeline_association_and_overlap(self):
        timeline = self.output / 'timeline.json'
        timeline.write_text(json.dumps({'media_sha256': evidence.digest(self.media),
                                       'dependencies': {k: evidence.digest(v) for k, v in self.deps.items()}}))
        self.deps['timeline'] = timeline
        self.assertEqual(self.collect()['checks']['timeline']['status'], 'PASS')
        timeline.write_text('{}')
        self.assertEqual(self.collect()['checks']['timeline']['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
