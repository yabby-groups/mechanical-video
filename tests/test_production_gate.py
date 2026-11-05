import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('production_gate', Path(__file__).parents[1] / 'scripts/production_gate.py')
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class ProductionGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.now = 10000
        (self.base / 'asset').write_text('source-v1')
        (self.base / 'proof').write_text('actual local evidence fixture')
        (self.base / 'local.mp4').write_bytes(b'encoded-fixture')
        (self.base / 'budget').write_text(json.dumps({'status': 'PASS', 'available_free_bytes': 20, 'required_free_bytes': 10}))
        ref = lambda name: {'path': name, 'sha256': gate.sha(self.base / name)}
        import hashlib
        result = {'returncode': 0}
        entry = {'status': 'PASS', 'result': result, 'result_sha256': hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
        (self.base / 'technical.json').write_text(json.dumps({'identity': {'media_sha256': ref('local.mp4')['sha256']}, 'checks': {'probe': entry, 'decode': entry}}))
        self.record = {'production_checks': {'schema_version': 1, 'assets': {'head': ref('asset')},
                       'actions': {'lift': [0, 10]}, 'required_interval': [0, 10],
                       'critical_mechanical_uncertainty': False, 'checks': [], 'issues': [],
                       'capability_gaps': ['actual listening unavailable'], 'delivery_mode': 'review'}}
        p = self.record['production_checks']
        for kind in set(sum((list(v) for v in gate.STAGES.values()), [])):
            c = {'kind': kind, 'action': 'lift' if kind in ('source_action', 'unfold', 'reassembly', 'attachments', 'clearance', 'neighbors', 'overlays', 'foley') else None,
                 'status': 'PASS', 'asset_fingerprints': {'head': ref('asset')['sha256']},
                 'coverage': [0, 10], 'method': 'actual independent local review', 'scope': 'fixture',
                 'producer': 'visual-agent', 'reviewer': 'qa-agent', 'evidence': [ref('budget' if kind == 'storage' else 'proof')],
                 'source_parts': ['part1'], 'representation': 'mixed', 'explanation_roles': 'source head plus labeled teaching gap', 'created_at': self.now}
            if kind in ('local_encode', 'final_encode'):
                c['evidence'] = [ref('local.mp4'), ref('technical.json')]
            p['checks'].append(c)

    def evaluate(self, stage='full-render'):
        return gate.evaluate(self.record, self.base, stage, self.now)

    def test_complete_and_read_only(self):
        before = copy.deepcopy(self.record)
        self.assertEqual(self.evaluate()['status'], 'READY')
        self.assertEqual(self.record, before)
        self.assertEqual(gate.evaluate(self.record, self.base, 'full-render', self.now, require_version=2)['status'], 'BLOCKED')

    def v2_fixture(self):
        from mechanical_video import scene_fidelity
        from mechanical_video.scene_fidelity import compare
        ref = lambda name: {'path': name, 'sha256': gate.sha(self.base / name)}
        matrix = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, .109], [0, 0, 0, 1]]
        scene = {'schema_version': 1, 'capture': 'evaluated-rest-state', 'unit_scale': 1,
                 'implementation_sha256': gate.sha(scene_fidelity.__file__),
                 'source': ref('asset'), 'renderer': ref('asset'), 'scene': {'camera': 'camera'},
                 'objects': {'belt': {'type': 'MESH', 'matrix_world': matrix, 'visibility': {},
                                      'geometry_sha256': 'deformed', 'appearance_sha256': 'material',
                                      'bounds_world': [[0, 0, 0], [1, 1, 1]]}}}
        policy = {'schema_version': 1, 'changes': []}
        for name, data in (('baseline.json', scene), ('current.json', scene), ('policy.json', policy),
                           ('fidelity.json', compare(scene, scene, policy))):
            (self.base / name).write_text(json.dumps(data))
        (self.base / 'ab.png').write_bytes(b'fixture image')
        p = self.record['production_checks']
        p['schema_version'] = 2
        p['assets'].update(baseline_scene=ref('asset'), renderer=ref('asset'),
                           baseline_inventory=ref('baseline.json'), scene_inventory=ref('current.json'),
                           scene_policy=ref('policy.json'))
        p['checks'].append(dict(p['checks'][0], kind='baseline_fidelity', action=None,
                                reviewed_views=['whole_machine', 'bottom', 'routing', 'mechanism'],
                                evidence=[ref('fidelity.json'), ref('ab.png')]))
        for c in p['checks']:
            c['asset_fingerprints'] = {k: r['sha256'] for k, r in p['assets'].items()}
        return p

    def test_v2_requires_actual_baseline_comparison_and_independent_ab(self):
        p = self.v2_fixture()
        self.assertEqual(self.evaluate()['status'], 'READY')
        self.assertEqual(self.evaluate('delivery')['status'], 'REVIEW_DELIVERY')
        c = p['checks'][-1]
        c['reviewed_views'].remove('bottom')
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')
        c['reviewed_views'].append('bottom')
        c['reviewer'] = c['producer']
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')

    def test_v2_recomputes_instead_of_trusting_pass_report(self):
        p = self.v2_fixture()
        current = self.base / 'current.json'
        data = json.loads(current.read_text())
        data['objects']['belt']['matrix_world'][2][3] = 0
        current.write_text(json.dumps(data))
        p['assets']['scene_inventory']['sha256'] = gate.sha(current)
        for c in p['checks']:
            c['asset_fingerprints']['scene_inventory'] = gate.sha(current)
        result = self.evaluate()
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn('missing/stale check: baseline_fidelity', result['reasons'])

    def test_missing_evidence_and_stale_asset(self):
        for name in ('proof', 'asset'):
            with self.subTest(name=name):
                original = (self.base / name).read_bytes()
                (self.base / name).write_bytes(b'changed')
                self.assertEqual(self.evaluate()['status'], 'BLOCKED')
                (self.base / name).write_bytes(original)
        (self.base / 'proof').unlink()
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')

    def test_open_p1_hold_uncertainty_and_limits(self):
        p = self.record['production_checks']
        for issue in ({'issue_id': 'P1', 'severity': 'P1', 'status': 'open', 'repair_attempts': 1},
                      {'issue_id': 'P2', 'severity': 'P2', 'status': 'open', 'repair_attempts': 3},
                      {'issue_id': 'P2', 'severity': 'P2', 'status': 'open', 'repair_attempts': 2, 'rounds_without_improvement': 2}):
            p['issues'] = [issue]
            self.assertEqual(self.evaluate()['status'], 'BLOCKED')
        p['issues'] = []
        p['holds'] = ['user preview required']
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')
        p['holds'] = []
        p['critical_mechanical_uncertainty'] = True
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')

    def test_coverage_cannot_be_shrunk_in_check(self):
        check = next(c for c in self.record['production_checks']['checks'] if c['kind'] == 'clearance')
        check.update(coverage=[0, 2], required_interval=[0, 2])
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')

    def test_v2_local_encoding_has_explicit_excerpt_scope_only(self):
        p = self.v2_fixture()
        p['local_encode_interval'] = [0, 2]
        local = next(c for c in p['checks'] if c['kind'] == 'local_encode')
        local['coverage'] = [0, 2]
        self.assertEqual(self.evaluate()['status'], 'READY')
        clearance = next(c for c in p['checks'] if c['kind'] == 'clearance')
        clearance['coverage'] = [0, 2]
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')
        clearance['coverage'] = [0, 10]
        final = next(c for c in p['checks'] if c['kind'] == 'final_encode')
        final['coverage'] = [0, 2]
        self.assertEqual(self.evaluate('delivery')['status'], 'BLOCKED')

    def test_v2_local_encoding_rejects_invalid_excerpt_bounds(self):
        p = self.v2_fixture()
        for interval in ([-1, 2], [0, 11], [2, 2], [True, 2], [0, float('nan')]):
            with self.subTest(interval=interval):
                p['local_encode_interval'] = interval
                self.assertEqual(self.evaluate()['status'], 'BLOCKED')

    def test_legacy_local_encoding_cannot_shrink_with_v2_field(self):
        p = self.record['production_checks']
        p['local_encode_interval'] = [0, 2]
        next(c for c in p['checks'] if c['kind'] == 'local_encode')['coverage'] = [0, 2]
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')

    def test_identity_conflict_not_overridden_by_flag(self):
        for c in self.record['production_checks']['checks']:
            c.update(reviewer='visual-agent', independent_required=False)
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')

    def test_stale_motion_dependency_and_storage(self):
        p = self.record['production_checks']
        p['assets']['motion'] = p['assets']['head']
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')
        del p['assets']['motion']
        self.now += 901
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')

    def test_static_proof_does_not_replace_local_encoding(self):
        c = next(c for c in self.record['production_checks']['checks'] if c['kind'] == 'local_encode')
        c['evidence'] = [self.record['production_checks']['checks'][0]['evidence'][0]]
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')

    def test_review_delivery_is_not_formal_acceptance(self):
        self.assertEqual(self.evaluate('delivery')['status'], 'REVIEW_DELIVERY')
        self.record['production_checks']['delivery_mode'] = 'formal'
        self.assertEqual(self.evaluate('delivery')['status'], 'BLOCKED')

    def test_formal_requires_same_version_independent_evidence(self):
        p = self.record['production_checks']
        p.update(delivery_mode='formal', capability_gaps=[], all_established_gates_passed=True)
        template = p['checks'][0]
        p['acceptance'] = {key: dict(template, score=95) for key in ('overall', 'technical', 'audience', 'audio_technical', 'audio_appeal')}
        self.assertEqual(self.evaluate('delivery')['status'], 'READY')
        p['acceptance']['audience']['profile'] = 'local-av'
        self.assertEqual(self.evaluate('delivery')['status'], 'BLOCKED')
        del p['acceptance']['audience']['profile']
        p['acceptance']['audience']['asset_fingerprints'] = {}
        self.assertEqual(self.evaluate('delivery')['status'], 'BLOCKED')

    def test_ep06_isolated_historical_regression(self):
        source = Path(__file__).parents[1] / 'series/3d-printer-v2/episodes-current/EP06/director-record.json'
        before = source.read_bytes()
        historical = json.loads(before)
        self.assertEqual(gate.evaluate(historical, self.base, 'full-render')['status'], 'BLOCKED')
        # Copy the actual rejected intersection finding, never rewrite its historical closure.
        finding = historical['realhead_repair']['latest_final_rejected_scope'] if 'realhead_repair' in historical else None
        if finding is None:
            finding = next(v['latest_final_rejected_scope'] for v in historical.values() if isinstance(v, dict) and 'latest_final_rejected_scope' in v)
        self.record['production_checks']['issues'].append({'issue_id': 'EP06-INTERSECTION-REGRESSION', 'severity': 'P1', 'status': 'open', 'repair_attempts': 1, 'evidence': finding})
        self.assertEqual(self.evaluate()['status'], 'BLOCKED')
        self.assertEqual(source.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
