"""Local review workspace: reuse an existing HTM session and add technical review jobs."""
import argparse
import hashlib
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading
import time
from urllib.parse import urlparse,parse_qs
import urllib.request
import uuid
from .av_technical_review import write_review, digest

class Jobs:
    def __init__(self,root,upstream):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.upstream=upstream;self.lock=threading.Lock();self.jobs={}
    def read_upstream(self,path):
        with urllib.request.urlopen(f'http://127.0.0.1:{self.upstream}'+path,timeout=30) as r:return json.load(r)
    def save(self,job):
        (self.root/job['id']/'status.json').write_text(json.dumps(job,ensure_ascii=False,indent=2))
    def start(self,lane,pass_number=None):
        if lane not in ('A','B'):raise ValueError('invalid lane')
        with self.lock:
            if any(j['status']=='processing' for j in self.jobs.values()):raise ValueError('已有审查正在运行，请等待完成')
            state=self.read_upstream('/api/state')
            if state['status']!='ready':raise ValueError('请等待模型初始化完成')
            p=int(pass_number if pass_number is not None else state['pass_number'])
            timeline=self.read_upstream(f'/api/timeline?pass={p}')
            if lane not in timeline['sources']:raise ValueError('该轮次不存在所选视频')
            source=timeline['sources'][lane];identity=uuid.uuid4().hex
            job=dict(id=identity,status='processing',progress='读取原始媒体',lane=lane,pass_number=p,
                source=source,created=time.time(),elapsed_seconds=0)
            (self.root/identity).mkdir();self.jobs[identity]=job;self.save(job)
            threading.Thread(target=self.work,args=(job,state['output']),daemon=True).start()
            return dict(job)
    def work(self,job,session_output):
        start=time.monotonic();directory=self.root/job['id'];media=directory/'input.mp4'
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.upstream}/media?lane={job['lane']}&pass={job['pass_number']}",timeout=120) as r, media.open('xb') as f:
                while block:=r.read(1024*1024):f.write(block)
            if digest(media)!=job['source']['sha256']:raise ValueError('媒体指纹变化，停止审查')
            job['progress']='逐帧和逐样本检查；关联 HTM 响应';self.save(job)
            report=write_review(media,directory/'report',display_name=job['source']['name'],htm_database=Path(session_output)/'history.sqlite',lane=job['lane'],pass_number=job['pass_number'])
            job.update(status='complete',progress='技术审查完成',report_url=f"/reviews/{job['id']}/index.html",report_status=report['status'],
                finding_count=len(report['findings']),counts={k:sum(f['kind']==k for f in report['findings']) for k in ('black','freeze','flash','dropout','clipping')},
                htm_status=report['htm']['status'],coverage=report['coverage'],qualification=report['qualification'],
                notice='检测到的现象需结合语境；不代表整片已通过审查')
            media.unlink()  # This job's downloaded staging copy only; report/media.mp4 retained.
        except Exception as exc:job.update(status='failed',progress='审查未完成',error=str(exc))
        finally:job['elapsed_seconds']=time.monotonic()-start;self.save(job)
    def get(self,identity):
        if not re.fullmatch('[0-9a-f]{32}',identity):raise ValueError('invalid review id')
        if identity in self.jobs:return dict(self.jobs[identity])
        path=self.root/identity/'status.json'
        if not path.is_file():raise ValueError('review not found')
        job=json.loads(path.read_text())
        if job['status']=='processing':job.update(status='failed',error='审查进程已停止，未标记完成')
        return job

def serve(jobs,port):
    page=Path(__file__).with_name('htm_av_live.html')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,data,status=200,ctype='application/json'):
            if not isinstance(data,bytes):data=json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
        def local_file(self,path,ctype):
            size=path.stat().st_size;start=0;end=size-1;status=200
            if self.headers.get('Range'):
                try:
                    unit,span=self.headers['Range'].split('=');a,b=span.split('-')
                    if unit!='bytes' or not a:raise ValueError()
                    start=int(a);end=min(int(b) if b else size-1,size-1)
                    if not 0<=start<=end<size:raise ValueError()
                    status=206
                except ValueError:return self.reply(b'',status=416)
            self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes')
            if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            self.end_headers()
            with path.open('rb') as f:
                f.seek(start);left=end-start+1
                while left:
                    b=f.read(min(left,1024*1024));self.wfile.write(b);left-=len(b)
        def proxy(self):
            conn=HTTPConnection('127.0.0.1',jobs.upstream,timeout=120)
            try:
                conn.putrequest(self.command,self.path)
                for k,v in self.headers.items():
                    if k.lower() not in ('host','connection','origin'):conn.putheader(k,v)
                if self.headers.get('Origin'):conn.putheader('Origin',f'http://127.0.0.1:{jobs.upstream}')
                conn.endheaders();left=int(self.headers.get('Content-Length',0))
                while left:
                    block=self.rfile.read(min(left,1024*1024))
                    if not block:raise ValueError('incomplete upload')
                    conn.send(block);left-=len(block)
                result=conn.getresponse();self.send_response(result.status)
                for k,v in result.getheaders():
                    if k.lower() not in ('server','date','connection','transfer-encoding'):self.send_header(k,v)
                self.end_headers()
                while b:=result.read(1024*1024):self.wfile.write(b)
            finally:conn.close()
        def route(self):
            origin=self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{port}',f'http://localhost:{port}'):
                return self.reply({'error':'origin rejected'},status=403)
            u=urlparse(self.path);query=parse_qs(u.query)
            try:
                if self.command=='GET' and u.path=='/':return self.reply(page.read_bytes(),ctype='text/html; charset=utf-8')
                if self.command=='GET' and u.path=='/api/review/capabilities':return self.reply(dict(available=True,kinds=['black','freeze','flash','dropout','clipping'],formal_acceptance=False))
                if self.command=='POST' and u.path=='/api/review/start':
                    length=int(self.headers.get('Content-Length',0))
                    if not 0<=length<=4096:raise ValueError('request too large')
                    body=json.loads(self.rfile.read(length) or '{}')
                    return self.reply(jobs.start(body.get('lane','A'),body.get('pass_number')),status=202)
                if self.command=='GET' and u.path=='/api/review/status':return self.reply(jobs.get(query.get('id',[''])[0]))
                if self.command=='GET' and u.path.startswith('/reviews/'):
                    match=re.fullmatch(r'/reviews/([0-9a-f]{32})/(index.html|report.json|media.mp4)',u.path)
                    if not match:return self.reply({'error':'not found'},status=404)
                    identity,name=match.groups();job=jobs.get(identity)
                    if job['status']!='complete':raise ValueError('review not complete')
                    return self.local_file(jobs.root/identity/'report'/name,{'index.html':'text/html; charset=utf-8','report.json':'application/json','media.mp4':'video/mp4'}[name])
                return self.proxy()
            except (BrokenPipeError,ConnectionResetError):return
            except (ValueError,KeyError,TypeError) as exc:return self.reply({'error':str(exc)},status=400)
            except Exception as exc:return self.reply({'error':str(exc)},status=502)
        do_GET=route
        do_POST=route
    print(f'Technical review workspace: http://127.0.0.1:{port} -> HTM {jobs.upstream}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8768);p.add_argument('--upstream',type=int,default=8769);p.add_argument('--output',default='reports/av-review-jobs')
    a=p.parse_args();serve(Jobs(a.output,a.upstream),a.port)
if __name__=='__main__':main()
