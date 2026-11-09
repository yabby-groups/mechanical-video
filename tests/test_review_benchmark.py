"""Synthetic contracts only; these fixtures do not qualify a real reviewer."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from mechanical_video.review_benchmark import validate_benchmark, DEFECTS, CONTROLS


def benchmark_fixture(base, adapter='fixture-adapter'):
    path = Path(base) / 'synthetic-benchmark-evidence.txt'
    path.write_text('Synthetic unit-test evidence; not actual media or model output')
    ref = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    cases = [dict(id=topic+'-'+kind, topic=topic, kind=kind,
                  verdict='defect' if kind in DEFECTS else 'clear', passed=True,
                  observation='Synthetic test observation', speech_control_passed=True,
                  coverage=dict(source_frames=3, frames_consumed=3,
                                source_audio_samples=1600, audio_samples_consumed=1600),
                  media=ref.copy(), raw_response=ref.copy(), ground_truth=ref.copy())
             for topic in ('tape', 'pen') for kind in sorted(DEFECTS | CONTROLS)]
    return dict(schema_version=1, status='PASS', adapter=adapter,
                model_revision='synthetic-revision', runtime_fingerprint='synthetic-runtime',
                detected=sorted(DEFECTS), cases=cases)


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.report = benchmark_fixture(self.base)

    def test_complete_fixture_contract(self):
        validate_benchmark(self.report, self.base)

    def test_failed_or_uncertain_controls_cannot_be_hidden_by_summary(self):
        for mutate in (
            lambda r: r.update(status='FAIL'),
            lambda r: r.pop('cases'),
            lambda r: r.update(cases=r['cases'][:5]),
            lambda r: r['cases'][0].update(passed=False),
            lambda r: r['cases'][0].update(verdict='clear|defect|uncertain'),
            lambda r: r['cases'][0].update(speech_control_passed=False),
            lambda r: r['cases'][0]['coverage'].update(frames_consumed=2),
            lambda r: r['cases'][0]['coverage'].update(audio_samples_consumed=0),
            lambda r: r['cases'][0].update(observation=''),
            lambda r: r.update(model_revision=''),
            lambda r: r['cases'].append(copy.deepcopy(r['cases'][0])),
            lambda r: r['cases'][0].pop('raw_response'),
        ):
            with self.subTest(mutation=mutate):
                candidate=copy.deepcopy(self.report); mutate(candidate)
                with self.assertRaises(ValueError): validate_benchmark(candidate,self.base)

    def test_stale_raw_response_is_rejected(self):
        Path(self.report['cases'][0]['raw_response']['path']).write_text('changed')
        with self.assertRaisesRegex(ValueError,'stale'): validate_benchmark(self.report,self.base)
