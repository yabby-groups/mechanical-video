import copy
import json
from pathlib import Path
import tempfile
import unittest
from mechanical_video.scene_preflight import validate_policy, verify
from mechanical_video.scene_fidelity import canonical,file_ref
from mechanical_video import scene_preflight


class ScenePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
        self.policy={'schema_version':1,'pose_mode':'renderer_callback','requirements':[{'id':'lock','frames':[1,3],'motion_object':'button','min_motion':.01,'targets':[{'object':'button','point':[0,0,0],'min_pixels':20,'tolerance':.01}],'connections':[{'a':{'object':'button','point':[0,0,0]},'b':{'object':'link','point':[0,0,0]},'max_distance':.01}]}]}
        for name in ['source','renderer']:(self.base/name).write_text('fixture')
        (self.base/'policy').write_text(json.dumps(self.policy))
        self.assets={n:file_ref(self.base/n) for n in ['source','renderer','policy']}
        self.report={'schema_version':1,'kind':'evaluated-pre-render-scene','inputs':self.assets,'policy':self.policy,'implementation_sha256':file_ref(scene_preflight.__file__)['sha256'],'coverage':{'lock':[1,2,3]},'status':'PASS','failures':[],'render_called':False,'pose_mode':'renderer_callback'}
        self.sign()

    def sign(self):
        self.report['result_sha256']=canonical({k:v for k,v in self.report.items() if k!='result_sha256'})

    def test_valid_report_traceability(self):
        self.assertTrue(verify(self.report,self.assets,['lock']))

    def test_coverage_cannot_skip_bad_middle_frame(self):
        self.report['coverage']['lock']=[1,3];self.sign()
        self.assertFalse(verify(self.report,self.assets,['lock']))

    def test_contract_requirement_cannot_be_omitted(self):
        self.assertFalse(verify(self.report,self.assets,['lock','rewind']))

    def test_stale_renderer_and_implementation_block(self):
        (self.base/'renderer').write_text('changed')
        self.assertFalse(verify(self.report,self.assets,['lock']))
        (self.base/'renderer').write_text('fixture')
        self.report['implementation_sha256']='different';self.sign()
        self.assertFalse(verify(self.report,self.assets,['lock']))

    def test_nonempty_failure_never_passes(self):
        self.report['failures']=[{'frame':2,'reason':'occluded'}];self.sign()
        self.assertFalse(verify(self.report,self.assets,['lock']))

    def test_policy_must_define_motion_targets_and_connections(self):
        for key in ['motion_object','targets','connections']:
            bad=copy.deepcopy(self.policy);bad['requirements'][0].pop(key)
            with self.subTest(key=key),self.assertRaises(ValueError):validate_policy(bad)

    def test_missing_or_nonnumeric_thresholds_rejected(self):
        for value in [None,False,float('nan'),0,-1]:
            bad=copy.deepcopy(self.policy);bad['requirements'][0]['targets'][0]['min_pixels']=value
            with self.subTest(value=value),self.assertRaises(ValueError):validate_policy(bad)

    def test_deforming_vertex_policy_rejects_invalid_indices(self):
        target = self.policy['requirements'][0]['targets'][0]
        target.pop('point')
        target['vertex_index'] = 2
        validate_policy(self.policy)
        for value in [False, None, -1, 2.5, '2']:
            target['vertex_index'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_policy(self.policy)

    def test_surface_anchor_uses_current_evaluated_mesh_and_releases_it(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        obj = Mock(type='MESH')
        obj.to_mesh.side_effect = [
            SimpleNamespace(vertices=[SimpleNamespace(co=[1, 2, 3])]),
            SimpleNamespace(vertices=[SimpleNamespace(co=[4, 5, 6])]),
            SimpleNamespace(vertices=[]),
        ]
        ref = {'vertex_index': 0}
        self.assertEqual(scene_preflight.local_anchor(obj, ref), (1, 2, 3))
        self.assertEqual(scene_preflight.local_anchor(obj, ref), (4, 5, 6))
        with self.assertRaises(ValueError):
            scene_preflight.local_anchor(obj, ref)
        self.assertEqual(obj.to_mesh_clear.call_count, 3)

    def test_face_center_anchor_and_ambiguous_indices(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        obj = Mock(type='MESH')
        obj.to_mesh.return_value = SimpleNamespace(polygons=[SimpleNamespace(center=[1, 2, 3])])
        self.assertEqual(scene_preflight.local_anchor(obj, {'face_index': 0}), (1, 2, 3))
        obj.to_mesh_clear.assert_called_once()
        target = self.policy['requirements'][0]['targets'][0]
        target['face_index'] = 0
        validate_policy(self.policy)
        target['vertex_index'] = 0
        with self.assertRaises(ValueError):
            validate_policy(self.policy)

    def test_full_render_gate_requires_same_scene_and_renderer_preflight(self):
        from unittest.mock import patch
        from test_production_gate import ProductionGateTests
        from mechanical_video import production_gate
        helper=ProductionGateTests()
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        checks=helper.v2_fixture()
        checks['schema_version']=4
        checks['assets']['renderer']=file_ref(helper.base/'asset')
        checks['assets']['scene_source']=self.assets['source']
        checks['assets']['scene_preflight_policy']=self.assets['policy']
        intent=self.base/'contract.json';intent.write_text(json.dumps({'requirements':[{'id':'lock'}]}))
        checks['assets']['content_contract']=file_ref(intent)
        self.report['inputs']=dict(source=self.assets['source'],renderer=checks['assets']['renderer'],policy=self.assets['policy'])
        self.sign()
        proof=self.base/'preflight.json';proof.write_text(json.dumps(self.report))
        checks['assets']['scene_preflight']=file_ref(proof)
        from mechanical_video.action_alignment import inspect as inspect_action
        motion=self.base/'action-motion.json';motion.write_text(json.dumps({'fps':2,'frames':6,'poses':[{'time':i/2,'extension':5-i} for i in range(6)]}))
        timeline=self.base/'action-timeline.json';timeline.write_text(json.dumps({'duration':3,'captions':[{'text':'return','start':0,'end':3}]}))
        policy=self.base/'action-policy.json';policy.write_text(json.dumps({'schema_version':1,'requirements':[{'id':'lock','assertions':[{'caption_text':'return','channel':'extension','relation':'decreasing','min_change':1}]}]}))
        action_report=self.base/'action-report.json';action_report.write_text(json.dumps(inspect_action(motion,timeline,policy)))
        checks['assets'].update(motion=file_ref(motion),timeline=file_ref(timeline),action_alignment_policy=file_ref(policy),action_alignment=file_ref(action_report))
        for check in checks['checks']:
            check['asset_fingerprints']={k:v['sha256'] for k,v in checks['assets'].items()}
        # Isolate scene proof integration; content traceability has its own real
        # gate integration tests. CAD/baseline checks still execute here.
        with patch('mechanical_video.content_contract.evaluate',return_value=[]):
            result=production_gate.evaluate(helper.record,helper.base,'full-render',helper.now,require_version=4)
            self.assertEqual(result['status'],'READY',result)
            action_ref=checks['assets'].pop('action_alignment')
            result=production_gate.evaluate(helper.record,helper.base,'full-render',helper.now,require_version=4)
            self.assertIn('missing/stale/blocked caption-action alignment proof',result['reasons'])
            checks['assets']['action_alignment']=action_ref
            checks['assets'].pop('scene_preflight')
            result=production_gate.evaluate(helper.record,helper.base,'full-render',helper.now,require_version=4)
            self.assertIn('missing/stale/blocked evaluated pre-render scene proof',result['reasons'])
