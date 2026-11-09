"""Workflow contract regressions. Fixture agents/media are not perceptual evidence."""
import json
import shutil
from pathlib import Path
import tempfile
import unittest
from test_review_benchmark import benchmark_fixture
from unittest.mock import patch
from mechanical_video import repair_controller as rc, production_run, production_gate


class WorkflowAutonomyTests(unittest.TestCase):
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

    def enable(self):
        for name in ('continuous_av','audio'):rc.capability(self.path,name,self.bench)

    def state(self):return json.loads(self.path.read_text())['repair_controller']

    def test_default_workflow_finishes_without_duplicate_reviews_or_user_steps(self):
        rc.initialize(self.path);self.enable()
        seen=set()
        for stage in rc.CHAIN:
            task=next(t for t in rc.next(self.path)['ready'] if t['id']==stage)
            review=rc._is_review(task)
            agent='qa' if review else ('/root' if task['owner']=='Director' else 'producer')
            receipt=({'agent_id':agent,'source':'active_session','role':'Director'} if agent=='/root'
                     else {'agent_id':agent,'tool_call_id':'synthetic-fixture'})
            kind='director' if agent=='/root' else ('reuse' if agent in seen else 'spawn')
            rc.claim(self.path,stage,agent,receipt,kind);seen.add(agent)
            if stage=='render':
                self.assertEqual(rc.validate_execution(json.loads(self.path.read_text()),self.base,'full-render'),[])
            # This test exercises scheduler topology, not fabricated media acceptance.
            with patch.object(production_gate,'evaluate',return_value={'status':'READY'}):
                rc.complete(self.path,stage,agent,stage+'-done',checks=task['required_checks'],evidence=self.evidence)
        state=self.state()
        self.assertEqual(len(state['tasks']),8)
        self.assertEqual(state['handoffs'],16)
        self.assertEqual(rc.resume(self.path)['workflow_status'],'COMPLETE')
        self.assertEqual(rc.resume(self.path)['ready'],[])
        self.assertEqual(set(state['tasks']['independent-check']['required_checks']),
                         {'original-intent','minimal-sample','independent-check'})
        self.assertIn('measured-narration-timeline',state['tasks']['preflight']['required_checks'])
        self.assertIn('render',state['tasks']['independent-post-review']['required_checks'])
        Path(next(iter(self.evidence))).write_text('changed')
        self.assertNotEqual(rc.next(self.path)['workflow_status'],'COMPLETE')

    def test_review_capability_is_checked_before_media_production(self):
        rc.initialize(self.path)
        rc.claim(self.path,'original-intent','/root',{'agent_id':'/root','source':'active_session','role':'Director'},'director')
        rc.complete(self.path,'original-intent','/root','intent',checks=['original-intent'])
        status=rc.next(self.path)
        self.assertEqual(status['workflow_status'],'DEPENDENCY_BLOCKED')
        self.assertEqual(status['dependency_owner'],'Director')
        self.assertIn('minimal-sample',status['blocked'])
        with self.assertRaises(ValueError):rc.capability(self.path,'audio',dict(adapter='fictional',detected=[]))
        self.enable()
        self.assertIn('minimal-sample',[t['id'] for t in rc.next(self.path)['ready']])
        other=self.base/'other-adapter.json'
        other.write_text(json.dumps(benchmark_fixture(self.base, 'other-adapter')))
        rc.capability(self.path,'audio',dict(adapter='other-adapter',detected=self.bench['detected'],
                                           evidence={str(other):rc._sha(other)}))
        self.assertIn('minimal-sample',rc.next(self.path)['blocked'])

    def test_legacy_capability_registration_preserves_controller_history(self):
        rc.initialize(self.path)
        record=json.loads(self.path.read_text())
        state=record['repair_controller'];state.pop('capability_benchmarks')
        state['handoffs']=7
        old_tasks=json.loads(json.dumps(state['tasks']))
        old_events=json.loads(json.dumps(state['events']))
        self.path.write_text(json.dumps(record))
        before=self.path.read_bytes()
        with self.assertRaises(ValueError):
            rc.capability(self.path,'audio',dict(adapter='failed',detected=[]))
        self.assertEqual(self.path.read_bytes(),before)
        rc.capability(self.path,'audio',self.bench)
        after=self.state()
        self.assertEqual(after['handoffs'],7)
        self.assertEqual(after['tasks'],old_tasks)
        self.assertEqual(after['events'][:-1],old_events)
        self.assertEqual(after['capability_benchmarks']['audio'],self.bench)

    def test_failed_cases_and_changed_raw_evidence_block_registration_and_resume(self):
        rc.initialize(self.path)
        report=benchmark_fixture(self.base)
        report['cases'][0]['passed']=False
        self.benchmark.write_text(json.dumps(report))
        self.bench['evidence']={str(self.benchmark):rc._sha(self.benchmark)}
        with self.assertRaisesRegex(ValueError,'failed benchmark case'):
            rc.capability(self.path,'audio',self.bench)
        self.assertNotIn('audio',self.state()['capabilities'])
        report['cases'][0]['passed']=True
        self.benchmark.write_text(json.dumps(report))
        self.bench['evidence']={str(self.benchmark):rc._sha(self.benchmark)}
        self.enable()
        Path(report['cases'][0]['raw_response']['path']).write_text('changed model answer')
        status=rc.resume(self.path)
        self.assertEqual(status['workflow_status'],'DEPENDENCY_BLOCKED')
        self.assertTrue(any('stale benchmark evidence' in e for e in status['dependency_errors']))

    def test_incomplete_review_requires_owned_internal_repair(self):
        rc.initialize(self.path,tasks=[dict(id='qa',stage='independent-check',owner='QA',
            required_checks=['contact'],inputs=self.evidence,outputs=[],capabilities=['audio'])],
            capabilities=['audio'],capability_benchmarks={'audio':self.bench})
        rc.claim(self.path,'qa','qa-agent',{'agent_id':'qa-agent','tool_call_id':'fixture'})
        with self.assertRaisesRegex(ValueError,'owned repair'):
            rc.complete(self.path,'qa','qa-agent','missing',verdict='needs-review',evidence=self.evidence)
        rc.complete(self.path,'qa','qa-agent','missing',verdict='needs-review',evidence=self.evidence,
            failures=[dict(issue_id='missing-audio',owner='Director',severity='P1',required_checks=['contact'],
                           evidence=self.evidence,repair_outputs=[],repair_capabilities=[])])
        task=self.state()['tasks']['missing-audio:repair:1']
        self.assertEqual(task['owner'],'Director')
        self.assertEqual(task['capabilities'],[])
        self.assertEqual(task['review_capabilities'],['audio'])
        self.assertIn(task['id'],[t['id'] for t in rc.next(self.path)['ready']])
        self.assertEqual(self.state()['tasks']['qa']['status'],'blocked')
        receipt={'agent_id':'/root','source':'active_session','role':'Director'}
        rc.claim(self.path,task['id'],'/root',receipt,'director')
        rc.complete(self.path,task['id'],'/root','still-incomplete',verdict='needs-review',evidence=self.evidence,
            failures=[dict(issue_id='missing-audio',owner='Director',severity='P1',required_checks=['contact'],
                           evidence=self.evidence,repair_outputs=[],repair_capabilities=[])])
        self.assertEqual(self.state()['issues']['missing-audio']['repair_attempts'],1)
        self.assertEqual(self.state()['tasks']['missing-audio:repair:2']['review_capabilities'],['audio'])

    def test_new_version_cannot_copy_controller_to_reset_dispatch(self):
        rc.initialize(self.path,tasks=[dict(id='work',stage='minimal-sample',owner='Director')])
        copy=self.base/'new-version.json';shutil.copyfile(self.path,copy)
        before=copy.read_bytes()
        for action in (lambda:rc.initialize(copy),lambda:rc.next(copy),
            lambda:rc.claim(copy,'work','/root',{'agent_id':'/root','source':'active_session','role':'Director'},'director')):
            with self.assertRaisesRegex(ValueError,'canonical'):action()
        self.assertEqual(copy.read_bytes(),before)

    def test_review_draft_cannot_complete_delivery_task(self):
        rc.initialize(self.path,tasks=[dict(id='delivery',stage='delivery',owner='Director',kind='handoff',required_checks=['delivery'])])
        rc.claim(self.path,'delivery','/root',{'agent_id':'/root','source':'active_session','role':'Director'},'director')
        with patch.object(production_gate,'evaluate',return_value={'status':'REVIEW_DELIVERY','reasons':[]}):
            with self.assertRaisesRegex(ValueError,'independent acceptance'):
                rc.complete(self.path,'delivery','/root','done',checks=['delivery'])
        self.assertEqual(self.state()['tasks']['delivery']['status'],'running')



    def test_handoff_cannot_create_unreviewed_assets(self):
        with self.assertRaisesRegex(ValueError,'unreviewed assets'):
            rc.initialize(self.path,tasks=[dict(id='delivery',stage='delivery',kind='handoff',owner='Director',outputs=['new.mp4'])])

    def test_explicit_review_must_depend_on_production(self):
        with self.assertRaisesRegex(ValueError,'depend on its producer'):
            rc.initialize(self.path,tasks=[dict(id='sample',stage='minimal-sample',owner='Producer',review_by='review'),
                dict(id='review',stage='independent-check',owner='QA')])
