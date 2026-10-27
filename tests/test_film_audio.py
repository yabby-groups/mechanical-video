import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from mechanical_video.film_audio import caption_lines,prepare_audio
from mechanical_video.voiceover import duration

class FilmAudioTests(unittest.TestCase):
    def test_punctuation_does_not_start_caption_line(self):
        text='这是一把充电式电钻。我们用照片建立了五十六个独立零件，接下来分层观察装配关系。'
        lines=caption_lines(text)
        self.assertEqual(''.join(lines),text)
        self.assertTrue(all(line[0] not in '，。；：！？、' for line in lines))
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
