"""Local live inspector for actual waveform SDR -> official SP/TM.

Run using the existing HTM runtime. No pretrained model is loaded.
"""
import argparse
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time
from urllib.parse import urlparse, parse_qs
import wave

import numpy as np
from .htm_waveform import Engine, decode, sha, runtime


class Inspector:
    def __init__(self, audio):
        self.source = Path(audio).resolve()
        self.config, self.samples = decode(self.source)
        if not np.isfinite(self.samples).all() or np.any(np.abs(self.samples) > 1):
            raise ValueError('audio exceeds fixed PCM range')
        self.source_hash = sha(self.source)
        self.runtime = runtime()
        self.lock = threading.RLock()
        self.running = False
        self.learning = True
        self.speed = 1.
        self.error = None
        self.generation = 0
        self.passes = []
        self.reset()
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as w:
            w.setnchannels(self.config.channels)
            w.setsampwidth(2)
            w.setframerate(self.config.rate)
            w.writeframes(np.clip(self.samples*32767, -32768, 32767).astype('<i2').tobytes())
        self.wav = buffer.getvalue()  # Listening copy only; model receives original f32.

    def reset(self):
        with self.lock:
            self.running = False
            self.engine = Engine(self.config)
            self.engine.tm.reset()
            self.frames = []
            self.cursor = 0
            self.pass_number = 1
            self.passes = []
            self.error = None
            self.generation += 1

    def restart(self):
        with self.lock:
            self.running = False
            self.passes.append(dict(pass_number=self.pass_number, frames=len(self.frames),
                mean_anomaly=float(np.mean([f['anomaly'] for f in self.frames])) if self.frames else None))
            self.engine.tm.reset()
            self.frames = []
            self.cursor = 0
            self.pass_number += 1
            self.generation += 1

    @property
    def total(self):
        return (len(self.samples)*1000+self.config.rate*self.config.frame_ms-1)//(self.config.rate*self.config.frame_ms)

    def step(self):
        with self.lock:
            if self.cursor >= self.total:
                self.running = False
                return None
            c = self.config
            start = self.cursor*c.rate*c.frame_ms//1000
            end = min(len(self.samples), (self.cursor+1)*c.rate*c.frame_ms//1000)
            sparse = c.encode(self.samples[start:end])
            e = self.engine
            e.input.sparse = sparse
            e.sp.compute(e.input, self.learning, e.columns)
            columns = e.columns.sparse.copy()
            # Exact documented compute ordering: dendrites use preceding cells;
            # inspect that prediction BEFORE current-frame cell activation.
            e.tm.activateDendrites(self.learning)
            predicted_cells = e.tm.getPredictiveCells().sparse.copy()
            predicted_columns = np.unique(predicted_cells//8)
            # compute reuses already-valid dendrites and also sets official anomaly.
            e.tm.compute(e.columns, learn=self.learning)
            actual_input = e.input.sparse.copy()
            active_cells = e.tm.getActiveCells().sparse.copy()
            actual_tm_columns = np.unique(active_cells//8)
            hits = np.intersect1d(columns, predicted_columns)
            missed = np.setdiff1d(columns, predicted_columns)
            manual = len(missed)/len(columns) if len(columns) else 0.
            anomaly = float(e.tm.anomaly)
            if not np.isclose(manual, anomaly, atol=1e-6):
                raise RuntimeError(f'Anomaly mismatch: {manual} != {anomaly}')
            frame = dict(index=self.cursor, start_sample=start, end_sample=end,
                start=start/c.rate, end=end/c.rate, learning=self.learning,
                input_sdr=actual_input.tolist(), sp_output=columns.tolist(), tm_input=columns.tolist(),
                tm_active_columns=actual_tm_columns.tolist(),
                predicted_cells_for_current=predicted_cells.tolist(),
                predicted_columns_for_current=predicted_columns.tolist(),
                predicted_hits=hits.tolist(), bursting_columns=missed.tolist(),
                active_cells=active_cells.tolist(),
                winner_cells=e.tm.getWinnerCells().sparse.tolist(),
                anomaly=anomaly, recomputed_anomaly=manual,
                checks=dict(input_count=len(actual_input)==(end-start)*c.channels,
                    unique_bits=len(np.unique(actual_input))==len(actual_input),
                    input_bounds=bool(np.all(actual_input < c.size)),
                    sp_tm_equal=bool(np.array_equal(columns, actual_tm_columns)),
                    anomaly_equal=bool(np.isclose(manual, anomaly, atol=1e-6))))
            self.frames.append(frame)
            self.cursor += 1
            if self.cursor == self.total:
                self.running = False
            return frame

    def snapshot(self, index=None):
        with self.lock:
            frame = None
            if self.frames:
                index = len(self.frames)-1 if index is None else max(0,min(index,len(self.frames)-1))
                frame = dict(self.frames[index])
                frame['waveform'] = self.samples[frame['start_sample']:frame['end_sample']].T.tolist()
            return dict(source=self.source.name, source_sha256=self.source_hash,
                config=vars(self.config), dimensions=dict(input=self.config.size, columns=512, cells=4096, cells_per_column=8),
                total=self.total, processed=self.cursor, duration=len(self.samples)/self.config.rate,
                running=self.running, learning=self.learning, speed=self.speed, error=self.error,
                pass_number=self.pass_number, generation=self.generation, frame=frame,
                history=[f['anomaly'] for f in self.frames], passes=self.passes)

    def loop(self):
        while True:
            started = time.monotonic()
            with self.lock:
                if self.running:
                    try:
                        self.step()
                    except Exception as exc:
                        self.error = str(exc)
                        self.running = False
                delay = self.config.frame_ms/1000/self.speed
            # Never skip audio frames. If compute is slow, wall-clock playback slows.
            time.sleep(max(.001, delay-(time.monotonic()-started)))


def serve(inspector, port):
    html = Path(__file__).with_name('htm_waveform_live.html').read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, data, content_type='application/json', status=200):
            if not isinstance(data, bytes):
                data = json.dumps(data, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == '/':
                return self.reply(html, 'text/html; charset=utf-8')
            if url.path == '/api/state':
                try:
                    index = parse_qs(url.query).get('frame', [None])[0]
                    return self.reply(inspector.snapshot(None if index is None else int(index)))
                except ValueError:
                    return self.reply({'error':'invalid frame'}, status=400)
            if url.path == '/api/export':
                with inspector.lock:
                    return self.reply(dict(metadata=inspector.snapshot(), runtime=inspector.runtime,
                        source=str(inspector.source), frames=inspector.frames))
            if url.path == '/audio.wav':
                data = inspector.wav
                # Native audio scrubbing needs byte ranges.
                requested = self.headers.get('Range')
                if requested:
                    try:
                        unit, value = requested.split('=')
                        a, b = value.split('-')
                        if unit != 'bytes' or not a:
                            raise ValueError()
                        start = int(a); end = min(len(data)-1, int(b) if b else len(data)-1)
                        if not 0 <= start <= end < len(data):
                            raise ValueError()
                    except ValueError:
                        return self.reply(b'', status=416)
                    self.send_response(206)
                    self.send_header('Content-Type','audio/wav')
                    self.send_header('Accept-Ranges','bytes')
                    self.send_header('Content-Range',f'bytes {start}-{end}/{len(data)}')
                    self.send_header('Content-Length',str(end-start+1))
                    self.end_headers(); self.wfile.write(data[start:end+1]); return
                return self.reply(data, 'audio/wav')
            return self.reply({'error':'not found'}, status=404)

        def do_POST(self):
            # Local browser only, reject cross-origin command submissions.
            if self.headers.get('Origin') not in (None, f'http://127.0.0.1:{port}', f'http://localhost:{port}'):
                return self.reply({'error':'origin rejected'}, status=403)
            try:
                length = int(self.headers.get('Content-Length','0'))
                if length > 4096:
                    raise ValueError('request too large')
                body = json.loads(self.rfile.read(length) or '{}')
                with inspector.lock:
                    action = self.path
                    if action == '/api/play': inspector.running = inspector.cursor < inspector.total
                    elif action == '/api/pause': inspector.running = False
                    elif action == '/api/step':
                        inspector.running = False
                        inspector.step()
                    elif action == '/api/reset': inspector.reset()
                    elif action == '/api/restart': inspector.restart()
                    elif action == '/api/settings':
                        if inspector.running:
                            raise ValueError('pause before changing settings')
                        learning = body.get('learning',inspector.learning)
                        speed = float(body.get('speed',inspector.speed))
                        if not isinstance(learning,bool) or speed not in (.1,.25,.5,1.,2.):
                            raise ValueError('invalid settings')
                        inspector.learning = learning; inspector.speed = speed
                    else: return self.reply({'error':'not found'}, status=404)
                return self.reply(inspector.snapshot())
            except (ValueError, TypeError) as exc:
                return self.reply({'error':str(exc)}, status=400)

    threading.Thread(target=inspector.loop, daemon=True).start()
    print(f'HTM live inspector: http://127.0.0.1:{port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio', required=True)
    p.add_argument('--port', type=int, default=8766)
    args = p.parse_args()
    serve(Inspector(args.audio), args.port)

if __name__ == '__main__': main()
