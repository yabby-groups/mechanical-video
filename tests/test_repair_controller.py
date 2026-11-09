import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from mechanical_video import repair_controller as rc


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.record = self.base / 'director-record.json'
        self.record.write_text(json.dumps({'preserve': 42}))
        self.source = self.ref('source', 'original')
        self.proof = self.ref('proof', 'independent observation')

    def ref(self, name, text):
        (self.base / name).write_text(text)
        return {name: hashlib.sha256(text.encode()).hexdigest()}

    def setup(self, **kwargs):
        tasks = [dict(id='sample', stage='minimal-sample', owner='Visual',
                      inputs=self.source, outputs=['v1'], required_checks=['contact'], capabilities=['visual'])]
        rc.initialize(self.record, tasks=tasks, capabilities=kwargs.get('capabilities', ['visual']))

    def claim(self, task, agent, kind='spawn'):
        return rc.claim(self.record, task, agent, {'agent_id': agent, 'tool_call_id': agent + ':' + task}, kind)

    def produce(self):
        self.claim('sample', 'producer')
        output = self.ref('v1', 'candidate')
        rc.complete(self.record, 'sample', 'producer', 'produce', outputs=output, checks=['contact'])
        return output

    def test_failure_repair_independent_close(self):
        self.setup()
        self.produce()
        with self.assertRaises(ValueError):
            self.claim('sample:review', 'producer', 'followup')
        self.claim('sample:review', 'reviewer')
        issue = dict(issue_id='contact-gap', owner='Visual', severity='P1', required_checks=['contact'],
                     evidence=self.proof, repair_outputs=['v2'])
        rc.complete(self.record, 'sample:review', 'reviewer', 'fail', verdict='fail', failures=[issue], evidence=self.proof)
        self.claim('contact-gap:repair:1', 'producer', 'followup')
        output = self.ref('v2', 'contact corrected')
        rc.complete(self.record, 'contact-gap:repair:1', 'producer', 'repair', outputs=output,
                    checks=['contact'], improvement=True)
        self.claim('contact-gap:repair:1:review', 'reviewer', 'followup')
        rc.complete(self.record, 'contact-gap:repair:1:review', 'reviewer', 'verified',
                    checks=['contact'], evidence=self.proof)
        state = json.loads(self.record.read_text())
        self.assertEqual(state['preserve'], 42)
        issue = state['repair_controller']['issues']['contact-gap']
        self.assertEqual(issue['status'], 'closed')
        self.assertEqual(issue['repair_attempts'], 1)
        self.assertNotEqual(issue['resolution']['producer'], issue['resolution']['reviewer'])

    def test_duplicate_and_resume(self):
        self.setup()
        self.claim('sample', 'producer')
        self.assertEqual(rc.resume(self.record)['uncertain_running'], ['sample'])
        with self.assertRaises(ValueError):
            self.claim('sample', 'other')
        output = self.ref('v1', 'candidate')
        args = dict(outputs=output, checks=['contact'])
        first = rc.complete(self.record, 'sample', 'producer', 'same', **args)
        self.assertEqual(first, rc.complete(self.record, 'sample', 'producer', 'same', **args))
        with self.assertRaises(ValueError):
            rc.complete(self.record, 'sample', 'producer', 'same', checks=[])
        self.assertEqual(len(rc.next(self.record)['ready']), 1)

    def test_two_issues_require_both_independent_resolutions(self):
        self.setup(); self.produce(); self.claim('sample:review','reviewer')
        issues=[dict(issue_id=i,owner='Visual',severity='P1',required_checks=['contact'],
                     evidence=self.proof,repair_outputs=[i+'-v2']) for i in ('a','b')]
        rc.complete(self.record,'sample:review','reviewer','two-fail',verdict='fail',failures=issues)
        producer_receipt={'agent_id':'producer','tool_call_id':'batch-repair'}
        reviewer_receipt={'agent_id':'reviewer','tool_call_id':'batch-review'}
        for index,i in enumerate(('a','b')):
            task=i+':repair:1'
            rc.claim(self.record,task,'producer',producer_receipt,'followup' if index==0 else 'reuse')
            rc.complete(self.record,task,'producer',i+'fixed',outputs=self.ref(i+'-v2','fixed'),checks=['contact'])
            rc.claim(self.record,task+':review','reviewer',reviewer_receipt,'followup' if index==0 else 'reuse')
            rc.complete(self.record,task+':review','reviewer',i+'checked',checks=['contact'],evidence=self.proof)
            state=json.loads(self.record.read_text())['repair_controller']
            self.assertEqual(state['tasks']['sample:review']['status'],'blocked' if index==0 else 'done')
        self.assertEqual(set(state['tasks']['sample:review']['inputs']),{'a-v2','b-v2'})

    def test_stale_and_output_ownership(self):
        self.setup()
        self.claim('sample', 'producer')
        output = self.ref('wrong', 'candidate')
        with self.assertRaises(ValueError):
            rc.complete(self.record, 'sample', 'producer', 'bad', outputs=output, checks=['contact'])
        self.ref('source', 'mutated')
        with self.assertRaises(ValueError):
            rc.complete(self.record, 'sample', 'producer', 'stale', outputs=self.ref('v1', 'candidate'), checks=['contact'])

    def test_capability_and_dag(self):
        self.setup(capabilities=[])
        self.assertIn('sample', rc.next(self.record)['blocked'])
        with self.assertRaises(ValueError):
            self.claim('sample', 'producer')
        self.assertFalse(rc.resume(self.record)['automatic_redispatch'])

    def test_spawn_review_reservation_and_followup(self):
        tasks = [dict(id=str(i), stage='minimal-sample', owner='Visual', inputs={}, outputs=[], required_checks=['ok']) for i in range(4)]
        rc.initialize(self.record, tasks=tasks)
        for i in range(3):
            self.claim(str(i), 'agent' + str(i))
        with self.assertRaises(ValueError):
            self.claim('3', 'agent3')
        self.assertEqual(len(rc.next(self.record)['running']), 3)

    def test_limits_preserved_by_initialize(self):
        self.setup()
        self.produce()
        self.claim('sample:review', 'reviewer')
        issue = dict(issue_id='gap', owner='Visual', severity='P1', required_checks=['contact'], evidence=self.proof, repair_outputs=['v2'])
        rc.complete(self.record, 'sample:review', 'reviewer', 'failure', verdict='fail', failures=[issue])
        record = json.loads(self.record.read_text())
        record['repair_controller']['issues']['gap']['rounds_without_improvement'] = 2
        self.record.write_text(json.dumps(record))
        rc.initialize(self.record)
        self.assertIn('gap:repair:1', rc.next(self.record)['blocked'])
        with self.assertRaises(ValueError):
            self.claim('gap:repair:1', 'producer', 'followup')

    def test_review_missing_evidence_cannot_close(self):
        self.setup()
        self.produce()
        self.claim('sample:review', 'reviewer')
        with self.assertRaises(ValueError):
            rc.complete(self.record, 'sample:review', 'reviewer', 'empty', checks=['contact'])
        with self.assertRaises(ValueError):
            rc.complete(self.record, 'sample:review', 'reviewer', 'partial', evidence=self.proof)


    def test_execution_intent_survives_resume_and_blocks_relaunch(self):
        tasks = [dict(id=name, stage=name, owner='Owner', inputs=self.source,
                      outputs=[], required_checks=['ok'], command=['true'])
                 for name in rc.CHAIN]
        rc.initialize(self.record, tasks=tasks)
        record = json.loads(self.record.read_text())
        state = record['repair_controller']
        for stage in rc.CHAIN[:3]:
            state['tasks'][stage]['status'] = 'done'
            state['tasks'][stage].update(agent_id='prior-agent', dispatch_receipt={'agent_id':'prior-agent'}, result={'outputs':{},'evidence':{}})
            state['events'].append(dict(event='claim',task_id=stage,agent_id='prior-agent'))
        self.record.write_text(json.dumps(record))
        self.claim('measured-narration-timeline', 'producer')
        token = rc.start_execution(self.record, 'narration', ['true'])
        rc.resume(self.record)
        with self.assertRaises(ValueError):
            rc.start_execution(self.record, 'narration', ['true'])
        result = rc.finish_execution(self.record, token, 0)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result, rc.finish_execution(self.record, token, 0))
        with self.assertRaises(ValueError):
            rc.finish_execution(self.record, token, 1)

    def test_initialization_preserves_legacy_repair_counts(self):
        self.record.write_text(json.dumps({'prior_version_issues': [
            dict(issue_id='old', repair_attempts=3, rounds_without_improvement=2, status='open')]}))
        self.setup()
        issue = rc.initialize(self.record)['issues']['old']
        self.assertEqual(issue['repair_attempts'], 3)
        self.assertEqual(issue['rounds_without_improvement'], 2)

    def test_cycle_and_output_conflicts_rejected_atomically(self):
        for tasks in ([dict(id='a', stage='minimal-sample', owner='A', deps=['b']),
                       dict(id='b', stage='minimal-sample', owner='B', deps=['a'])],
                      [dict(id='a', stage='minimal-sample', owner='A', outputs=['same']),
                       dict(id='b', stage='minimal-sample', owner='B', outputs=['./same'])],
                      [dict(id='a', stage='minimal-sample', owner='A', outputs=['folder']),
                       dict(id='b', stage='minimal-sample', owner='B', outputs=['folder/child'])]):
            with self.assertRaises(ValueError):
                rc.initialize(self.record, tasks=tasks)
            self.assertNotIn('repair_controller', json.loads(self.record.read_text()))

    def test_handoff_limit_and_active_hold(self):
        self.setup()
        record = json.loads(self.record.read_text())
        record['repair_controller']['handoffs'] = 20
        self.record.write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            self.claim('sample', 'producer')
        record['repair_controller']['handoffs'] = 0
        record['hold'] = True
        self.record.write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            self.claim('sample', 'producer')

    def test_same_tool_turn_reuse_requires_exact_receipt(self):
        rc.initialize(self.record, tasks=[dict(id=str(i), stage='minimal-sample', owner='Visual',
                       inputs={}, outputs=[], required_checks=['ok']) for i in range(2)])
        receipt = {'agent_id': 'producer', 'tool_call_id': 'one-real-call'}
        rc.claim(self.record, '0', 'producer', receipt)
        rc.complete(self.record, '0', 'producer', 'done0', checks=['ok'])
        with self.assertRaises(ValueError):
            rc.claim(self.record, '1', 'producer', {'agent_id': 'producer', 'tool_call_id': 'invented'}, 'reuse')
        rc.claim(self.record, '1', 'producer', receipt, 'reuse')
        state = json.loads(self.record.read_text())['repair_controller']
        self.assertEqual(len(state['agents']), 1)
        self.assertEqual(state['agents']['producer']['followups'], 0)

    def test_stale_completed_dependency_blocks_claim(self):
        rc.initialize(self.record, tasks=[
            dict(id='a', stage='minimal-sample', owner='Visual', inputs=self.source, outputs=['v1'], required_checks=['ok']),
            dict(id='b', stage='preflight', owner='Editor', deps=['a'], inputs={}, outputs=[], required_checks=['ok'])])
        self.claim('a', 'producer')
        rc.complete(self.record, 'a', 'producer', 'a-done', outputs=self.ref('v1', 'candidate'), checks=['ok'])
        self.claim('a:review', 'reviewer')
        rc.complete(self.record, 'a:review', 'reviewer', 'review-done', checks=['ok'], evidence=self.proof)
        self.ref('source', 'stale')
        self.assertIn('b', rc.next(self.record)['blocked'])
        with self.assertRaises(ValueError):
            self.claim('b', 'editor')

    def test_unbenchmarked_sensory_capability_blocks(self):
        rc.initialize(self.record, tasks=[dict(id='listen', stage='independent-check', owner='QA',
            inputs={}, outputs=[], required_checks=['ok'], capabilities=['audio'])], capabilities=['audio'])
        self.assertIn('listen', rc.next(self.record)['blocked'])

    def test_command_completion_requires_successful_execution_receipt(self):
        rc.initialize(self.record, tasks=[dict(id='command', stage='render', owner='Visual',
            command=['true'], inputs={}, outputs=[], required_checks=['ok'])])
        self.claim('command', 'producer')
        with self.assertRaises(ValueError):
            rc.complete(self.record, 'command', 'producer', 'fake-complete', checks=['ok'])


if __name__ == '__main__':
    unittest.main()
