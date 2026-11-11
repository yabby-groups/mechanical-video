"""Local A/V SDR inspector. Run with the project's official HTM runtime."""
import argparse
import json
import math
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from .htm_av_core import Source, Models, Lane, Store, compare
from .htm_waveform import runtime, sha

DEFAULT_VIDEO=Path(__file__).resolve().parent.parent/'series/everyday-mechanisms/episodes/EVERYDAY_EP03/neil-voice-20261110/Tape-measure-Neil-workprint.mp4'

class Session:
    def __init__(self,video,reference=None,output=None):
        self.root=Path(output or f'reports/htm-av-live/{uuid.uuid4().hex}').resolve()
        self.root.mkdir(parents=True,exist_ok=False)
        self.lock=threading.RLock(); self.lanes={}; self.sources={}
        self.status='initializing'; self.progress='解码 A'; self.error=None
        self.running=False; self.learning=True; self.speed=1.; self.offset=0.; self.pass_number=1
        self.clock=0.; self.compute_seconds=0.; self.events=0; self.changes=[]
        self.pass_sources={}; self.models=Models(); self.store=Store(self.root/'history.sqlite')
        self.initialization_seconds=None
        threading.Thread(target=self.initialize,args=(video,reference),daemon=True).start()
    def initialize(self,video,reference):
        began=time.monotonic()
        try:
            self.sources['A']=Source(video)
            if reference:
                self.progress='解码 B'; self.sources['B']=Source(reference)
            self.progress='初始化官方 SP/TM；同配置只初始化一次，随后复制未学习状态'
            for key,source in self.sources.items():
                self.lanes[key]=Lane(source,self.models)
            self.store.meta('sources',{k:s.metadata for k,s in self.sources.items()})
            self.store.meta('runtime',dict(**runtime(),av_core=sha(Path(__file__).with_name('htm_av_core.py')),av_live=sha(__file__)))
            self.save_pass()
            self.status='ready'; self.progress='就绪'
            self.initialization_seconds=time.monotonic()-began
            self.store.meta('initialization_seconds',self.initialization_seconds)
        except Exception as e: self.error=str(e); self.status='error'
    def save_pass(self):
        self.pass_sources[self.pass_number]=dict(self.sources)
        self.store.meta(f'pass:{self.pass_number}',dict(sources={k:s.metadata for k,s in self.sources.items()},offset=self.offset,learning=self.learning))

    def require_ready(self):
        if self.status!='ready': raise ValueError('session is not ready: '+self.status)
    def candidates(self):
        return sorted((lane.next_time(mode)+(self.offset if key=='B' else 0),key,mode)
                      for key,lane in self.lanes.items() for mode in ('video','audio'))
    def step_event(self):
        t,key,mode=self.candidates()[0]
        if not math.isfinite(t): self.running=False; return False
        began=time.monotonic(); lane=self.lanes[key]
        try:
            f=lane.step(mode,self.learning)
            self.store.put(self.pass_number,key,mode,f)
            self.clock=t; self.events+=1
        except Exception as e:
            lane.error[mode]=str(e)
        self.compute_seconds+=time.monotonic()-began
        return True
    def step_mode(self,mode,lane_key='A'):
        target=self.lanes[lane_key].next_time(mode)+(self.offset if lane_key=='B' else 0)
        if not math.isfinite(target): return
        while self.candidates()[0][0]<=target: self.step_event()
    def control(self,action,body):
        with self.lock:
            self.require_ready()
            if action=='play': self.running=True
            elif action=='pause': self.running=False
            elif action=='step':
                self.running=False
                if body.get('mode','video') not in ('video','audio') or body.get('lane','A') not in self.lanes: raise ValueError('invalid lane/mode')
                self.step_mode(body.get('mode','video'),body.get('lane','A'))
            elif action in ('restart','reset'):
                self.running=False
                for lane in self.lanes.values(): lane.restart(action=='reset')
                self.pass_number+=1; self.clock=min(0,self.offset); self.events=0; self.compute_seconds=0
                self.save_pass()
                self.changes.append(dict(action=action,pass_number=self.pass_number))
                self.store.meta('changes',self.changes)
            elif action=='settings':
                if self.running: raise ValueError('pause before changing settings')
                learning=body.get('learning',self.learning); speed=float(body.get('speed',self.speed)); offset=float(body.get('offset',self.offset))
                if type(learning)!=bool or speed not in (.1,.25,.5,1.,2.) or not math.isfinite(offset): raise ValueError('invalid settings')
                if offset!=self.offset and self.events: raise ValueError('restart before changing offset')
                self.learning=learning; self.speed=speed; self.offset=offset
                if not self.events: self.save_pass()
                self.changes.append(dict(action=action,pass_number=self.pass_number,position=self.clock,learning=learning,speed=speed,offset=offset,cursors={k:dict(l.cursor) for k,l in self.lanes.items()}))
                self.store.meta('changes',self.changes)
            else: raise ValueError('unknown action')
    def state(self):
        with self.lock:
            return dict(status=self.status,progress=self.progress,error=self.error,initialization_seconds=self.initialization_seconds,
                running=self.running,learning=self.learning,speed=self.speed,offset=self.offset,clock=self.clock,
                pass_number=self.pass_number,events=self.events,compute_seconds=self.compute_seconds,
                events_per_second=self.events/self.compute_seconds if self.compute_seconds else 0,
                media_speed=max(0,self.clock)/self.compute_seconds if self.compute_seconds else 0,
                output=str(self.root),changes=self.changes,
                lanes={k:dict(source=l.source.metadata,processed=dict(l.cursor),errors=dict(l.error)) for k,l in self.lanes.items()})
    def timelines(self,start=0,end=None,pass_number=None):
        with self.lock:
            p=pass_number or self.pass_number
            meta=self.store.get_meta(f'pass:{p}')
            if meta is None: raise ValueError('unknown pass')
            data={k:{m:self.store.timeline(p,k,m) for m in ('video','audio')} for k in meta['sources']}
            result=dict(pass_number=p,lanes=data,comparison={},sources=meta['sources'],offset=meta['offset'])
            if 'B' in data:
                for mode in ('video','audio'):
                    compatible=mode=='video' or (meta['sources']['A']['audio_config'] is not None and meta['sources']['A']['audio_config']==meta['sources']['B']['audio_config'])
                    result['comparison'][mode]=compare(data['A'][mode],data['B'][mode],start,end if end is not None else float('inf'),meta['offset']) if compatible else dict(disabled='音频配置不一致或缺少音轨，禁用数值差值')
            return result
    def loop(self):
        last=time.monotonic()
        while True:
            now=time.monotonic(); elapsed=now-last; last=now
            with self.lock:
                if self.running and self.status=='ready':
                    target=self.clock+min(elapsed,.1)*self.speed
                    while self.running and self.candidates()[0][0]<=target: self.step_event()
                    if not math.isfinite(self.candidates()[0][0]): self.running=False
                    else: self.clock=max(self.clock,target)
            time.sleep(.005)


def report_html(state,timeline):
    payload=json.dumps(dict(state=state,timeline=timeline),ensure_ascii=False).replace('<','\\u003c')
    return ('''<!doctype html><meta charset="utf-8"><title>HTM 音视频对比报告</title>
<style>body{font:16px system-ui;max-width:1100px;margin:40px auto;background:#101824;color:#e0eafa}canvas{width:100%;background:#172433}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:400px;overflow:auto}</style>
<h1>HTM 音视频对比报告</h1><p>异常表示预测新颖度，不表示缺陷或质量。B−A 仅在同模态、共同覆盖区间内计算。</p>
<div id="plots"></div><pre id="summary"></pre><details><summary>来源、配置与完整时间线</summary><pre id="raw"></pre></details>
<script>const data='''+payload+''';
for(const mode of ['video','audio']){const h=document.createElement('h2');h.textContent=mode;plots.append(h);const c=document.createElement('canvas');c.width=1000;c.height=220;plots.append(c);const ctx=c.getContext('2d');const lanes=data.timeline.lanes;const max=Math.max(1,...Object.values(data.state.lanes).map(x=>x.source.duration));for(const [k,color] of [['A','#49d9c0'],['B','#ffc777']]){ctx.strokeStyle=color;ctx.beginPath();(lanes[k]?.[mode]||[]).forEach((p,i)=>{const x=(p.start+(k==='B'?data.state.offset:0))/max*1000,y=210-p.anomaly*200;i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke()} }
summary.textContent=JSON.stringify(Object.fromEntries(Object.entries(data.timeline.comparison).map(([k,v])=>[k,Object.fromEntries(Object.entries(v).filter(([n])=>n!=='segments'))])),null,2);raw.textContent=JSON.stringify(data,null,2);</script>''').encode()

def serve(session,port):
    page=Path(__file__).with_suffix('.html').read_bytes()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def reply(self,data,ctype='application/json',status=200,filename=None):
            if not isinstance(data,bytes): data=json.dumps(data,allow_nan=False).encode()
            self.send_response(status); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store')
            if filename: self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
            self.end_headers(); self.wfile.write(data)
        def file(self,path,ctype):
            size=path.stat().st_size; start=0; end=size-1; status=200
            if self.headers.get('Range'):
                try:
                    unit,r=self.headers['Range'].split('='); a,b=r.split('-')
                    if unit!='bytes' or not a: raise ValueError()
                    start=int(a); end=min(size-1,int(b) if b else size-1)
                    if not 0<=start<=end<size: raise ValueError()
                    status=206
                except ValueError: return self.reply(b'',status=416)
            self.send_response(status); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(end-start+1)); self.send_header('Accept-Ranges','bytes')
            if status==206: self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            self.end_headers()
            with path.open('rb') as f:
                f.seek(start); left=end-start+1
                while left:
                    chunk=f.read(min(left,1024*1024)); self.wfile.write(chunk); left-=len(chunk)
        def do_GET(self):
            u=urlparse(self.path); q={k:v[0] for k,v in parse_qs(u.query).items()}
            try:
                if u.path=='/': return self.reply(page,'text/html; charset=utf-8')
                if u.path=='/api/state': return self.reply(session.state())
                if u.path=='/api/timeline': return self.reply(session.timelines(float(q.get('start',0)),float(q['end']) if 'end' in q else None,int(q['pass']) if 'pass' in q else None))
                if u.path=='/api/frame':
                    with session.lock: detail=session.store.detail(int(q.get('pass',session.pass_number)),q.get('lane','A'),q.get('mode','video'),int(q['index']))
                    return self.reply(detail)
                if u.path=='/media': return self.file(session.pass_sources[int(q.get('pass',session.pass_number))][q.get('lane','A')].path,'video/mp4')
                if u.path=='/api/export':
                    with session.lock:
                        state=session.state(); timeline=session.timelines(float(q.get('start',0)),float(q['end']) if 'end' in q else None,int(q['pass']) if 'pass' in q else None)
                        state['exported_pass']=timeline['pass_number']; state['offset']=timeline['offset']
                        state['lanes']={k:dict(source=source) for k,source in timeline['sources'].items()}
                        if q.get('format')=='html': return self.reply(report_html(state,timeline),'text/html; charset=utf-8',filename='htm-comparison.html')
                        if q.get('format')=='sqlite': return self.file(session.store.path,'application/vnd.sqlite3')
                        return self.reply(dict(state=state,timeline=timeline),filename='htm-timeline.json')
                return self.reply({'error':'not found'},status=404)
            except (ValueError,KeyError) as e: return self.reply({'error':str(e)},status=400)
            except (BrokenPipeError,ConnectionResetError): return
        def do_POST(self):
            if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{port}',f'http://localhost:{port}'):
                return self.reply({'error':'origin rejected'},status=403)
            try:
                size=int(self.headers.get('Content-Length','0'))
                if size<0: raise ValueError('invalid length')
                if self.path=='/api/reference':
                    with session.lock:
                        session.require_ready()
                        if session.running: raise ValueError('pause before importing B')
                        if size>2*1024**3: raise ValueError('file exceeds 2 GiB')
                        path=session.root/('reference-'+uuid.uuid4().hex+'.mp4')
                        with path.open('wb') as f:
                            remaining=size
                            while remaining:
                                chunk=self.rfile.read(min(1024*1024,remaining))
                                if not chunk: raise ValueError('incomplete file')
                                f.write(chunk); remaining-=len(chunk)
                        # New paired session starts both lanes from identical unlearned weights.
                        session.status='initializing'; session.progress='解码本地 B 并复制初始状态'
                    def load():
                        try:
                            source=Source(path); source.metadata['name']=unquote(self.headers.get('X-Filename',path.name)); lane=Lane(source,session.models)
                            with session.lock:
                                session.sources['B']=source; session.lanes['B']=lane
                                for l in session.lanes.values(): l.restart(True)
                                session.pass_number+=1; session.events=0; session.compute_seconds=0; session.clock=min(0,session.offset)
                                session.store.meta('sources',{k:s.metadata for k,s in session.sources.items()})
                                session.save_pass(); session.error=None; session.status='ready'; session.progress='就绪'
                        except Exception as e:
                            session.error=str(e); session.status='ready'; session.progress='B 导入失败'
                    threading.Thread(target=load,daemon=True).start()
                    return self.reply({'status':'initializing'})
                if size>4096: raise ValueError('request too large')
                body=json.loads(self.rfile.read(size) or '{}')
                if self.path!='/api/control': return self.reply({'error':'not found'},status=404)
                session.control(body['action'],body)
                return self.reply(session.state())
            except (ValueError,KeyError,TypeError) as e: return self.reply({'error':str(e)},status=400)
    threading.Thread(target=session.loop,daemon=True).start()
    print(f'HTM A/V: http://127.0.0.1:{port}  records: {session.root}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--video',default=str(DEFAULT_VIDEO)); p.add_argument('--reference'); p.add_argument('--port',type=int,default=8767); p.add_argument('--output')
    args=p.parse_args(); serve(Session(args.video,args.reference,args.output),args.port)
if __name__=='__main__': main()
