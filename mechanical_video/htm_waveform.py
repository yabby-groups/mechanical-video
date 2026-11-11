"""Versioned raw waveform SDR -> official SP -> TM. No quality classifier."""
import argparse
from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np

VERSION = 'waveform-sdr-v1'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

@dataclass(frozen=True)
class Config:
    rate: int
    channels: int
    frame_ms: int = 10
    levels: int = 64

    def __post_init__(self):
        if self.rate <= 0 or self.channels <= 0 or self.frame_ms <= 0 or self.levels != 64:
            raise ValueError('invalid encoding configuration')

    @property
    def width(self):
        return (self.rate*self.frame_ms+999)//1000

    @property
    def size(self):
        return self.channels*self.width*self.levels

    def frames(self, samples):
        # Rational boundaries avoid drift at rates not divisible by 100 Hz.
        i = 0
        while (start := i*self.rate*self.frame_ms//1000) < len(samples):
            end = min(len(samples), (i+1)*self.rate*self.frame_ms//1000)
            if end <= start:
                raise ValueError('frame interval is below one sample')
            yield start, end, self.encode(samples[start:end])
            i += 1

    def encode(self, frame):
        frame = np.asarray(frame)
        if frame.ndim != 2 or frame.shape[1] != self.channels or not 0 < len(frame) <= self.width:
            raise ValueError('frame shape does not match configuration')
        if not np.isfinite(frame).all() or np.any(np.abs(frame) > 1):
            raise ValueError('samples outside fixed PCM amplitude range [-1,1]')
        bins = np.minimum(63, np.floor((frame+1)*32)).astype(np.uint32)
        positions = np.arange(len(frame), dtype=np.uint32)[:, None]
        channels = np.arange(self.channels, dtype=np.uint32)[None, :]
        return np.sort(((channels*self.width+positions)*64+bins).ravel())


def decode(path):
    info = json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','a:0',
        '-show_entries','stream=sample_rate,channels','-of','json',str(path)]))['streams'][0]
    cfg = Config(int(info['sample_rate']), int(info['channels']))
    raw = subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0',
                                  '-f','f32le','-acodec','pcm_f32le','-'])
    samples = np.frombuffer(raw, dtype='<f4').reshape(-1, cfg.channels)
    if not len(samples):
        raise ValueError('empty audio')
    return cfg, samples

class Engine:
    def __init__(self, cfg):
        from htm.bindings.algorithms import SpatialPooler, TemporalMemory
        from htm.bindings.sdr import SDR
        self.cfg = cfg
        self.input = SDR(cfg.size)
        self.columns = SDR(512)
        self.sp = SpatialPooler(inputDimensions=[cfg.size], columnDimensions=[512],
            potentialRadius=cfg.size, potentialPct=.1, globalInhibition=True,
            localAreaDensity=.04, synPermInactiveDec=.008, synPermActiveInc=.04,
            synPermConnected=.1, seed=42)
        self.tm = TemporalMemory(columnDimensions=[512], cellsPerColumn=8,
            activationThreshold=8, minThreshold=5, maxNewSynapseCount=20, seed=42)

    def sequence(self, samples, learn=False):
        self.tm.reset()
        rows = []
        for start, end, sparse in self.cfg.frames(samples):
            self.input.sparse = sparse
            self.sp.compute(self.input, learn, self.columns)
            self.tm.compute(self.columns, learn=learn)
            rows.append(dict(start_sample=start, end_sample=end, start=start/self.cfg.rate,
                end=end/self.cfg.rate, valid_samples=end-start, active_bits=len(sparse),
                anomaly=float(self.tm.anomaly), sequence_start=start == 0))
        return rows

    def fit(self, recordings, epochs=3):
        if epochs < 1:
            raise ValueError('epochs must be positive')
        for _ in range(epochs):
            for samples in recordings:
                self.sequence(samples, learn=True)
        # SP vocabulary must stabilize before learning final temporal transitions.
        self.tm = Engine(self.cfg).tm
        for _ in range(epochs):
            for samples in recordings:
                self.tm.reset()
                for _, _, sparse in self.cfg.frames(samples):
                    self.input.sparse = sparse
                    self.sp.compute(self.input, False, self.columns)
                    self.tm.compute(self.columns, learn=True)

    def state_hash(self):
        # Official inference updates counters even with learn=False. Hash learned
        # connections, permanences and SP adaptation state, not those counters.
        h = hashlib.sha256()
        values = np.zeros(self.cfg.size, dtype=np.float32)
        for column in range(512):
            self.sp.getPermanence(column, values)
            h.update(values.tobytes())
        for getter in ('getBoostFactors', 'getActiveDutyCycles', 'getOverlapDutyCycles'):
            state = np.zeros(512, dtype=np.float32)
            getattr(self.sp, getter)(state)
            h.update(state.tobytes())
        h.update(str(self.sp.getIterationLearnNum()).encode())
        c = self.tm.connections
        for cell in range(c.numCells()):
            for segment in c.segmentsForCell(cell):
                synapses = [(c.presynapticCellForSynapse(s), c.permanenceForSynapse(s))
                            for s in c.synapsesForSegment(segment)]
                h.update(repr((cell, segment, sorted(synapses))).encode())
        return h.hexdigest()

    def write_states(self, directory):
        self.tm.reset()
        result = {}
        for name in ('sp','tm'):
            path = directory/(name+'.bin')
            getattr(self,name).saveToFile(str(path),'BINARY')
            result[path.name] = sha(path)
        return result

    def save(self, directory, sources):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=False)
        manifest = dict(version=VERSION, config=asdict(self.cfg), sources=sources,
                        files=self.write_states(directory), runtime=runtime())
        (directory/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')

    @classmethod
    def load(cls, directory):
        directory = Path(directory)
        manifest = json.loads((directory/'manifest.json').read_text())
        if manifest['version'] != VERSION or manifest['runtime'] != runtime():
            raise ValueError('encoding/runtime mismatch')
        if set(manifest['files']) != {'sp.bin','tm.bin'}:
            raise ValueError('incomplete checkpoint')
        engine = cls(Config(**manifest['config']))
        for name, digest in manifest['files'].items():
            if sha(directory/name) != digest:
                raise ValueError('checkpoint changed')
            getattr(engine, name[:-4]).loadFromFile(str(directory/name),'BINARY')
        return engine


def runtime():
    import htm.bindings.algorithms as a
    import htm.bindings.sdr as s
    return dict(algorithms=sha(a.__file__), sdr=sha(s.__file__), implementation=sha(__file__))


def intervals(rows, threshold):
    result = []
    for row in rows:
        # First frame has no preceding context and is reported but not alarmed.
        if row['sequence_start'] or row['anomaly'] < threshold:
            continue
        if result and result[-1]['end_sample'] == row['start_sample']:
            result[-1].update(end=row['end'], end_sample=row['end_sample'])
        else:
            result.append({k:row[k] for k in ('start','end','start_sample','end_sample')})
    return result


def review(engine, samples, source, output, threshold):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    before = engine.state_hash()
    rows = engine.sequence(samples)
    after = engine.state_hash()
    if before != after:
        raise RuntimeError('frozen inference changed learned parameters')
    # Exact PCM permits reconstruction of every point, no image artifacts.
    np.save(output/'waveform.npy', samples, allow_pickle=False)
    (output/'timeline.json').write_text(json.dumps(rows)+'\n')
    report = dict(version=VERSION, status='UNQUALIFIED', learning=False,
        config=asdict(engine.cfg), source=source, samples=len(samples),
        samples_consumed=sum(r['valid_samples'] for r in rows), threshold=threshold,
        candidates=intervals(rows,threshold), model_before=before, model_after=after,
        evidence={name:sha(output/name) for name in ('waveform.npy','timeline.json')},
        limitation='Prediction novelty is not a defect verdict or complete listening review.')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    train = sub.add_parser('train')
    train.add_argument('--audio', nargs='+', required=True)
    train.add_argument('--model', required=True)
    train.add_argument('--epochs', type=int, default=3)
    evaluate = sub.add_parser('review')
    evaluate.add_argument('--audio', required=True)
    evaluate.add_argument('--model', required=True)
    evaluate.add_argument('--output', required=True)
    evaluate.add_argument('--threshold', type=float, default=.8)
    args = p.parse_args()
    if args.command == 'train':
        if args.epochs < 1:
            p.error('epochs must be positive')
        decoded = [decode(path) for path in args.audio]
        cfg = decoded[0][0]
        if any(c != cfg for c,_ in decoded):
            p.error('all inputs must match encoding rate and channels; no resampling')
        engine = Engine(cfg)
        engine.fit([samples for _, samples in decoded], args.epochs)
        engine.save(args.model, [dict(path=str(Path(x).resolve()),sha256=sha(x)) for x in args.audio])
    else:
        if not 0 < args.threshold <= 1:
            p.error('threshold must be in (0,1]')
        cfg, samples = decode(args.audio)
        engine = Engine.load(args.model)
        if cfg != engine.cfg:
            p.error('audio configuration differs from frozen model')
        report = review(engine,samples,dict(path=str(Path(args.audio).resolve()),sha256=sha(args.audio)),
                        args.output,args.threshold)
        print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
