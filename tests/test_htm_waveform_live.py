import unittest
import tempfile
import wave
from pathlib import Path
import numpy as np
from mechanical_video.htm_waveform import Engine
from mechanical_video.htm_waveform_live import Inspector

try:
    import htm.bindings.algorithms
    NATIVE = True
except ImportError:
    NATIVE = False

@unittest.skipUnless(NATIVE, 'official native HTM environment required')
class LiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'input.wav'
        values = np.tile(np.repeat([-.75,-.25,.25,.75],10),5)
        with wave.open(str(self.path),'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(1000)
            w.writeframes((values*32767).astype('<i2').tobytes())
        self.live = Inspector(self.path)
    def tearDown(self): self.temp.cleanup()
    def test_exact_official_sequence(self):
        expected = Engine(self.live.config).sequence(self.live.samples,True)
        for row in expected:
            f = self.live.step()
            self.assertAlmostEqual(f['anomaly'],row['anomaly'])
            self.assertTrue(all(f['checks'].values()))
            self.assertEqual(f['sp_output'],f['tm_input'])
        self.assertIsNone(self.live.step())
        self.assertEqual(self.live.cursor,len(expected))
    def test_restart_reset_and_frozen(self):
        cold=self.live.engine.state_hash()
        for _ in range(self.live.total):self.live.step()
        trained=self.live.engine.state_hash()
        self.assertNotEqual(cold,trained)
        self.live.restart()
        self.assertEqual(trained,self.live.engine.state_hash())
        self.assertEqual(self.live.pass_number,2)
        self.live.learning=False
        self.live.step()
        before=self.live.engine.state_hash()
        self.live.snapshot(0)
        self.assertEqual(before,self.live.engine.state_hash())
        self.assertEqual(trained,before)
        self.live.reset()
        self.assertEqual(cold,self.live.engine.state_hash())
        self.assertEqual(self.live.cursor,0)

if __name__=='__main__': unittest.main()
