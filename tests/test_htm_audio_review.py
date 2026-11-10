"""Acoustic/provenance/qualification regression tests; not listening acceptance."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import wave
import os

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
    def test_fingerprint_cache_invalidates_same_size_edit_with_restored_mtime(self):
        from mechanical_video.htm_audio_features import sha
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'data';path.write_bytes(b'abcd');before=path.stat();first=sha(path)
            self.assertEqual(first,sha(path))
            path.write_bytes(b'abce');os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
            self.assertNotEqual(first,sha(path))
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


class DevelopmentQualificationTest(unittest.TestCase):
    def test_development_result_can_never_qualify(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'development.json';path.write_text(json.dumps({'split':'development'}))
            with self.assertRaisesRegex(ValueError,'development results'):
                qualification(path,Path(d)/'model',Path(d)/'cal.json')


class RecognizedTimingTest(unittest.TestCase):
    def test_ctc_blank_separates_repeated_tokens(self):
        from mechanical_video.speech_alignment import recognized_units
        class Tokenizer:
            all_special_ids=[0,3]
            def decode(self,ids,group_tokens=False):return {0:'',1:'甲',2:'乙',3:'<unk>'}[ids[0]]
        ids=np.array([1,1,0,1,2,2,3]);p=np.log(np.full((7,4),.8))
        units=recognized_units(ids,p,Tokenizer(),.02,.001,.2)
        self.assertEqual(''.join(u['text'] for u in units),'甲甲乙')
        self.assertAlmostEqual(units[1]['start'],.061)
        self.assertAlmostEqual(units[0]['confidence'],.8)
        with self.assertRaisesRegex(ValueError,'invalid actual CTC'):
            recognized_units(ids,p,Tokenizer(),0,0,.2)

    def test_asr_difference_uses_recognized_time_and_stays_uncertain(self):
        from mechanical_video.htm_audio_review import text_candidates
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);script=root/'script.txt';script.write_text('甲乙')
            evidence=dict(transcript='甲乙',greedy_transcript='甲丙',
                characters=[dict(text='甲',start=0.,end=.1),dict(text='乙',start=.1,end=.2)],
                recognition_units=[dict(text='甲',start=.5,end=.6,confidence=.9),dict(text='丙',start=.7,end=.8,confidence=.95)])
            path=root/'asr.json';path.write_text(json.dumps(evidence))
            candidates,status=text_candidates(script,path,1.)
            self.assertEqual(status,'UNQUALIFIED')
            self.assertEqual(candidates[0]['start'],.7)
            self.assertEqual(candidates[0]['end'],.8)
            self.assertIn('actual recognized',candidates[0]['timing'])
            self.assertIsNone(candidates[0]['confidence'])
            self.assertFalse(candidates[0]['actionable'])
            self.assertFalse(candidates[0]['automatic_generation'])
            self.assertEqual(candidates[0]['recognition_confidence'],.95)
            evidence['recognition_units'][1]['end']=.4;path.write_text(json.dumps(evidence))
            with self.assertRaisesRegex(ValueError,'invalid actual recognition'):
                text_candidates(script,path,1.)


class CorpusTest(unittest.TestCase):
    def make_dataset(self, root):
        cases = []
        for n, split in enumerate(('train', 'calibration', 'test')):
            audio, script = root/f'{n}.wav', root/f'{n}.txt'
            wav(audio, .2*np.sin(np.arange(1600)*(n+1)*.1)); script.write_text(f'机械{n}')
            cases.append(dict(id=str(n), split=split, recording_id=str(n), speaker_id=str(n),
                              license='CC0-original-fixture', provenance='procedural isolated test',
                              audio=ref(audio), script=ref(script), labels=[],
                              negative_kinds=['clipping','noise','pause','splice','pace','masking'],
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

    def test_unknown_dimensions_not_trained_as_negatives(self):
        from mechanical_video.htm_audio_model import supervised_dimensions, acoustic_normal
        case=dict(labels=[dict(kind='clipping',start=0,end=1)],negative_kinds=['pace'])
        self.assertEqual(supervised_dimensions(case),{'clipping','pace'})
        self.assertEqual(supervised_dimensions(dict(labels=[])),set())
        self.assertFalse(acoustic_normal(dict(labels=[])))
        self.assertFalse(acoustic_normal(dict(labels=[],negative_kinds=['clipping'])))
        self.assertTrue(acoustic_normal(dict(labels=[],negative_kinds=['clipping','noise','pause','splice','pace','masking'])))
        from mechanical_video.htm_audio_review import summarize
        from mechanical_video.htm_audio_model import DIMENSIONS
        review=dict(dimensions={k:dict(candidate_intervals=[],predicted_quality=.5) for k in DIMENSIONS},
                    baseline={k:[] for k in DIMENSIONS},tracks={})
        rows=summarize([dict(case=dict(labels=[],negative_kinds=[],recording_id='r',split='test'),review=review)])
        self.assertTrue(all(row['normal_count']==0 for row in rows.values()))

    def test_contradictory_negative_labels_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path,cases=self.make_dataset(root)
            cases[0].update(labels=[dict(kind='clipping',start=0,end=.08)],negative_kinds=['clipping'])
            path.write_text(json.dumps({'cases':cases}))
            with self.assertRaisesRegex(ValueError,'contradictory'):
                load_dataset(path)

    def test_cross_defect_detector_cannot_qualify(self):
        row=dict(defect_count=60,normal_count=60,recall=1.,false_positive_rate=0.,
                 independent_test_groups=True,htm_gain=1.,subjective=False,supported=True,
                 known_negative_count=60,cross_defect_false_positive_rate=1.)
        self.assertFalse(eligible(row))
        row['cross_defect_false_positive_rate']=0.
        self.assertTrue(eligible(row))

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
                 independent_test_groups=True,htm_gain=.1,subjective=False,supported=True,
                 known_negative_count=50,cross_defect_false_positive_rate=0.)
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
            frozen_cases=path.read_text()
            unknown=copy.deepcopy(cases)
            for item in unknown:
                item['negative_kinds']=[]
            path.write_text(json.dumps({'cases':unknown}))
            with self.assertRaisesRegex(ValueError,'cold start'):
                train(path,root/'unknown-model',build,epochs=1)
            self.assertFalse((root/'unknown-model').exists())
            path.write_text(frozen_cases)
            model=root/'model'; train(path,model,build,epochs=1)
            cal=root/'cal.json'; calibrate(path,model,cal)
            case=next(c for c in cases if c['split']=='test')
            report=evaluate(case['audio']['path'],case['script']['path'],model,cal)
            with patch('mechanical_video.htm_audio_review.qualification',return_value={'pace'}):
                missing=evaluate(case['audio']['path'],case['script']['path'],model,cal)
                self.assertEqual(missing['dimensions']['pace']['status'],'UNQUALIFIED')
            report_path=root/'report.json'; write_new(report_path,report)
            self.assertEqual(validate_report(report_path)['status'],'UNQUALIFIED')
            # The second call takes the cache path and must still bind every
            # calibration dependency, including an audio file changed in place.
            from mechanical_video.htm_audio_review import load_calibration
            load_calibration(cal,model)
            dependency=Path(next(c for c in cases if c['split']=='calibration')['audio']['path'])
            original_bytes=dependency.read_bytes()
            dependency.write_bytes(original_bytes+b'changed')
            with self.assertRaisesRegex(ValueError,'stale evidence'):
                load_calibration(cal,model)
            dependency.write_bytes(original_bytes)
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
