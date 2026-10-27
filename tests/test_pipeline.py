import json
import tempfile
import unittest
from pathlib import Path
from mechanical_video.model import build
from mechanical_video.cli import enqueue, connect, TEMPLATES

class AcceptanceRecoveryTests(unittest.TestCase):
    def test_reaccepts_failed_audit_with_archived_script(self):
        from unittest.mock import patch
        from mechanical_video.acceptance import accept
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); manifest=root/'assembly.json'; manifest.write_text('{}')
            key=enqueue(root,manifest,['explode'])[0]['id']
            folder=root/'videos'/key
            (folder/'scene.validation.json').write_text('{}')
            con=connect(root)
            con.execute("UPDATE jobs SET state='failed',error='Acceptance: GPU unavailable'")
            con.commit(); con.close()
            with patch('mechanical_video.acceptance.subprocess.run') as run, patch('mechanical_video.acceptance.caption_video'), patch('mechanical_video.acceptance.verify',return_value={'decode':'passed'}), patch('mechanical_video.acceptance.generate'):
                report=accept(root)
            self.assertEqual(report['accepted'],1)
            self.assertIn(str((folder/'renderer'/'audit_scene.py').resolve()),run.call_args.args[0])
            con=connect(root)
            row=con.execute('SELECT state,error FROM jobs WHERE id=?',(key,)).fetchone()
            self.assertEqual(tuple(row),('done',None)); con.close()

class PipelineTests(unittest.TestCase):
    def test_real_cad_exports_and_cache(self):
        from build123d import import_step
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); path=build(root); data=json.loads(path.read_text())
            self.assertGreaterEqual(len(data['parts']),10)
            self.assertEqual(data['gear_teeth']['ring'],data['gear_teeth']['sun']+2*data['gear_teeth']['planet'])
            for part in data['parts']:
                solid=import_step(path.parent/part['step'])
                self.assertTrue(solid.is_valid)
                self.assertGreater(solid.volume,0)
                self.assertEqual(len(solid.solids()),1,part['name'])
            from build123d import Pos
            solids={p['name']: Pos(*p['position'])*import_step(path.parent/p['step']) for p in data['parts']}
            for i in range(1,4):
                for central in ['sun_gear','ring_gear']:
                    overlap=solids[central] & solids[f'planet_{i}']
                    self.assertLess(overlap.volume if overlap else 0,0.001)
            stamp=path.stat().st_mtime_ns
            self.assertEqual(build(root),path)
            self.assertEqual(path.stat().st_mtime_ns,stamp)
    def test_queue_deduplicates_and_preserves_portrait(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); manifest=root/'assembly.json'; manifest.write_text('{}')
            enqueue(root,manifest,TEMPLATES,portrait=True)
            enqueue(root,manifest,TEMPLATES,portrait=True)
            db=connect(root); rows=list(db.execute('SELECT * FROM jobs')); db.close()
            self.assertEqual(len(rows),10)
            spec=json.loads(rows[0]['spec']); self.assertEqual((spec['width'],spec['height']),(720,1280))
    def test_reject_bad_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): build(Path(tmp),{'module':100})

class ImageContractTests(unittest.TestCase):
    def test_missing_provider_never_fabricates_analysis(self):
        from unittest.mock import patch
        from PIL import Image
        from mechanical_video.cli import analyze
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); image=root/'product.png'; Image.new('RGB',(16,16)).save(image)
            with patch.dict('os.environ',{},clear=True):
                with self.assertRaisesRegex(RuntimeError,'no image recognition result'):
                    analyze(image,root)
            self.assertEqual(len(list((root/'inputs').glob('*/*.png'))),1)
            self.assertEqual(len(list((root/'inputs').glob('*/analysis.json'))),0)
    def test_unsupported_provider_result_is_saved_without_substitution(self):
        from unittest.mock import patch,Mock
        from PIL import Image
        from mechanical_video.cli import analyze
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); image=root/'product.png'; Image.new('RGB',(16,16)).save(image)
            response=Mock(); response.json.return_value={'choices':[{'message':{'content':json.dumps({'product_type':'pump','supported_family':'unsupported'})}}]}
            with patch.dict('os.environ',{'VISION_ENDPOINT':'http://local.invalid','VISION_MODEL':'test'}), patch('requests.post',return_value=response):
                with self.assertRaisesRegex(ValueError,'outside implemented CAD families'): analyze(image,root)
            self.assertEqual(len(list((root/'inputs').glob('*/analysis.json'))),1)
            self.assertFalse((root/'models').exists())

class RuntimeTests(unittest.TestCase):
    def test_idle_consumer_does_not_block_acceptance(self):
        from mechanical_video.runtime import exclusive_lock
        from mechanical_video.cli import worker
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def idle(_):
                with exclusive_lock(root/'render.lock'):
                    pass
                with self.assertRaisesRegex(RuntimeError,'worker.lock'):
                    worker(root)
                raise KeyboardInterrupt
            with patch('mechanical_video.cli.time.sleep',side_effect=idle):
                with self.assertRaises(KeyboardInterrupt): worker(root,watch=True)
            # Both leases are released when the consumer exits.
            with exclusive_lock(root/'worker.lock'),exclusive_lock(root/'render.lock'): pass

    def test_archived_renderer_is_immutable_across_source_edits(self):
        from unittest.mock import patch
        from mechanical_video import runtime
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); src=root/'source'; src.mkdir()
            for name in runtime.RENDER_FILES: (src/name).write_bytes((runtime.SOURCE/name).read_bytes())
            manifest=root/'assembly.json'; manifest.write_text('{}')
            with patch.object(runtime,'SOURCE',src):
                first=enqueue(root,manifest,['explode'])[0]
                old=json.loads(connect(root).execute('SELECT spec FROM jobs WHERE id=?',(first['id'],)).fetchone()[0])
                archived=runtime.render_sources(Path(old['directory']),old)
                original=(archived/'blender_scene.py').read_bytes()
                with (src/'blender_scene.py').open('a') as f: f.write('\n# next renderer revision\n')
                second=enqueue(root,manifest,['explode'])[0]
                self.assertNotEqual(first['id'],second['id'])
                self.assertEqual((runtime.render_sources(Path(old['directory']),old)/'blender_scene.py').read_bytes(),original)
                (archived/'blender_scene.py').write_text('modified archive')
                with self.assertRaisesRegex(ValueError,'modified'): runtime.render_sources(Path(old['directory']),old)

    def test_too_short_or_nonfinite_duration_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); manifest=root/'assembly.json'; manifest.write_text('{}')
            for seconds in [0,0.001,float('nan'),float('inf')]:
                with self.assertRaises(ValueError): enqueue(root,manifest,['explode'],seconds=seconds)

class VisionModelTests(unittest.TestCase):
    def test_default_and_override_reach_the_provider_request(self):
        from unittest.mock import patch,Mock
        from PIL import Image
        from mechanical_video.cli import analyze
        for override,expected in [(None,'gpt-6-luna'),('custom-vision','custom-vision')]:
            with self.subTest(model=expected),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp); image=root/'product.png'; Image.new('RGB',(16,16)).save(image)
                response=Mock(); response.json.return_value={'choices':[{'message':{'content':json.dumps({'supported_family':'unsupported'})}}]}
                env={'VISION_ENDPOINT':'http://local.invalid/chat/completions'}
                if override: env['VISION_MODEL']=override
                with patch.dict('os.environ',env,clear=True),patch('requests.post',return_value=response) as post:
                    with self.assertRaisesRegex(ValueError,'outside implemented CAD families'): analyze(image,root)
                self.assertEqual(post.call_args.kwargs['json']['model'],expected)
                self.assertEqual(post.call_args.kwargs['json']['messages'][0]['content'][1]['type'],'image_url')
