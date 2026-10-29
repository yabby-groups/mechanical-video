import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mechanical_video import remake
from mechanical_video.remake_content import selected, validate_editorial


class RemakeSafetyTests(unittest.TestCase):
    def test_editorial_hold_prevents_worker_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp); (base/'editorial-hold.json').write_text('{}')
            with patch.object(remake,'BASE',base),patch.object(remake,'queue') as queue:
                with self.assertRaisesRegex(RuntimeError,'editorial hold'): remake.worker()
                queue.assert_not_called()

    def test_only_definite_transient_rejections_can_retry(self):
        self.assertEqual(remake.rejected_status('Error: Audio provider request failed: HTTP 503'),503)
        self.assertEqual(remake.rejected_status('Error: Audio provider request failed: HTTP 429'),429)
        self.assertIsNone(remake.rejected_status('Audio provider request or response read failed'))
        self.assertIsNone(remake.rejected_status('Read timed out after 503 milliseconds'))

    def test_uncertain_submission_blocks_even_with_retry_authority(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp); script=folder/'script.md'; script.write_text('先看这里。\n')
            with patch.dict(remake.os.environ,{'OPENAI_API_KEY':'test-only'}),patch.object(remake.subprocess,'run',return_value=type('Result',(),{'returncode':1})()):
                with self.assertRaisesRegex(RuntimeError,'uncertain'):
                    remake.prepare_clips(script,folder)
            with patch.object(remake.subprocess,'run') as runner:
                with self.assertRaisesRegex(RuntimeError,'Uncertain prior speech'):
                    remake.prepare_clips(script,folder)
                runner.assert_not_called()

    def test_completed_output_hash_mismatch_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp); episode=base/'episodes/EP01'; episode.mkdir(parents=True)
            output=base/'output/EP01.mp4'; output.parent.mkdir(); output.write_bytes(b'original output')
            (episode/'validation.json').write_text(json.dumps({'passed':True,'video_sha256':'different'}))
            with patch.object(remake,'BASE',base),patch.object(remake,'audio') as audio:
                with self.assertRaises(AssertionError): remake.render(1)
                audio.assert_not_called()
            self.assertEqual(output.read_bytes(),b'original output')

    def test_source_controller_variants_are_not_shown_simultaneously(self):
        for controller in ['Spider','S6','GTR','SKR-Pro']:
            part={'path':f'/_Unsaved_/Electronics/Controllers__1_/{controller}/SOLID','group':'other'}
            self.assertFalse(selected('whole',part))
        octopus={'path':'/_Unsaved_/Electronics/Controllers__1_/Octopus/SOLID','group':'other'}
        self.assertTrue(selected('whole',octopus))

    def test_authored_season_meets_production_contract(self):
        self.assertTrue(validate_editorial())


if __name__=='__main__': unittest.main()
