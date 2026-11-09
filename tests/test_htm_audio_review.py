"""Acoustic/provenance/qualification regression tests; not listening acceptance."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import wave

import numpy as np

from mechanical_video.htm_audio_features import extract, ref, encode, FEATURES
from mechanical_video.htm_audio_model import load_dataset, Engine
from mechanical_video.htm_audio_review import eligible, spans, spearman, wilson, qualification


def wav(path, samples, rate=16000):
    samples = np.asarray(samples)
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1 if samples.ndim == 1 else samples.shape[1])
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes((np.clip(samples, -1, 1)*32767).astype('<i2').tobytes())


class FeaturesTest(unittest.TestCase):
    def test_stereo_cancellation_does_not_hide_clipping(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'stereo.wav'
            x = np.sign(np.sin(np.arange(321)*.3))
            wav(path, np.column_stack([x, -x]), 48000)
            f = extract(path)
            self.assertGreater(f['raw_amplitude']['clipped_fraction'], .9)
            self.assertGreater(f['raw_amplitude']['peak'], .99)
            self.assertEqual(f['coverage']['sample_rate'], 48000)
            self.assertEqual(f['coverage']['source_samples'], 321)
            self.assertEqual(f['coverage']['samples_consumed'], 321)
            self.assertAlmostEqual(f['intervals'][-1, 1], 321/48000)

    def test_pitch_and_partial_final_frame(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'tone.wav'
            wav(path, .3*np.sin(2*np.pi*200*np.arange(16001)/16000))
            f = extract(path)
            self.assertEqual(len(f['features']), 51)
            self.assertAlmostEqual(float(np.median(f['features'][:-3, 6])), 200, delta=8)
            self.assertTrue(np.isfinite(f['features']).all())
            active = encode(f['features'][0])
            self.assertEqual(len(active), len(FEATURES)*5)
            self.assertEqual(len(set(active)), len(active))

    def test_stale_alignment_and_bad_intervals_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); audio = root/'a.wav'; alignment = root/'a.json'
            wav(audio, np.zeros(1600))
            data = dict(method='forced_alignment', audio=ref(audio), duration=.1,
                        transcript='字', characters=[dict(text='字', start=.08, end=.07, confidence=.8)])
            alignment.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'invalid measured'):
                extract(audio, alignment)
            data['audio']['sha256'] = 'bad'
            alignment.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'bind the actual'):
                extract(audio, alignment)

    def test_temporal_spans_and_normal_pause_control(self):
        intervals = np.asarray([[i*.02, (i+1)*.02] for i in range(10)])
        self.assertEqual(spans([0,1,1,1,0,0,1,0,0,0], intervals, .5), [[.02,.08]])
        self.assertEqual(spans([1]*10, intervals, .5, minimum_seconds=1.), [])

    def test_paired_features_use_actual_stem_and_mix(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); voice=root/'voice.wav'; mix=root/'mix.wav'
            x=.15*np.sin(2*np.pi*220*np.arange(3200)/16000)
            wav(voice,x); wav(mix,x+.6*np.sin(2*np.pi*360*np.arange(3200)/16000))
            f=extract(mix,narration_track=voice,mix_track=mix)
            self.assertTrue(np.all(f['features'][:,13] == 1))
            self.assertLess(float(np.median(f['features'][:,14])),.6)
            self.assertGreater(float(np.median(f['features'][:,15])),5)
            with self.assertRaisesRegex(ValueError,'actual evaluated audio'):
                extract(mix,narration_track=voice,mix_track=voice)


class CorpusTest(unittest.TestCase):
    def make_dataset(self, root):
        cases = []
        for n, split in enumerate(('train', 'calibration', 'test')):
            audio, script = root/f'{n}.wav', root/f'{n}.txt'
            wav(audio, .2*np.sin(np.arange(1600)*(n+1)*.1)); script.write_text(f'机械{n}')
            cases.append(dict(id=str(n), split=split, recording_id=str(n), speaker_id=str(n),
                              license='CC0-original-fixture', provenance='procedural isolated test',
                              audio=ref(audio), script=ref(script), labels=[],
                              label_source='synthetic_fixture', labeler='fixture', producer='fixture'))
        p = root/'corpus.json'; p.write_text(json.dumps({'cases':cases}))
        return p, cases

    def test_recording_speaker_text_and_audio_leakage(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); path,cases=self.make_dataset(root)
            load_dataset(path)
            for field in ('recording_id', 'speaker_id', 'script', 'audio'):
                with self.subTest(field=field):
                    bad=copy.deepcopy(cases); bad[1][field]=bad[0][field]
                    path.write_text(json.dumps({'cases':bad}))
                    with self.assertRaisesRegex(ValueError, 'leakage'):
                        load_dataset(path)

    def test_subjective_synthetic_labels_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); path,cases=self.make_dataset(root)
            cases[0]['labels']=[dict(kind='expression', start=0., end=.08)]
            path.write_text(json.dumps({'cases':cases}))
            with self.assertRaisesRegex(ValueError, 'independent quality'):
                load_dataset(path)

    def test_no_metrics_only_qualification(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); model=root/'model'; model.mkdir()
            (model/'manifest.json').write_text('{}'); cal=root/'cal.json'; cal.write_text('{}')
            from mechanical_video import htm_audio_review as module
            fake=dict(model=ref(model/'manifest.json'),calibration=ref(cal),adapter=ref(module.__file__),
                      evidence=[], cases=[], dimensions={})
            p=root/'benchmark.json'; p.write_text(json.dumps(fake))
            with self.assertRaisesRegex(ValueError, 'held-out case'):
                qualification(p,model,cal)

    def test_sample_floor_gain_subjective_and_confidence_intervals(self):
        row=dict(defect_count=49,normal_count=50,recall=.98,false_positive_rate=.02,
                 independent_test_groups=True,htm_gain=.1,subjective=False,supported=True)
        self.assertFalse(eligible(row)); row['defect_count']=50
        self.assertTrue(eligible(row)); row['htm_gain']=0
        self.assertFalse(eligible(row)); row['htm_gain']=.1; row['subjective']=True
        row.update(independent_ratings=50, spearman=.69)
        self.assertFalse(eligible(row)); row['spearman']=.7
        self.assertTrue(eligible(row)); row['supported']=False
        self.assertFalse(eligible(row))
        self.assertAlmostEqual(spearman([1,2,2,4],[2,4,4,8]),1.)
        self.assertIsNone(spearman([1,1,1],[1,2,3]))
        lo,hi=wilson(50,50); self.assertGreater(lo,.9); self.assertAlmostEqual(hi,1.)


try:
    import htm.bindings.algorithms
    HTM = True
except ImportError:
    HTM = False


@unittest.skipUnless(HTM, 'run in isolated source-built HTM environment')
class ActualHTMTest(unittest.TestCase):
    def test_actual_checkpoint_calibration_and_report_reject_tampering(self):
        from unittest.mock import patch
        from mechanical_video.htm_audio_model import train, runtime, SOURCE_REVISION
        from mechanical_video.htm_audio_review import calibrate, evaluate, write_new
        from mechanical_video.htm_audio_bridge import validate_report
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); path,cases=CorpusTest().make_dataset(root)
            for original in list(cases):
                wav(original['audio']['path'],.2*np.sin(np.arange(16000)*(int(original['id'])+1)*.1))
                original['audio']=ref(original['audio']['path'])
                duplicate=copy.deepcopy(original); duplicate['id']+='-second'; duplicate['recording_id']+='-second'
                audio=root/(duplicate['id']+'.wav'); script=root/(duplicate['id']+'.txt')
                wav(audio,.2*np.sin(np.arange(16000)*(int(original['id'])+1)*.13))
                script.write_text('独立测试'+duplicate['id'])
                duplicate.update(audio=ref(audio),script=ref(script)); cases.append(duplicate)
            path.write_text(json.dumps({'cases':cases}))
            build=root/'build.json'; write_new(build,dict(source_revision=SOURCE_REVISION,bindings=runtime()['bindings']))
            model=root/'model'; train(path,model,build,epochs=1)
            cal=root/'cal.json'; calibrate(path,model,cal)
            case=next(c for c in cases if c['split']=='test')
            report=evaluate(case['audio']['path'],case['script']['path'],model,cal)
            report_path=root/'report.json'; write_new(report_path,report)
            self.assertEqual(validate_report(report_path)['status'],'UNQUALIFIED')
            actual_cal=json.loads(cal.read_text())
            fake_cal=copy.deepcopy(actual_cal); fake_cal['cases']=['test-only-forged-calibration']
            cal.write_text(json.dumps(fake_cal))
            with self.assertRaisesRegex(ValueError,'calibration-only'):
                evaluate(case['audio']['path'],case['script']['path'],model,cal)
            cal.write_text(json.dumps(actual_cal,indent=2)+'\n')
            bad=copy.deepcopy(report); bad['status']='REWORK'; bad['dimensions']['clipping']['status']='REWORK'
            report_path.write_text(json.dumps(bad))
            with patch('mechanical_video.htm_audio_bridge.qualification',return_value={'clipping'}):
                # A fixture qualification cannot turn missing defects into PASS.
                bad['qualification']=ref(cal); report_path.write_text(json.dumps(bad))
                with self.assertRaisesRegex(ValueError,'REWORK requires'):
                    validate_report(report_path)
            report_path.write_text(json.dumps(report))
            manifest_path=model/'manifest.json'; original_manifest=manifest_path.read_text()
            incomplete=json.loads(original_manifest); del incomplete['files']['noise.bin']
            manifest_path.write_text(json.dumps(incomplete))
            with self.assertRaisesRegex(ValueError,'every required component'):
                Engine.load(model)
            manifest_path.write_text(original_manifest)
            with (model/'sp.bin').open('ab') as stream: stream.write(b'corrupt')
            with self.assertRaisesRegex(ValueError,'checkpoint fingerprint'):
                validate_report(report_path)

    def test_official_pipeline_and_frozen_replay(self):
        engine=Engine()
        f=np.zeros((120,len(FEATURES)))
        f[:,0]=-20; f[:,1]=.3; f[:,6]=200; f[:,7]=.8
        engine.sequence(f,learn=True)
        engine.sequence(f,labels=[{'noise'}]*120)
        with tempfile.TemporaryDirectory() as d:
            engine.save(d)
            from htm.bindings.algorithms import TemporalMemory
            tm=TemporalMemory(); tm.loadFromFile(str(Path(d)/'tm.bin'),'BINARY')
            first=engine.sequence(f)
            second=engine.sequence(f)
            self.assertEqual(first,second)
            self.assertGreater(first[-1]['probabilities']['noise'],.5)


if __name__ == '__main__':
    unittest.main()
