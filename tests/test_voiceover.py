import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from mechanical_video.voiceover import compose, RUNNER

class VoiceoverTests(unittest.TestCase):
    def test_real_mux_timing_cache_and_no_overwrite(self):
        run=subprocess.run
        submissions=[]
        def speech_or_run(args,**kwargs):
            if len(args)>1 and args[1]==str(RUNNER):
                submissions.append(args)
                return run(['ffmpeg','-y','-v','error','-f','lavfi','-i','sine=frequency=440:duration=0.4',args[args.index('--out')+1]],check=True)
            return run(args,**kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); video=root/'silent.mp4'; script=root/'script.txt'; output=root/'中文.mp4'
            script.write_text('观察太阳轮。\n接着看行星架。',encoding='utf-8')
            run(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=s=16x16:r=30:d=2','-c:v','libx264','-pix_fmt','yuv420p',str(video)],check=True)
            with patch.dict('os.environ',{'OPENAI_API_KEY':'test-only'}),patch('mechanical_video.voiceover.subprocess.run',side_effect=speech_or_run):
                compose(video,script,output)
                self.assertEqual(len(submissions),2)
                with self.assertRaisesRegex(ValueError,'new output'): compose(video,script,output)
                output.unlink(); compose(video,script,output)
                self.assertEqual(len(submissions),2)
            data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]))
            self.assertEqual({s['codec_type'] for s in data['streams']},{'video','audio','subtitle'})
            self.assertAlmostEqual(float(data['format']['duration']),2,places=1)
            srt=next(root.glob('*.voiceover/*/narration.zh.srt')).read_text()
            self.assertIn('观察太阳轮。',srt)
            self.assertIn('00:00:01,000',srt)
