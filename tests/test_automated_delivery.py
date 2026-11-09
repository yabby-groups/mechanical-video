"""Workflow contract regressions. Fixture agents/media are not perceptual evidence."""
import json
import shutil
from pathlib import Path
import tempfile
import unittest
from test_review_benchmark import benchmark_fixture
from unittest.mock import patch
from mechanical_video import repair_controller as rc, production_run, production_gate


class AutomatedDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name); self.path=self.base/'director-record.json'
        self.path.write_text('{}')
        proof=self.base/'fixture-proof';proof.write_text('Synthetic scheduler fixture, not media acceptance')
        self.evidence={str(proof):rc._sha(proof)}
        self.benchmark=self.base/'fixture-benchmark.json'
        self.benchmark.write_text(json.dumps(benchmark_fixture(self.base)))
        self.bench=dict(adapter='fixture-adapter',detected=['action_contradiction','occlusion','speech_desync'],
                        evidence={str(self.benchmark):rc._sha(self.benchmark)})

    def test_review_draft_never_launches_delivery_process(self):
        command=['must-not-run']
        self.path.write_text(json.dumps({'production_checks':{'schema_version':5,
            'execution':{'delivery':command},'content_review':{'execution':{'delivery':command}}}}))
        with patch.object(production_run,'evaluate',return_value={'status':'REVIEW_DELIVERY','reasons':[]}), \
             patch.object(production_run.subprocess,'run') as launch:
            result,code=production_run.run(self.path,'delivery',command)
        self.assertEqual(code,1);self.assertEqual(result['status'],'BLOCKED');launch.assert_not_called()

    def test_v5_review_delivery_is_not_a_successful_exit(self):
        self.path.write_text(json.dumps({'production_checks':{'schema_version':5,'delivery_mode':'review'}}))
        result=production_gate.evaluate(json.loads(self.path.read_text()),self.base,'delivery')
        self.assertEqual(result['status'],'BLOCKED')
        self.assertTrue(any('automated delivery requires formal' in r for r in result['reasons']))

    def test_automated_acceptance_requires_dispatched_continuous_review(self):
        import copy
        from mechanical_video.perceptual_review import MODALITIES, QUESTIONS
        evidence_path=next(iter(self.evidence))
        review=dict(media_sha256='final-hash',duration=1,
            reviewer=dict(id='qa',independent=True,method='continuous_av_model',tool='fixture-adapter',completed_at='fixture',
                          model_revision='synthetic-revision',runtime_fingerprint='synthetic-runtime'),
            evidence=[dict(path=evidence_path,sha256=self.evidence[evidence_path])],
            coverage={m:dict(observed=True,ranges=[[0,1]],notes='Synthetic coverage',evidence=evidence_path) for m in MODALITIES},
            answers={q:dict(time=.5,observation='Synthetic answer',verdict='clear',evidence=evidence_path) for q in QUESTIONS},issues=[])
        path=self.base/'review.json'
        def record_for(data):
            path.write_text(json.dumps(data))
            ref=dict(path=str(path),sha256=rc._sha(path))
            return dict(production_checks=dict(required_interval=[0,1],assets=dict(perceptual_review=ref,final_media=dict(sha256='final-hash'))),
                repair_controller=dict(capabilities=['continuous_av','audio'],tasks={'render':dict(stage='render',agent_id='producer'),
                    'qa':dict(stage='independent-post-review',status='done',agent_id='qa',result=dict(evidence={str(path):ref['sha256']}))},
                    capability_benchmarks={name:self.bench for name in ('continuous_av','audio')}))
        self.assertEqual(production_gate.automated_review_errors(record_for(review),self.base),[])
        for mutate in (lambda r:r['reviewer'].update(method='realtime_av_playback'),
                       lambda r:r['reviewer'].update(tool='untested-adapter'),
                       lambda r:r['reviewer'].update(model_revision='changed-model'),
                       lambda r:r['reviewer'].update(runtime_fingerprint='changed-runtime'),
                       lambda r:r['reviewer'].update(id='producer'),
                       lambda r:r['coverage']['audio'].update(observed=False),
                       lambda r:r.update(media_sha256='another-version')):
            candidate=copy.deepcopy(review);mutate(candidate)
            self.assertTrue(production_gate.automated_review_errors(record_for(candidate),self.base))
        record=record_for(review);record['repair_controller']['tasks']['qa']['result']['evidence']={}
        self.assertTrue(production_gate.automated_review_errors(record,self.base))
        record=record_for(review)
        original_benchmark=self.benchmark.read_text()
        benchmark=json.loads(original_benchmark);benchmark['model_revision']='newly-qualified-model'
        self.benchmark.write_text(json.dumps(benchmark))
        updated=dict(self.bench,evidence={str(self.benchmark):rc._sha(self.benchmark)})
        record['repair_controller']['capability_benchmarks']={name:updated for name in ('continuous_av','audio')}
        self.assertTrue(production_gate.automated_review_errors(record,self.base))
        self.benchmark.write_text(original_benchmark)
        record=record_for(review);record['production_checks']['required_interval']=[]
        self.assertTrue(production_gate.automated_review_errors(record,self.base))
        record=record_for(review);path.write_text('changed')
        self.assertTrue(production_gate.automated_review_errors(record,self.base))
