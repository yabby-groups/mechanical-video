"""Check real FFmpeg image-sequence timing at preview and production rates."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image


class ImageSequenceTimingTest(unittest.TestCase):
    def encode_and_read(self, preview):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            values = [25, 55, 85, 115, 145, 175]
            for i, value in enumerate(values):
                number = 1 + i*(2 if preview else 1)
                Image.new('L', (16, 16), value).save(folder/f'{number:06}.png')
            source = (['-framerate', '15', '-pattern_type', 'glob', '-i', str(folder/'*.png')]
                      if preview else ['-framerate', '30', '-start_number', '1', '-i', str(folder/'%06d.png')])
            video = folder/'test.mkv'
            subprocess.run(['ffmpeg', '-v', 'error'] + source +
                           ['-r', '30', '-c:v', 'ffv1', '-pix_fmt', 'gray', str(video)], check=True)
            raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(video),
                                           '-f', 'rawvideo', '-pix_fmt', 'gray', '-'])
            return [raw[i] for i in range(0, len(raw), 16*16)]

    def test_preview_duplicates_each_sample_once(self):
        self.assertEqual(self.encode_and_read(True), [v for v in (25, 55, 85, 115, 145, 175) for _ in range(2)])

    def test_production_keeps_every_frame_once(self):
        self.assertEqual(self.encode_and_read(False), [25, 55, 85, 115, 145, 175])


if __name__ == '__main__':
    unittest.main()
