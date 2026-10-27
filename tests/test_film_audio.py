import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from mechanical_video.film_audio import caption_lines,prepare_audio
from mechanical_video.voiceover import duration

class FilmAudioTests(unittest.TestCase):
    def test_single_line_limit_counts_all_characters(self):
        self.assertEqual(caption_lines('中A1。'*5),['中A1。'*5])
        for text in ['中A1。'*5+'！','两行\n字幕','']:
            with self.assertRaisesRegex(ValueError,'at most 20'):
                caption_lines(text)
    def test_real_track_padding_and_measured_caption_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); cache=root/'cache'; cache.mkdir()
            clip=cache/'000.mp3'
            subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','sine=frequency=440:duration=0.4',str(clip)],check=True)
            measured=duration(clip)
            story={'speech_cache':str(cache),'chapters':[{'start':0,'speech_end':measured,'end':1,'narration':'电池结构为推测。'}]}
            path=root/'storyboard.json'; path.write_text(json.dumps(story))
            track=prepare_audio(path)
            self.assertAlmostEqual(duration(track),1,places=3)
            self.assertIn('电池结构为推测。',(root/'narration.zh.srt').read_text())
            self.assertIn('PlayResY: 720',(root/'captions.zh.ass').read_text())
            story['chapters'][0]['speech_end']+=.5; path.write_text(json.dumps(story))
            with self.assertRaisesRegex(ValueError,'duration changed'): prepare_audio(path)
