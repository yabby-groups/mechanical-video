"""Receipt/resume contract tests. Fake CTC fixtures do not prove listening."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_htm_audio_review as fixtures
from mechanical_video.htm_audio_alignment import align_corpus
from mechanical_video.htm_audio_features import ref
from mechanical_video.speech_alignment import normalize


class FakeCTC:
    calls = 0

    def align(self, audio, text):
        self.calls += 1
        units = normalize(text)
        return dict(method='forced_alignment', audio=ref(audio), transcript=text, duration=.1,
                    characters=[dict(text=c, start=i*.1/len(units), end=min(.1,(i+1)*.1/len(units)), confidence=.9)
                                for i,c in enumerate(units)])


class AlignmentCorpusTest(unittest.TestCase):
    def setup_corpus(self, root):
        corpus, cases = fixtures.CorpusTest().make_dataset(root)
        model = root/'asr'; model.mkdir(); (model/'weights.bin').write_bytes(b'unit-test-model')
        return corpus, cases, model, root/'measured'

    def test_completed_resume_does_not_repeat_inference_and_binds_model(self):
        with tempfile.TemporaryDirectory() as d:
            corpus,cases,model,output=self.setup_corpus(Path(d));engine=FakeCTC()
            with patch('mechanical_video.htm_audio_alignment.CTCAligner',return_value=engine) as factory, \
                 patch('mechanical_video.htm_audio_alignment.importlib.metadata.version',return_value='test-only'):
                result=align_corpus(corpus,output,model,'test-revision')
                self.assertEqual(engine.calls,3)
                self.assertEqual(len(json.loads(result.read_text())['cases']),3)
                align_corpus(corpus,output,model,'test-revision',resume=True)
                self.assertEqual(engine.calls,3);self.assertEqual(factory.call_count,1)
                (model/'weights.bin').write_bytes(b'changed-model')
                with self.assertRaisesRegex(ValueError,'existing alignment job differs'):
                    align_corpus(corpus,output,model,'test-revision',resume=True)

    def test_resume_rejects_changed_output_and_changed_case_set(self):
        with tempfile.TemporaryDirectory() as d:
            corpus,cases,model,output=self.setup_corpus(Path(d))
            with patch('mechanical_video.htm_audio_alignment.CTCAligner',return_value=FakeCTC()), \
                 patch('mechanical_video.htm_audio_alignment.importlib.metadata.version',return_value='test-only'):
                result=align_corpus(corpus,output,model,'test-revision')
                alignment=Path(json.loads(result.read_text())['cases'][0]['alignment']['path'])
                original=alignment.read_bytes();alignment.write_bytes(original+b' ')
                with self.assertRaisesRegex(ValueError,'receipt fingerprint'):
                    align_corpus(corpus,output,model,'test-revision',resume=True)
                alignment.write_bytes(original)
                corpus.write_text(json.dumps({'cases':cases[:-1]}))
                with self.assertRaisesRegex(ValueError,'existing alignment job differs'):
                    align_corpus(corpus,output,model,'test-revision',resume=True)

    def test_failure_keeps_case_required_on_resume(self):
        with tempfile.TemporaryDirectory() as d:
            corpus,cases,model,output=self.setup_corpus(Path(d));engine=FakeCTC()
            original=engine.align
            def fail_second(audio,text):
                if engine.calls==1:raise ValueError('simulated CTC failure')
                return original(audio,text)
            with patch('mechanical_video.htm_audio_alignment.CTCAligner',return_value=engine), \
                 patch('mechanical_video.htm_audio_alignment.importlib.metadata.version',return_value='test-only'), \
                 patch.object(engine,'align',side_effect=fail_second):
                with self.assertRaisesRegex(ValueError,'simulated CTC failure'):
                    align_corpus(corpus,output,model,'test-revision')
            self.assertFalse((output/'dataset.json').exists())
            with patch('mechanical_video.htm_audio_alignment.CTCAligner',return_value=engine), \
                 patch('mechanical_video.htm_audio_alignment.importlib.metadata.version',return_value='test-only'):
                result=align_corpus(corpus,output,model,'test-revision',resume=True)
                self.assertEqual(engine.calls,3)
                self.assertEqual(len(json.loads(result.read_text())['cases']),3)


if __name__ == '__main__':
    unittest.main()
