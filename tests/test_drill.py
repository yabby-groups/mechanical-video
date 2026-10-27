import json
import tempfile
import unittest
from pathlib import Path

class DrillTests(unittest.TestCase):
    def test_exports_reimport_and_cache(self):
        from mechanical_video.drill import build
        from build123d import import_step
        with tempfile.TemporaryDirectory() as tmp:
            path=build(Path(tmp)); data=json.loads(path.read_text())
            self.assertEqual(data['product'],'cordless_drill')
            self.assertEqual(len(data['parts']),len({p['name'] for p in data['parts']}))
            for p in data['parts']:
                shape=import_step(path.parent/p['step'])
                self.assertTrue(shape.is_valid,p['name'])
                self.assertGreater(shape.volume,0,p['name'])
                self.assertEqual(len(shape.solids()),1,p['name'])
                self.assertTrue(p['inferred'])
                self.assertTrue((path.parent/p['stl']).is_file())
            stamp=path.stat().st_mtime_ns
            self.assertEqual(build(Path(tmp)),path)
            self.assertEqual(path.stat().st_mtime_ns,stamp)
    def test_drill_rejects_reducer_simulation_without_partial_queue(self):
        from mechanical_video.cli import enqueue
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); manifest=root/'assembly.json'
            manifest.write_text('{"product":"cordless_drill"}')
            with self.assertRaisesRegex(ValueError,'reducer-specific'):
                enqueue(root,manifest,['explode','working'])
            self.assertFalse((root/'queue.sqlite').exists())
    def test_drill_captions_do_not_claim_reducer_ratio(self):
        from mechanical_video.narration import create
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); manifest=root/'assembly.json'
            manifest.write_text('{"product":"cordless_drill"}')
            (root/'job.json').write_text(json.dumps({'manifest':str(manifest)}))
            content=create(root,'explode',5).read_text()
            self.assertIn('hypothetical',content)
            self.assertNotIn('planetary reducer',content)
            self.assertNotIn('Seventeen',content)
