import copy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mechanical_video import scene_fidelity
from mechanical_video.scene_fidelity import canonical, capture_scene, compare, file_ref, write_inventory


def inventory():
    mesh = {'type': 'MESH', 'geometry_sha256': 'deformed-belt-mesh',
            'matrix_world': [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, .109096], [0, 0, 0, 1]],
            'bounds_world': [[0, 0, .01], [1, 1, 1]], 'visibility': {'hide_render': False},
            'appearance_sha256': 'material'}
    return {'schema_version': 1, 'capture': 'evaluated-rest-state', 'unit_scale': 1,
            'implementation_sha256': file_ref(scene_fidelity.__file__)['sha256'],
            'source': {'sha256': 'baseline'}, 'renderer': {'sha256': 'renderer'},
            'scene': {'camera': 'Camera', 'resolution': [1080, 1920, 100]},
            'objects': {'belt': mesh, 'support-without-part-id': copy.deepcopy(mesh)}}


class SceneFidelityTests(unittest.TestCase):
    def setUp(self):
        self.baseline = inventory()
        self.current = copy.deepcopy(self.baseline)

    def test_preservation_read_only_and_roundoff(self):
        original = copy.deepcopy(self.baseline)
        self.current['objects']['belt']['matrix_world'][2][3] += 1e-8
        self.assertEqual(compare(self.baseline, self.current)['status'], 'PASS')
        self.assertEqual(self.baseline, original)

    def test_ep07_regressions_are_blocked(self):
        for mutation, expected in (
            (lambda d: d['objects']['belt']['matrix_world'][2].__setitem__(3, 0), 'matrix_world'),
            (lambda d: d['objects'].pop('support-without-part-id'), '$object'),
            (lambda d: d['objects']['belt'].__setitem__('geometry_sha256', 'nominal-mesh'), 'geometry_sha256'),
            (lambda d: d['objects']['belt'].__setitem__('visibility', {'hide_render': True}), 'visibility'),
            (lambda d: d['scene'].__setitem__('resolution', [720, 1280, 100]), 'resolution')):
            with self.subTest(expected=expected):
                current = copy.deepcopy(self.baseline)
                mutation(current)
                result = compare(self.baseline, current)
                self.assertEqual(result['status'], 'BLOCKED')
                self.assertIn(expected, [i['field'] for i in result['issues']])

    def test_explicit_camera_and_overlay_changes_do_not_exempt_belt(self):
        self.current['scene']['camera'] = 'EpisodeCamera'
        self.current['objects']['label'] = {'type': 'FONT', 'matrix_world': self.baseline['objects']['belt']['matrix_world'],
                                             'visibility': {}, 'appearance_sha256': 'text'}
        changes = [{'object': '$scene', 'field': 'camera', 'before_sha256': canonical('Camera'),
                    'after_sha256': canonical('EpisodeCamera'), 'reason': 'episode framing'},
                   {'object': 'label', 'field': '$object', 'before_sha256': canonical(None),
                    'after_sha256': canonical(self.current['objects']['label']), 'reason': 'new label'}]
        policy = {'schema_version': 1, 'changes': changes}
        self.assertEqual(compare(self.baseline, self.current, policy)['status'], 'PASS')
        self.current['objects']['belt']['matrix_world'][2][3] = 0
        self.assertEqual(compare(self.baseline, self.current, policy)['status'], 'BLOCKED')

    def test_stale_duplicate_and_unexplained_exceptions(self):
        change = {'object': 'belt', 'field': 'geometry_sha256', 'before_sha256': canonical('deformed-belt-mesh'),
                  'after_sha256': canonical('other'), 'reason': 'candidate'}
        policy = {'schema_version': 1, 'changes': [change]}
        self.assertEqual(compare(self.baseline, self.current, policy)['status'], 'BLOCKED')
        policy['changes'].append(change)
        with self.assertRaises(ValueError):
            compare(self.baseline, self.current, policy)
        change['reason'] = ''
        with self.assertRaises(ValueError):
            compare(self.baseline, self.current, {'schema_version': 1, 'changes': [change]})

    def test_invalid_partial_or_nonfinite_inventory_is_not_pass(self):
        for mutation in (lambda d: d['objects'].clear(),
                         lambda d: d['objects']['belt'].pop('geometry_sha256'),
                         lambda d: d['objects']['belt']['matrix_world'][0].__setitem__(0, float('nan'))):
            broken = copy.deepcopy(self.current)
            mutation(broken)
            with self.assertRaises(ValueError):
                compare(self.baseline, broken)

    def test_capture_uses_evaluated_geometry_and_keeps_untagged_support(self):
        class Matrix(list):
            def __matmul__(self, vector):
                return [sum(self[i][j] * vector[j] for j in range(3)) + self[i][3] for i in range(3)]
        matrix = Matrix([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, .109], [0, 0, 0, 1]])
        mesh = SimpleNamespace(vertices=[SimpleNamespace(co=(0, 0, 0)), SimpleNamespace(co=(1, 1, 1))],
                               polygons=[SimpleNamespace(vertices=(0, 1), material_index=0, use_smooth=False)])
        cleared = []
        evaluated = SimpleNamespace(matrix_world=matrix, data=mesh, to_mesh=lambda: mesh,
                                    to_mesh_clear=lambda: cleared.append(True))
        obj = SimpleNamespace(name='untagged-support', type='MESH', material_slots=[],
                              hide_render=False, hide_viewport=False, visible_get=lambda: True,
                              evaluated_get=lambda graph: evaluated)
        # There is intentionally no part_id, original mesh or original matrix.
        scene = SimpleNamespace(objects=[obj], unit_settings=SimpleNamespace(scale_length=1),
                                collection=SimpleNamespace(name='Scene Collection', hide_render=False,
                                                           hide_viewport=False, objects=[obj], children=[]),
                                camera=SimpleNamespace(name='Camera'), world=None,
                                render=SimpleNamespace(engine='CYCLES', resolution_x=1080, resolution_y=1920,
                                                       resolution_percentage=100, fps=30, fps_base=1),
                                view_settings=SimpleNamespace(view_transform='Standard', look='None', exposure=0, gamma=1))
        bpy = SimpleNamespace(context=SimpleNamespace(view_layer=SimpleNamespace(update=lambda: None),
                                                      evaluated_depsgraph_get=lambda: 'actual graph'))
        with tempfile.TemporaryDirectory() as folder, patch.dict(sys.modules, {'bpy': bpy}):
            root = Path(folder)
            source = root / 'source.blend'
            source.write_bytes(b'source fixture')
            renderer = root / 'renderer.py'
            renderer.write_text('# frozen fixture')
            baseline = write_inventory(root / 'inventory.json', scene, source, renderer)
            self.assertEqual(baseline['objects']['untagged-support']['bounds_world'], [[0, 0, .109], [1, 1, 1.109]])
            self.assertEqual(cleared, [True])
            with self.assertRaises(FileExistsError):
                write_inventory(root / 'inventory.json', scene, source, renderer)
            matrix[2][3] = 0
            current = capture_scene(scene, source, renderer)
            self.assertEqual(compare(baseline, current)['status'], 'BLOCKED')
            mesh.calc_loop_triangles = lambda: None
            mesh.loop_triangles = [SimpleNamespace(vertices=(0, 1, 0))]
            scene.get = lambda name: (.1, .2, .3)
            sampled = capture_scene(scene, source, renderer, cad_objects=['untagged-support'])
            self.assertEqual(sampled['cad_frame']['presentation_shift_m'], [.1,.2,.3])
            geometry = sampled['objects']['untagged-support']['cad_geometry']
            self.assertEqual(geometry['vertices_world'], [[0, 0, 0], [1, 1, 1]])
            self.assertEqual(geometry['triangles'], [[0, 1, 0]])


if __name__ == '__main__':
    unittest.main()
