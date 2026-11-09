import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from mechanical_video import content_contract as contract
from mechanical_video import production_gate as gate
from mechanical_video import production_run


class ContentContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        for name, value in [('brief.txt', '卷尺回卷与锁止。释放后回卷。'), ('script.txt', '卷簧拉动卷盘回卷。按钮通过制动件锁止尺带。'), ('proof.txt', 'Independent observed state transition fixture')]:
            (self.base / name).write_text(value)
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=gray:s=32x32:r=2:d=2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(self.base / 'clip.mp4')], check=True, capture_output=True)
        requirements = [dict(id='rewind', brief_quote='回卷', observable='卷盘转动与尺带回收', source_parts=['spring', 'spool']), dict(id='lock', brief_quote='锁止', observable='外部输入经制动件停止尺带', source_parts=['button', 'brake'])]
        intent = dict(schema_version=1, question='卷尺怎样回卷与锁止？', brief=self.ref('brief.txt'), requirements=requirements)
        (self.base / 'contract.json').write_text(json.dumps(intent, ensure_ascii=False))
        self.p = dict(schema_version=4, assets={'approved_brief': self.ref('brief.txt'), 'content_contract': self.ref('contract.json'), 'narration_draft': self.ref('script.txt'), 'local_clip': self.ref('clip.mp4')}, required_interval=[0, 2])
        self.review = dict(contract_sha256=self.p['assets']['content_contract']['sha256'], producer='visual', reviewer='independent-mechanics', evidence=[self.ref('proof.txt')], script_asset='narration_draft', requirements=[])
        for rid, quote in [('rewind', '卷簧拉动卷盘回卷'), ('lock', '按钮通过制动件锁止尺带')]:
            self.review['requirements'].append(dict(id=rid, script_quote=quote, verdict='clear', source_consistent=True, clip_asset='local_clip', clip_interval=[0, 2], observations=[dict(time=t, observation=state, evidence=self.ref('proof.txt')) for t, state in [(0, 'before'), (1, 'after')]], causal_explanation='fixture mechanism', input_linkage='external button -> brake', output_result='blade held'))
        self.p['content_review'] = self.review
        self.refresh()

    def ref(self, name):
        return dict(path=name, sha256=gate.sha(self.base / name))

    def refresh(self):
        self.review['asset_fingerprints'] = {k:v['sha256'] for k,v in self.p['assets'].items()}

    def errors(self, stage='narration'):
        return contract.evaluate(self.p, self.base, stage)

    def test_complete_traceability_is_read_only(self):
        before = copy.deepcopy(self.p)
        self.assertEqual(self.errors(), [])
        self.assertEqual(self.p, before)

    def test_wrong_topic_script_is_blocked(self):
        (self.base / 'script.txt').write_text('尺头松动是厚度补偿。')
        self.p['assets']['narration_draft'] = self.ref('script.txt')
        self.refresh()
        self.assertTrue(any('answer absent' in e for e in self.errors()))

    def test_required_question_cannot_be_dropped(self):
        self.review['requirements'].pop()
        self.assertTrue(any('omitted' in e for e in self.errors()))

    def test_missing_or_static_evidence_is_blocked(self):
        for states in (None, [], [self.review['requirements'][0]['observations'][0]]):
            with self.subTest(states=states):
                self.review['requirements'][0]['observations'] = states
                self.assertTrue(any('before/after' in e for e in self.errors()))

    def test_external_control_or_unclear_contact_blocks(self):
        self.review['requirements'][1]['input_linkage'] = ''
        self.review['requirements'][1]['verdict'] = 'unclear'
        errors = self.errors()
        self.assertTrue(any('input/contact/output' in e for e in errors))
        self.assertTrue(any('unresolved' in e for e in errors))

    def test_fake_mp4_and_out_of_bounds_observations_block(self):
        (self.base / 'clip.mp4').write_bytes(b'not a video')
        self.p['assets']['local_clip'] = self.ref('clip.mp4')
        self.refresh()
        self.assertTrue(any('not decodable' in e for e in self.errors()))

    def test_stale_assets_and_self_review_block(self):
        self.review['reviewer'] = 'visual'
        (self.base / 'brief.txt').write_text('changed topic')
        self.assertTrue(any('brief' in e for e in self.errors()))
        (self.base / 'brief.txt').write_text('卷尺回卷与锁止。释放后回卷。')
        self.assertTrue(any('independent' in e for e in self.errors()))

    def test_final_payoff_cannot_be_omitted(self):
        self.assertTrue(any('final causal payoff' in e for e in self.errors('delivery')))
        self.p['assets']['final_media'] = self.ref('clip.mp4')
        self.refresh()
        for proof in self.review['requirements']:
            proof.update(final_interval=[0, 2], final_media_sha256=self.ref('clip.mp4')['sha256'], final_evidence=self.ref('proof.txt'))
        self.assertEqual(self.errors('delivery'), [])

    def test_real_gate_invokes_content_contract_before_narration(self):
        # The existing source_action association alone must not waive intent.
        self.p.update(actions={'a':[0,2]}, critical_mechanical_uncertainty=False, checks=[], issues=[])
        check = dict(kind='source_action', action='a', status='PASS', asset_fingerprints=self.review['asset_fingerprints'], coverage=[0,2], method='fixture', scope='fixture', producer='visual', reviewer='other', evidence=[self.ref('proof.txt')], source_parts=['spring'], representation='teaching', explanation_roles='source')
        self.p['checks'] = [check]
        record = dict(production_checks=self.p)
        self.assertEqual(gate.evaluate(record, self.base, 'narration', require_version=4)['status'], 'READY')
        record['prior_version_issues'] = [dict(issue_id='unreadable-contact', severity='P1', status='open', repair_attempts=2)]
        self.assertEqual(gate.evaluate(record, self.base, 'narration', require_version=4)['status'], 'BLOCKED')
        record.pop('prior_version_issues')
        self.review['requirements'].pop()
        self.assertEqual(gate.evaluate(record, self.base, 'narration', require_version=4)['status'], 'BLOCKED')

    def test_runner_never_launches_blocked_or_unbound_command(self):
        sentinel = self.base / 'launched'
        cmd = [sys.executable, '-c', 'from pathlib import Path; Path(' + repr(str(sentinel)) + ').touch()']
        self.p['execution'] = {'narration':cmd}
        self.review['execution'] = {'narration':cmd}
        record = self.base / 'record.json'
        record.write_text(json.dumps(dict(production_checks=self.p)))
        report, code = production_run.run(record, 'narration', cmd)
        self.assertEqual(code, 1)
        self.assertFalse(sentinel.exists())
        # Isolate command dispatch from the separately integration-tested gate.
        with patch.object(production_run, 'evaluate', return_value={'status':'READY'}):
            self.assertEqual(production_run.run(record, 'narration', cmd)[1], 0)
        self.assertTrue(sentinel.exists())
        sentinel.unlink()
        with patch.object(production_run, 'evaluate', return_value={'status':'READY'}):
            self.assertEqual(production_run.run(record, 'narration', cmd + ['different'])[1], 1)
        self.assertFalse(sentinel.exists())
