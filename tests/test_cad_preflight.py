import copy
import json
from pathlib import Path
import tempfile
import unittest

from build123d import Box, Compound, Location, export_step
from mechanical_video import cad_preflight as cad

IDENTITY = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]


def fixture(base):
    export_step(Box(2, 2, 2), base / 'box.step')
    placed = copy.deepcopy(IDENTITY)
    placed[0][3] = 4
    spec = dict(schema_version=1, units='mm', parts=[
        dict(id='a', step='box.step', matrix_mm=IDENTITY),
        dict(id='b', step='box.step', matrix_mm=placed)],
        pairs=[dict(parts=['a', 'b'], min_gap_mm=1, max_gap_mm=3)])
    path = base / 'cad-manifest.json'
    path.write_text(json.dumps(spec))
    return path, spec


class CADTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.path, self.spec = fixture(self.base)

    def inspect(self):
        self.path.write_text(json.dumps(self.spec))
        return cad.inspect_manifest(self.path)

    def test_valid_parts_gap_and_stale_evidence(self):
        report = self.inspect()
        self.assertEqual(report['status'], 'PASS')
        self.assertTrue(cad.verify_report(report))
        report['facts']['a']['valid'] = False
        self.assertFalse(cad.verify_report(report))
        report = self.inspect()
        self.path.write_text('{}')
        self.assertFalse(cad.verify_report(report))

    def test_interference_coordinates(self):
        self.spec['parts'][1]['matrix_mm'][0][3] = 1
        r = self.inspect()
        self.assertEqual(r['status'], 'BLOCKED')
        self.assertAlmostEqual(r['measurements'][0]['intersection_mm3'], 4)
        self.assertEqual(r['issues'][0]['parts'], ['a', 'b'])
        self.assertEqual(r['issues'][0]['severity'], 'P1')
        self.assertTrue(r['issues'][0]['coordinate_mm'])
        self.assertTrue(r['issues'][0]['repair'])

    def test_contact_pressfit_and_excess(self):
        m = cad.pair_measure(Box(2,2,2), Box(2,2,2).moved(Location((2,0,0))))
        self.assertIsNone(cad.classify(m, dict(mode='contact', reason='designed face contact')))
        m['intersection_mm3'] = .2
        self.assertEqual(cad.classify(m, {})[1], 'unexpected_interference')
        self.assertIsNone(cad.classify(m, dict(mode='press_fit', reason='drawing fit', max_intersection_mm3=.3)))
        self.assertEqual(cad.classify(m, dict(mode='press_fit', reason='drawing fit', max_intersection_mm3=.1))[1], 'unexpected_interference')
        with self.assertRaises(ValueError):
            cad.classify(m, dict(mode='contact'))
        with self.assertRaises(ValueError):
            cad.classify(m, dict(volume_tolerance_mm3=.5))

    def test_missing_contact_and_gap(self):
        m = dict(distance_mm=2, intersection_mm3=0)
        self.assertEqual(cad.classify(m, dict(mode='contact', reason='mating faces'))[1], 'missing_contact')
        self.assertEqual(cad.classify(m, dict(max_gap_mm=1))[1], 'unexpected_gap')
        self.assertEqual(cad.classify(m, dict(min_gap_mm=3))[1], 'insufficient_clearance')

    def test_path_midpoint_collision_endpoints_clear(self):
        self.spec['pairs'][0] = dict(parts=['a','b'], samples=[])
        for t, x in [(0,0),(1,-4),(2,-8)]:
            matrix = copy.deepcopy(IDENTITY)
            matrix[0][3] = x
            self.spec['pairs'][0]['samples'].append(dict(time=t, transforms={'b':matrix}))
        r = self.inspect()
        self.assertEqual([i['time'] for i in r['issues']], [1])
        self.assertIn('no continuous collision', r['scope'])

    def test_bad_transform_and_placement(self):
        for value in (float('nan'), 2, -1):
            m = copy.deepcopy(IDENTITY)
            m[0][0] = value
            with self.assertRaises(ValueError):
                cad.matrix_location(m)
        self.spec['parts'][1]['expected_matrix_mm'] = IDENTITY
        self.assertEqual(self.inspect()['issues'][0]['code'], 'placement_mismatch')

    def test_invalid_surface(self):
        from build123d import Face, Wire
        face = Face.make_rect(2,2)
        self.assertFalse(cad.geometry(face)['valid'])

    def test_mesh_geometry_volume_surface_and_holes(self):
        import trimesh
        mesh = trimesh.creation.box(extents=[2,2,2])
        data = dict(vertices_world=mesh.vertices.tolist(), triangles=mesh.faces.tolist())
        self.assertEqual(cad.mesh_measure(Box(2,2,2), data, 1, .01)['status'], 'PASS')
        damaged = copy.deepcopy(data)
        damaged['triangles'].pop()
        self.assertEqual(cad.mesh_measure(Box(2,2,2), damaged, 1, .01)['status'], 'BLOCKED')
        damaged = copy.deepcopy(data)
        damaged['vertices_world'][0][0] -= 1
        r = cad.mesh_measure(Box(2,2,2), damaged, 1, .01)
        self.assertEqual(r['status'], 'BLOCKED')
        self.assertGreater(r['max_sample_surface_distance_mm'], .1)
        damaged = copy.deepcopy(data)
        damaged['vertices_world'][0] = [0,0,0]
        r = cad.mesh_measure(Box(2,2,2), damaged, 1, .01)
        self.assertGreater(r['max_sample_surface_distance_mm'], .9)

    def test_manifest_mesh_geometry_required(self):
        import trimesh
        objects = {}
        for name, x in [('a',0),('b',4)]:
            mesh = trimesh.creation.box(extents=[2,2,2])
            mesh.apply_translation([x,0,0])
            objects[name] = dict(type='MESH', bounds_world=mesh.bounds.tolist(), cad_geometry=dict(
                vertices_world=mesh.vertices.tolist(), triangles=mesh.faces.tolist()))
        self.spec.update(scene_inventory='scene.json', blender_to_mm=1,
                         require_mesh_geometry=True, scene_objects={'a':'a','b':'b'})
        (self.base/'scene.json').write_text(json.dumps(dict(objects=objects)))
        self.assertEqual(self.inspect()['status'], 'PASS')
        del objects['a']['cad_geometry']
        (self.base/'scene.json').write_text(json.dumps(dict(objects=objects)))
        self.assertEqual(self.inspect()['issues'][0]['code'], 'missing_mesh_geometry')

    def test_step_hierarchy_repeated_occurrences(self):
        first, second = Box(2,2,2), Box(2,2,2).moved(Location((5,0,0)))
        first.label = 'same'
        second.label = 'same'
        nested = Compound(children=[second], label='nested').moved(Location((10,0,0),(0,0,90)))
        assembly = Compound(children=[first, nested], label='root')
        export_step(assembly, self.base/'assembly.step')
        nodes, parts = cad.parse_step(self.base/'assembly.step')
        self.assertEqual(len(parts), 2)
        self.assertTrue(any(n['name'] == 'nested' for n in nodes))
        xs = sorted(matrix[0][3] for _, matrix in parts.values())
        self.assertAlmostEqual(xs[0], 0)
        self.assertAlmostEqual(xs[1], 10)
        self.assertAlmostEqual(max(matrix[1][3] for _,matrix in parts.values()), 5)
        self.spec = dict(schema_version=1, units='mm', assembly_step='assembly.step', pairs=[dict(parts=list(parts))])
        self.assertEqual(self.inspect()['status'], 'PASS')

    def test_blender_bounds_mismatch_and_missing_mapping(self):
        scene = {'objects': {name: dict(type='MESH', bounds_world=cad.bounds(Box(2,2,2).moved(Location((x,0,0))))) for name,x in [('a',0),('b',4)]}}
        (self.base/'scene.json').write_text(json.dumps(scene))
        self.spec.update(scene_inventory='scene.json', blender_to_mm=1, scene_objects={'a':'a','b':'b'})
        self.assertEqual(self.inspect()['status'], 'PASS')
        scene['objects']['b']['bounds_world'][0][0] += 1
        (self.base/'scene.json').write_text(json.dumps(scene))
        self.assertEqual(self.inspect()['issues'][0]['code'], 'mesh_bounds_mismatch')
        self.spec['scene_objects'].pop('b')
        with self.assertRaises(ValueError):
            self.inspect()

    def test_historical_ep09_regression(self):
        path = Path(__file__).parents[1]/'reports/occt/ep09-source-manifest.json'
        data = json.loads(path.read_text())
        if not all(Path(p['step']).exists() for p in data['parts']):
            self.skipTest('Local historical printer STEP assets not distributed')
        report = cad.inspect_manifest(path)
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertAlmostEqual(report['measurements'][0]['intersection_mm3'], 1.265004905, places=5)
        self.assertAlmostEqual(report['measurements'][1]['intersection_mm3'], .0083817601, places=5)
        self.assertEqual(len(report['issues']), 2)
