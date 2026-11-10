"""Rhythm timing, leakage, ablation and frozen-inference checks; not listening QA."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from mechanical_video import htm_audio_rhythm as r
from mechanical_video.htm_audio_features import ref


def sample_features():
    return dict(features=[[6.,6.,.8,.05,.1,.04,0.,180.,20.,-20.,2.,.8]]*8,
                intervals=[[i*.5,(i+1)*.5] for i in range(8)],valid=[True]*8,
                windows=[[i*.5,i*.5+2] for i in range(8)],duration=4.,coverage_fraction=1.)


class TimingTest(unittest.TestCase):
    def test_measured_window_and_decision_coverage(self):
        f=dict(duration=4.2,intervals=[[i*.02,(i+1)*.02] for i in range(210)],
               features=[[ -20, .1,0,0,0,0,180,.8,0,0,0,0,0,0,0,0]]*210)
        chars=[dict(start=i*.2,end=i*.2+.08,confidence=.9) for i in range(20)]
        value=r.window_features(f,chars)
        self.assertEqual(value['intervals'][0][0],0)
        self.assertEqual(value['intervals'][-1][1],4.2)
        self.assertAlmostEqual(sum(b-a for a,b in value['intervals']),4.2)
        self.assertTrue(all(b==c for (a,b),(c,d) in zip(value['intervals'],value['intervals'][1:])))
        self.assertEqual(value['coverage_fraction'],1.)
        low=r.window_features(f,[dict(c,confidence=.1) for c in chars])
        self.assertEqual(low['coverage_fraction'],0.)
        self.assertEqual(value['features'][0][0],5.)

    def test_uncertain_boundary_not_normal(self):
        case=dict(labels=[dict(kind='pace',start=.4,end=1.2)])
        self.assertIsNone(r.labels(case,[0,1],'pause'))
        self.assertEqual(r.labels(case,[0,1],'pace'),1)
        self.assertIsNone(r.labels(case,[1,2],'pace'))
        self.assertEqual(r.labels(case,[2,3],'pace'),0)

    def test_missing_alignment_has_no_synthetic_zero_rate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a';p.write_text('placeholder')
            value=r.features(dict(audio=ref(p),script=ref(p)))
            self.assertEqual(value['features'],[])
            self.assertEqual(value['coverage_fraction'],0)
            self.assertIn('missing',value['uncovered'])

    def test_iou_rejects_whole_clip_alarm(self):
        self.assertLess(r.iou([0,10],[4,5]),.5)
        self.assertEqual(r.spans([.9,None,.9],[[0,.5],[.5,1],[1,1.5]],.5),[[0,.5],[1,1.5]])

    def test_calibration_cannot_silently_override_build(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'manifest.json').write_text('{}')
            p=root/'calibration.json';p.write_text(json.dumps(dict(model=ref(root/'manifest.json'),implementation=[])))
            with self.assertRaisesRegex(ValueError,'build'): r.calibration(p,root)


class QualificationTest(unittest.TestCase):
    def observations(self, count=60):
        result=[]
        for i in range(count):
            for positive in (True,False):
                c=dict(recording_id=str(i),negative_kinds=[] if positive else ['pace'],
                       labels=[dict(kind='pace',subtype='global_fast',start=0,end=4)] if positive else [])
                p={m:dict(pace=[float(positive)]*8,pause=[0.]*8) for m in r.METHODS}
                result.append((c,sample_features(),p))
        return result

    def test_tied_perfect_baseline_has_no_htm_gain(self):
        observations=self.observations()
        thresholds={m:{k:.5 for k in r.KINDS} for m in r.METHODS}
        result=r.summarize(observations,thresholds,'test')['pace']
        self.assertEqual(result['methods']['htm']['recall'],1.)
        self.assertEqual(result['gain']['rules']['ci95'],[0.,0.])
        self.assertEqual(result['status'],'UNQUALIFIED')

    def test_controlled_pass_requires_real_gain_and_cross_defect_support(self):
        observations=self.observations()
        for c,f,p in observations:
            for method in ('rules','no_tm'): p[method]['pace']=[0.]*8
        for i in range(60):
            c=dict(recording_id=str(i),negative_kinds=['pace'],labels=[dict(kind='noise',start=0,end=4)])
            p={m:dict(pace=[0.]*8,pause=[0.]*8) for m in r.METHODS}
            observations.append((c,sample_features(),p))
        thresholds={m:{k:.5 for k in r.KINDS} for m in r.METHODS}
        result=r.summarize(observations,thresholds,'test')
        self.assertEqual(result['pace']['status'],'PASS')
        self.assertEqual(result['pace/global_fast']['status'],'PASS')
        self.assertEqual(r.summarize(observations,thresholds,'development')['pace']['status'],'UNQUALIFIED')

    def test_duplicates_are_one_group_and_missing_coverage_fails(self):
        observations=self.observations(2)
        c,f,p=copy.deepcopy(observations[0]);f['coverage_fraction']=.5
        observations.append((c,f,p))
        g=r.grouped(observations,'htm','pace',.5)
        self.assertEqual(len(g[0]),2)
        self.assertFalse(g[0]['0'])
        self.assertFalse(g[3])

    def test_paired_bootstrap_and_development_cannot_qualify(self):
        a=({str(i):True for i in range(60)},{str(i):False for i in range(60)},{})
        b=({str(i):False for i in range(60)},{str(i):False for i in range(60)},{})
        self.assertEqual(r.gain_interval(a,b),[1.,1.])
        obs=self.observations(2)
        th={m:{k:.5 for k in r.KINDS} for m in r.METHODS}
        self.assertTrue(all(v['status']=='UNQUALIFIED' for v in r.summarize(obs,th,'development').values()))


try:
    from htm.bindings.algorithms import SpatialPooler
    NATIVE=True
except ImportError:
    NATIVE=False


@unittest.skipUnless(NATIVE,'official native HTM environment required')
class NativeTest(unittest.TestCase):
    def test_frozen_sequences_reset_without_learning(self):
        engine=r.RhythmEngine();f=sample_features()
        engine.sequence(f,learn=True)
        engine.sequence(f,case=dict(labels=[],negative_kinds=list(r.KINDS)))
        engine.sequence(f,case=dict(labels=[dict(kind='pace',start=0,end=4)],negative_kinds=['pause']))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);engine.save(root)
            before={p.name:p.read_bytes() for p in root.iterdir()}
            engine._frozen_directory = root
            engine._frozen_files = {p.name:r.sha(p) for p in root.iterdir()}
            a=engine.sequence(f)
            engine.sequence(dict(f,features=[v[::-1] for v in f['features']]))
            b=engine.sequence(f)
            self.assertEqual(a,b)
            # Inference must not rewrite the frozen checkpoint. SP runtime
            # counters may change in memory even when learning is disabled.
            self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})
            self.assertEqual(set(a),{'htm','no_tm','anomaly'})
            (root/'htm-pace.bin').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'changed between recordings'):
                engine.sequence(f)

    def test_invalid_windows_never_train(self):
        engine=r.RhythmEngine();f=sample_features();f['valid']=[False]*8
        p=engine.sequence(f,learn=True,case=dict(labels=[],negative_kinds=list(r.KINDS)))
        self.assertEqual(p['htm']['pace'],[None]*8)
        self.assertEqual(p['no_tm']['pause'],[None]*8)


class EntryTest(unittest.TestCase):
    def test_explicit_rhythm_dispatch_preserves_default_acoustic_entry(self):
        from mechanical_video.htm_audio_entry import main
        with patch('sys.argv',['htm_audio_review','--engine','rhythm','train','--help']), \
             patch.object(r,'main',return_value=0) as rhythm:
            self.assertEqual(main(),0)
            rhythm.assert_called_once_with(['train','--help'])
        with patch('sys.argv',['htm_audio_review','train','--help']), \
             patch('mechanical_video.htm_audio_review.main',return_value=0) as acoustic:
            self.assertEqual(main(),0)
            acoustic.assert_called_once_with()


class RecoveryTest(unittest.TestCase):
    def test_feature_cache_reuse_and_corruption(self):
        import wave
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);audio=root/'a.wav';script=root/'a.txt';alignment=root/'a.json'
            with wave.open(str(audio),'wb') as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
                f.writeframes((5000*np.sin(np.arange(64000)*.08)).astype('<i2').tobytes())
            script.write_text('字'*20)
            alignment.write_text(json.dumps(dict(method='forced_alignment',audio=ref(audio),duration=4.,
                transcript='字'*20,characters=[dict(text='字',start=i*.2,end=i*.2+.08,confidence=.9) for i in range(20)])))
            case=dict(audio=ref(audio),script=ref(script),alignment=ref(alignment))
            first=r.features(case,root/'cache')
            with patch.object(r,'extract',side_effect=AssertionError('duplicate decode')):
                self.assertEqual(first,r.features(case,root/'cache'))
            target=next(p for p in (root/'cache').glob('*.json') if not p.name.endswith('.receipt.json'))
            value=json.loads(target.read_text());value['result']['coverage_fraction']=0.
            target.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'stale evidence'): r.features(case,root/'cache')

    def test_completed_experiment_resume_does_not_repeat_blind_inference(self):
        from scripts.run_htm_rhythm_experiment import run
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);dataset=root/'data.json';build=root/'build.json'
            dataset.write_text('{}');build.write_text('{}');output=root/'run'
            def train(data,model,*args):
                model.mkdir();(model/'manifest.json').write_text('{}')
            def calibrate(data,model,path,*args):
                if path: r.write(path,{})
                return {}
            def benchmark(data,model,cal,target,**kwargs):
                binding=dict(dataset=ref(data),model=ref(model/'manifest.json'),calibration=ref(cal),implementation=r.implementation())
                r.write(target.with_suffix('.lock.json'),binding)
                result=dict(status='UNQUALIFIED',dimensions={})
                r.write(target,result);return result
            with patch.object(r,'train',side_effect=train), patch.object(r.RhythmEngine,'load',return_value=(None,{})), \
                 patch.object(r,'partition',return_value=[]), patch.object(r,'calibrate',side_effect=calibrate), \
                 patch.object(r,'benchmark',side_effect=benchmark) as inference:
                run(dataset,build,output)
                run(dataset,build,output,resume=True)
                self.assertEqual(inference.call_count,1)
                (output/'benchmark.json.receipt.json').unlink()
                with self.assertRaisesRegex(ValueError,'lacks receipt'): run(dataset,build,output,resume=True)


if __name__=='__main__': unittest.main()
