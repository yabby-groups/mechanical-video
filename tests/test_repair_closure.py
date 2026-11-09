import copy, unittest
from unittest.mock import patch
import test_production_gate as fixtures
from mechanical_video import production_gate as gate

class RepairClosureTests(unittest.TestCase):
 def setUp(self):
  self.fixture=fixtures.ProductionGateTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
  self.record=self.fixture.record;self.p=self.record['production_checks'];self.p['schema_version']=4
  self.issue=dict(issue_id='CONTROL-001',severity='P1',status='resolved',repair_attempts=1,required_checks=['source_connection','camera_visibility'])
  self.record['issues']=[self.issue]
 def result(self):
  # Isolate closure logic; the actual contract checker is separately integrated.
  with patch('mechanical_video.content_contract.evaluate',return_value=[]):
   return gate.evaluate(self.record,self.fixture.base,'narration',self.fixture.now,require_version=4)
 def resolution(self):
  self.issue['resolution']=dict(issue_id='CONTROL-001',verdict='verified',producer='visual',reviewer='independent-video-qa',checks_covered=['source_connection','camera_visibility'],asset_fingerprints={k:v['sha256'] for k,v in self.p['assets'].items()},evidence=[{'path':'proof','sha256':gate.sha(self.fixture.base/'proof')}])
 def test_producer_closed_label_cannot_pass(self):
  self.assertEqual(self.result()['status'],'BLOCKED')
 def test_independent_current_evidence_with_all_checks_can_pass(self):
  self.resolution();self.assertEqual(self.result()['status'],'READY')
 def test_self_review_and_geometry_only_do_not_close_visibility(self):
  self.resolution();self.issue['resolution']['reviewer']='visual'
  self.assertEqual(self.result()['status'],'BLOCKED')
  self.resolution();self.issue['resolution']['checks_covered']=['source_connection']
  self.assertEqual(self.result()['status'],'BLOCKED')
 def test_stale_evidence_or_other_version_blocks(self):
  self.resolution();self.issue['resolution']['asset_fingerprints']={'head':'old'}
  self.assertEqual(self.result()['status'],'BLOCKED')
  self.resolution();(self.fixture.base/'proof').write_text('changed evidence')
  self.assertEqual(self.result()['status'],'BLOCKED')
 def test_missing_required_checks_cannot_be_used_to_close(self):
  self.resolution();self.issue['required_checks']=[]
  self.assertEqual(self.result()['status'],'BLOCKED')
 def test_prior_version_closure_needs_the_same_proof(self):
  self.record.pop('issues');self.record['prior_version_issues']=[self.issue]
  self.assertEqual(self.result()['status'],'BLOCKED')
 def test_open_issue_and_repair_limits_still_apply(self):
  self.resolution();self.issue.update(status='open',repair_attempts=3)
  result=self.result();self.assertEqual(result['status'],'BLOCKED');self.assertIn('repair strategy exhausted',result['reasons'])
 def test_historical_v1_not_rewritten(self):
  before=copy.deepcopy(self.record);self.p['schema_version']=1
  self.assertEqual(gate.evaluate(self.record,self.fixture.base,'narration',self.fixture.now)['status'],'READY')
  self.p['schema_version']=4;self.assertEqual(self.record,before)
