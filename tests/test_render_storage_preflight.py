import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

SPEC = importlib.util.spec_from_file_location(
    "render_storage_preflight", Path(__file__).resolve().parents[1] / "scripts/render_storage_preflight.py")
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


class StoragePreflightTests(unittest.TestCase):
    def test_largest_frame_and_existing_files_not_double_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.png", Path(tmp) / "b.png"
            a.write_bytes(b"a" * 100)
            b.write_bytes(b"b" * 200)
            with patch.object(preflight.shutil, "disk_usage", return_value=SimpleNamespace(free=500)):
                report = preflight.storage_budget([a, b], tmp, 2, 0, 0, 1.25)
            self.assertEqual(report["required_free_bytes"], 500)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(a.stat().st_size, 100)
            self.assertEqual(b.stat().st_size, 200)

    def test_insufficient_space_includes_encoding_and_reserve(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "frame.png"
            sample.write_bytes(b"x" * 100)
            with patch.object(preflight.shutil, "disk_usage", return_value=SimpleNamespace(free=100)):
                report = preflight.storage_budget([sample], tmp, 1, 1, 1, 1)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["shortfall_bytes"], 2 * preflight.GIB)

    def test_invalid_estimates_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "empty.png"
            sample.touch()
            for kwargs in ({}, {"remaining_frames": -1}, {"temporary_gib": float("nan")},
                           {"reserve_gib": -1}, {"safety_factor": 0.9}):
                args = {"samples": [sample], "output_dir": tmp, "remaining_frames": 1, **kwargs}
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    preflight.storage_budget(**args)
            with self.assertRaises(ValueError):
                preflight.storage_budget([], tmp, 1)
            with self.assertRaises(OSError):
                preflight.storage_budget([sample], Path(tmp) / "missing", 1)


if __name__ == "__main__":
    unittest.main()
