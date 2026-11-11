"""Automatic local technical inspection of new or changed production videos.

No production commands, repairs, acceptance votes or model training are launched.
"""
import argparse
from contextlib import contextmanager
import fcntl
from functools import partial
import hashlib
import html
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import threading
import time
import uuid

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO / 'reports/av-auto-review'
EXTENSIONS = {'.mp4', '.mov', '.mkv', '.webm', '.m4v'}


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    os.replace(temporary, path)


def signature(path):
    s = path.stat()
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def fingerprint(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def implementation():
    # Include decoding and report generation dependencies, not only thresholds.
    return hashlib.sha256(''.join(fingerprint(Path(__file__).with_name(name)) for name in
        ('av_auto_review.py', 'av_technical_review.py', 'htm_av_core.py', 'htm_waveform.py')).encode()).hexdigest()


class Monitor:
    def __init__(self, roots, output=DEFAULT_OUTPUT, settle=15):
        self.roots = [Path(p).resolve() for p in roots]
        self.output = Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.settle = settle

    @contextmanager
    def state(self):
        # Hook and daemon share this lock, including scanning, so no duplicate work.
        with (self.output / 'queue.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            path = self.output / 'state.json'
            state = json.loads(path.read_text()) if path.exists() else dict(schema=1, initialized=False, files={}, jobs={})
            yield state
            state['updated'] = time.time()
            atomic_json(path, state)
            self.dashboard(state)

    def paths(self):
        for root in self.roots:
            if not root.exists():
                continue
            for directory, dirs, files in os.walk(root, followlinks=False):
                dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'frames', 'reports', '.venv'}
                           and not (Path(directory) / d).is_symlink()
                           and (Path(directory) / d).resolve() != self.output]
                for name in files:
                    path = Path(directory) / name
                    if path.suffix.lower() in EXTENSIONS and not path.is_symlink():
                        yield path

    def tick(self):
        with self.state() as state:
            now = time.time()
            first = not state['initialized']
            for path in self.paths():
                try:
                    sig = signature(path)
                except FileNotFoundError:
                    continue
                key = str(path)
                previous = state['files'].get(key)
                if previous is None or previous['signature'] != sig:
                    state['files'][key] = dict(signature=sig, changed_at=now,
                        status='baseline' if first else 'pending')
                    continue
                if previous['status'] == 'pending' and now - previous['changed_at'] >= self.settle:
                    try:
                        receipt = self.inspect(path, state)
                    except OSError as exc:
                        receipt = dict(status='failed', source=str(path), error=str(exc), owner='Director', formal_acceptance=False)
                    previous.update(status=receipt['status'], receipt=receipt)
            state.update(initialized=True, roots=[str(p) for p in self.roots], heartbeat=now)
            return state

    def inspect(self, path, state):
        from .av_technical_review import write_review
        path = Path(path).resolve()
        sig = signature(path)
        sha = fingerprint(path)
        key = hashlib.sha256((str(path) + sha + implementation()).encode()).hexdigest()
        prior = state['jobs'].get(key)
        if prior and prior['status'] == 'complete':
            report = Path(prior['report'])
            if (report.is_file() and fingerprint(report) == prior['report_sha256']
                    and (report.parent/'media.mp4').is_file()
                    and fingerprint(report.parent/'media.mp4') == sha and signature(path) == sig):
                return prior
        folder = self.output / 'jobs' / (key[:20] + '-' + uuid.uuid4().hex[:8])
        folder.mkdir(parents=True)
        source = folder / ('input' + path.suffix.lower())
        receipt = dict(status='processing', source=str(path), source_sha256=sha,
            created=time.time(), owner='Director', formal_acceptance=False,
            qualification='UNQUALIFIED_FOR_PRODUCTION', directory=str(folder))
        atomic_json(folder / 'receipt.json', receipt)
        try:
            shutil.copy2(path, source)
            if signature(path) != sig or fingerprint(source) != sha:
                raise ValueError('source changed during snapshot; waiting for stable next version')
            report = write_review(source, folder / 'report', display_name=path.name)
            if signature(path) != sig or fingerprint(path) != sha:
                raise ValueError('source changed during review; results superseded')
            report_path = folder / 'report/report.json'
            receipt.update(status='complete' if report['status'] != 'INCOMPLETE' else 'incomplete',
                report=str(report_path), report_sha256=fingerprint(report_path),
                report_status=report['status'], coverage=report['coverage'],
                observations=len(report['findings']),
                review_state='INTERNAL_CONTEXT_REVIEW_REQUIRED' if report['findings'] else 'TECHNICAL_SCOPE_ONLY',
                elapsed_seconds=time.time()-receipt['created'])
            # The report carries its own verified copy; keep snapshot path valid too.
        except Exception as exc:
            receipt.update(status='failed', error=str(exc), elapsed_seconds=time.time()-receipt['created'])
        atomic_json(folder / 'receipt.json', receipt)
        state['jobs'][key] = receipt
        return receipt

    def review(self, paths):
        with self.state() as state:
            receipts = []
            for path in paths:
                path = Path(path).resolve()
                initial = signature(path) if path.exists() else None
                try:
                    receipt = self.inspect(path, state)
                except OSError as exc:
                    receipt = dict(status='failed', source=str(path), error=str(exc), owner='Director', formal_acceptance=False)
                receipts.append(receipt)
                if path.exists():
                    state['files'][str(path)] = dict(signature=initial, changed_at=time.time(),
                        status=receipt['status'], receipt=receipt)
            return receipts

    def dashboard(self, state):
        rows = []
        for receipt in sorted(state['jobs'].values(), key=lambda r:r['created'], reverse=True):
            report = Path(receipt.get('report', ''))
            link = (report.parent / 'index.html').relative_to(self.output).as_posix() if receipt.get('report') else None
            label = html.escape(Path(receipt['source']).name)
            if link:
                label = '<a href="' + html.escape(link, quote=True) + '">' + label + '</a>'
            label += '<br><small>' + receipt['source_sha256'][:12] + ' · ' + time.strftime('%m-%d %H:%M:%S', time.localtime(receipt['created'])) + '</small>'
            rows.append('<tr><td>' + label + '</td><td>' + html.escape(receipt['status']) + '</td><td>'
                + str(receipt.get('observations', '—')) + '</td><td>' + html.escape(receipt.get('error', 'Director 内部复核；不代表整片通过')) + '</td></tr>')
        content = '''<!doctype html><html lang="zh"><meta charset="utf-8"><meta http-equiv="refresh" content="15"><title>自动视频审查</title>
<style>body{font:16px system-ui;background:#f3f6f5;color:#213c38;max-width:1100px;margin:48px auto;padding:20px}table{width:100%;background:white;border-radius:12px}td,th{text-align:left;padding:16px;border-bottom:1px solid #e5eeeb}a{color:#286e63}p{line-height:1.7}</style>
<h1>自动视频技术审查</h1><p>新片与修改版本写入制作目录后自动检查，无需导入或点击。旧文件仅登记基线。报告中的现象由制作流程内部承接，不是交给用户逐条找错，也不等于整片自动验收。</p>'''
        content += '<p>最近扫描：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(state.get('heartbeat', time.time()))) + '（若长时间未更新，后台可能已停止）</p>'
        content += '<table><tr><th>视频 / 报告</th><th>扫描状态</th><th>观察数</th><th>后续责任</th></tr>' + ''.join(rows) + '</table></html>'
        temp = self.output / 'index.tmp'
        temp.write_text(content)
        os.replace(temp, self.output / 'index.html')


def review_execution(record_path, token):
    """Called after successful bound production, without replaying its command."""
    from .repair_controller import _transaction
    record_path = Path(record_path).resolve()
    record = json.loads(record_path.read_text())
    state = record['repair_controller']
    execution = state['executions'][token]
    task = state['tasks'][execution['task_id']]
    videos = []
    for value in task['outputs']:
        path = (record_path.parent / value).resolve()
        if path.suffix.lower() in EXTENSIONS:
            videos.append(path)
        elif path.is_dir():
            videos.extend(p for p in path.rglob('*') if p.is_file() and p.suffix.lower() in EXTENSIONS and not p.is_symlink())
    receipts = Monitor([], DEFAULT_OUTPUT).review(videos)
    result = dict(status='complete' if all(r['status']=='complete' for r in receipts) else 'failed',
        scope='technical_observations_only', owner='Director', formal_acceptance=False, reports=receipts)
    if not videos:
        result.update(status='no_video_outputs', reason='No declared video output; directory watcher handles later assembly')
    with _transaction(record_path) as (current, base):
        current['repair_controller']['executions'][token]['automatic_technical_review'] = result
        current['repair_controller']['tasks'][execution['task_id']]['automatic_technical_review'] = result
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', action='append', type=Path)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--interval', type=float, default=5)
    parser.add_argument('--settle', type=float, default=15)
    parser.add_argument('--port', type=int, default=8770)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    monitor = Monitor(args.root or [REPO/'series', REPO/'output', REPO/'artifacts'], args.output, args.settle)
    if args.once:
        monitor.tick()
        return
    # Lock prevents duplicate daemons; queue lock serializes hook versus watcher.
    with (monitor.output / 'daemon.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(SimpleHTTPRequestHandler, directory=str(monitor.output)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f'Automatic review: http://127.0.0.1:{args.port}', flush=True)
        while True:
            try:
                monitor.tick()
            except Exception as exc:
                atomic_json(monitor.output/'service-error.json', dict(time=time.time(), error=str(exc)))
                print(str(exc), flush=True)
            time.sleep(max(1, args.interval))


if __name__ == '__main__':
    main()
