import unittest
import tempfile
from pathlib import Path
import numpy as np
from mechanical_video.htm_waveform import Config, Engine

try:
    import htm.bindings.algorithms
    NATIVE = True
except ImportError:
    NATIVE = False

class WaveformTests(unittest.TestCase):
    def test_mapping_channels_padding(self):
        c = Config(1000,2)
        points = c.encode(np.array([[-1,1],[0,-.5]]))
        self.assertEqual(points.tolist(),[0,96,703,720])
        self.assertEqual(len(points),4)
        self.assertFalse(any(128 <= x < 640 for x in points))
    def test_coverage_fractional_rate(self):
        c = Config(11025,1)
        frames = list(c.frames(np.zeros((22053,1))))
        self.assertEqual(sum(b-a for a,b,_ in frames),22053)
        self.assertEqual(frames[-1][1],22053)
        for a,b,s in frames:
            self.assertEqual(len(s),b-a)
            self.assertEqual(len(set(s)),b-a)
            self.assertTrue(np.all(s < c.size))
    def test_fixed_scale(self):
        c = Config(1000,1)
        self.assertEqual(c.encode(np.array([[.25]]))[0],40)
        self.assertEqual(c.encode(np.array([[.25],[1.]]))[0],40)
        with self.assertRaises(ValueError): c.encode(np.array([[1.1]]))
    @unittest.skipUnless(NATIVE, 'official native HTM environment required')
    def test_temporal_learning_freezing_reset(self):
        e = Engine(Config(1000,1))
        x = np.repeat(np.array([-.75,-.25,.25,.75]),10)[:,None]
        x = np.tile(x,(20,1))
        cold = e.sequence(x)
        for _ in range(8): e.sequence(x,True)
        state = e.state_hash()
        a = e.sequence(x)
        e.sequence(-x)
        b = e.sequence(x)
        self.assertEqual(a,b)
        self.assertEqual(state,e.state_hash())
        self.assertLess(np.mean([r['anomaly'] for r in a[4:]]),np.mean([r['anomaly'] for r in cold[4:]]))

    @unittest.skipUnless(NATIVE, 'official native HTM environment required')
    def test_checkpoint_roundtrip_and_tamper(self):
        e = Engine(Config(1000,1))
        x = np.tile(np.repeat([-.75,-.25,.25,.75],10),10)[:,None]
        e.fit([x],2)
        expected = e.sequence(x)
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory)/'model'
            e.save(model,[])
            loaded = Engine.load(model)
            self.assertEqual(expected,loaded.sequence(x))
            with (model/'tm.bin').open('ab') as f: f.write(b'changed')
            with self.assertRaises(ValueError): Engine.load(model)

if __name__ == '__main__': unittest.main()
