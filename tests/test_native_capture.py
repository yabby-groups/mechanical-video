import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from mechanical_video import native_capture
from mechanical_video.runtime import GPUUnavailable


class NativeCaptureTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / 'source.blend'
        self.source.write_bytes(b'fixture')
        self.renderer = self.root / 'renderer.py'
        self.renderer.write_text('# renderer identity; never executed')
        self.output = self.root / 'capture'

    def test_gpu_absent_never_starts_blender_or_creates_output(self):
        with patch.object(native_capture, 'require_metal_device', side_effect=GPUUnavailable), \
                patch.object(native_capture.subprocess, 'run') as run, contextlib.redirect_stdout(io.StringIO()) as out:
            code = native_capture.main(['--scene', str(self.source), '--renderer', str(self.renderer), '--output', str(self.output)])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out.getvalue())['status'], 'GPU_ACCESS_REQUIRED')
        run.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_native_success_preserves_inputs_and_records_identity(self):
        def execute(command, **kwargs):
            job = json.loads((self.output / 'request.json').read_text())
            inventory = {'source': job['source'], 'renderer': job['renderer'],
                         'schema_version': 1, 'capture': 'evaluated-rest-state', 'unit_scale': 1,
                         'scene': {'camera': None}, 'implementation_sha256': job['implementation']['sha256'],
                         'objects': {'support': {'type': 'FONT', 'matrix_world': [[1, 0, 0, 0], [0, 1, 0, 0],
                                                                                [0, 0, 1, 0], [0, 0, 0, 1]],
                                                 'visibility': {}, 'appearance_sha256': 'fixture'}}}
            (self.output / 'scene-inventory.json').write_text(json.dumps(inventory))
            self.assertNotIn('--render-frame', command)
            self.assertNotIn('--engine', command)
            return subprocess.CompletedProcess(command, 0)
        with patch.object(native_capture, 'ROOT', self.root), patch.object(native_capture, 'require_metal_device'), \
                patch.object(native_capture.subprocess, 'run', side_effect=execute):
            result = native_capture.capture(self.source, self.renderer, self.output)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(self.source.read_bytes(), b'fixture')
        self.assertTrue((self.output / 'capture-result.json').is_file())

    def test_signal_and_timeout_remain_blocked_without_retry(self):
        for failure in ('signal', 'timeout'):
            with self.subTest(failure=failure), patch.object(native_capture, 'ROOT', self.root), \
                    patch.object(native_capture, 'require_metal_device'), patch.object(native_capture.subprocess, 'run') as run:
                if failure == 'signal':
                    run.return_value = subprocess.CompletedProcess(['blender'], -11)
                else:
                    run.side_effect = subprocess.TimeoutExpired(['blender'], 1)
                result = native_capture.capture(self.source, self.renderer, self.root / failure)
                self.assertEqual(result['status'], 'BLOCKED')
                self.assertEqual(run.call_count, 1)

    def test_exit_zero_without_inventory_does_not_pass(self):
        with patch.object(native_capture, 'ROOT', self.root), patch.object(native_capture, 'require_metal_device'), \
                patch.object(native_capture.subprocess, 'run', return_value=subprocess.CompletedProcess(['blender'], 0)):
            result = native_capture.capture(self.source, self.renderer, self.output)
        self.assertEqual(result['status'], 'BLOCKED')

    def test_cad_request_does_not_pass_without_actual_geometry(self):
        def execute(command, **kwargs):
            job = json.loads((self.output / 'request.json').read_text())
            self.assertEqual(job['cad_objects'], ['gear'])
            inventory = {'source': job['source'], 'renderer': job['renderer'],
                         'implementation_sha256': job['implementation']['sha256'],
                         'objects': {'gear': {}}}
            (self.output / 'scene-inventory.json').write_text(json.dumps(inventory))
            return subprocess.CompletedProcess(command, 0)
        with patch.object(native_capture, 'ROOT', self.root), patch.object(native_capture, 'require_metal_device'), \
                patch.object(native_capture.scene_fidelity, 'compare'), \
                patch.object(native_capture.subprocess, 'run', side_effect=execute):
            self.assertEqual(native_capture.capture(self.source, self.renderer, self.output, cad_objects=['gear'])['status'], 'BLOCKED')

    def test_invalid_cad_request_never_starts_blender(self):
        with patch.object(native_capture.subprocess, 'run') as run:
            with self.assertRaises(ValueError):
                native_capture.capture(self.source, self.renderer, self.output, cad_objects='gear')
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
