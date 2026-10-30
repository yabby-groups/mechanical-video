import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from mechanical_video.audio_qa import inspect, silence_intervals


class AudioQATest(unittest.TestCase):
    def test_silence_interval_open_at_eof(self):
        self.assertEqual(silence_intervals('silence_start: 1.0', 3.0), [(1.0, 3.0)])

    def test_real_silent_audio_never_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, script, out = root / 'silent.wav', root / 'script.txt', root / 'out'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'anullsrc=r=16000:cl=mono', '-t', '2', str(source)], check=True)
            script.write_text('热端')
            report = inspect(source, script, out)
            self.assertEqual(report['status'], 'NEEDS_REVIEW')
            self.assertIsNone(report['total'])
            self.assertTrue(all(value is None for value in report['scores'].values()))
            self.assertTrue(any(i['category'] == 'silence_candidate' for i in report['issues']))
            self.assertEqual(json.loads((out / 'audio-qa-report.json').read_text())['audio_sha256'], report['audio_sha256'])
            with self.assertRaises(FileExistsError):
                inspect(source, script, out)


if __name__ == '__main__':
    unittest.main()
