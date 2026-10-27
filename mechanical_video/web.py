"""Loopback workbench: image handoff, cached CAD production and streamed playback."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import threading
from urllib.parse import urlsplit
from .cli import ROOT, TEMPLATES, connect, analyze, enqueue
from .model import build
from .config import vision_model

PAGE='''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>机械视频工作台</title>
<style>body{background:#101927;color:#dce9f6;font:16px system-ui;max-width:1120px;margin:36px auto;padding:0 20px}h1{font-size:32px}p{color:#afc3d8}section,article{background:#182638;padding:20px;border-radius:12px;margin:18px 0}label{display:inline-block;margin:8px}button,select,input{background:#24384e;color:#fff;border:1px solid #49647e;border-radius:6px;padding:10px}button{cursor:pointer;background:#12668a}button:disabled{opacity:.5}#videos{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}video{width:100%;max-height:340px}article{margin:0}h3{margin-top:0}#result{white-space:pre-wrap}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #30465e}.pill{color:#8ee2bc}a{color:#8ad6ff}</style>
<h1>机械视频工作台</h1><p>复用独立 CAD 零件，批量生成拆解、传动和装配视频。当前模型家族：行星减速器；内部结构及估计尺寸均为推测。</p>
<section><h2>生成视频</h2><p id="vision">正在检查图片识别服务…</p>
<label>主题 <select id="template"><option value="all">全部十种主题</option><option value="explode">完整爆炸图</option><option value="shell">外壳拆解</option><option value="overview">360°展示</option><option value="internals">内部零件</option><option value="gears">齿轮传动</option><option value="closeup">零件特写</option><option value="transparent">透明外壳</option><option value="assembly">反向组装</option><option value="working">工作过程</option><option value="explanation">完整讲解</option></select></label>
<label>画幅 <select id="portrait"><option value="false">横屏 16:9</option><option value="true">竖屏 9:16</option></select></label>
<label>分辨率 <select id="production"><option value="false">720p 测试</option><option value="true">1080p 生产</option></select></label>
<label>时长（秒） <input id="seconds" type="number" min="1" max="120" value="5" style="width:70px"></label>
<label>引擎 <select id="engine"><option value="eevee">Eevee</option><option value="cycles">Cycles Metal</option></select></label>
<p><input id="file" type="file" accept="image/png,image/jpeg,image/webp"> <button id="upload">分析图片并生成</button></p>
<p><label>示例模数（mm） <input id="module" type="number" min="0.5" max="5" step="0.1" value="2" style="width:70px"></label><button id="batch">复用示例模型生成</button></p><div id="result" role="status"></div></section>
<h2>视频资产</h2><div id="videos"></div><section><h2>任务队列</h2><p id="summary"></p><table><thead><tr><th>主题 / 画幅</th><th>状态</th><th>尝试次数</th><th>任务编号 / 异常</th></tr></thead><tbody id="jobs"></tbody></table></section>
<script>
const names={overview:'360°展示',shell:'外壳拆解',internals:'内部零件',explode:'完整爆炸图',gears:'齿轮传动',closeup:'零件特写',transparent:'透明外壳',assembly:'反向组装',working:'工作过程',explanation:'完整讲解'};
const states={pending:'等待中',running:'生成中',done:'已完成',failed:'失败'};
const el=id=>document.getElementById(id);let shown='';
function options(){let t=el('template').value;return {templates:t==='all'?Object.keys(names):[t],portrait:el('portrait').value==='true',production:el('production').value==='true',seconds:Number(el('seconds').value),module:Number(el('module').value),engine:el('engine').value}}
async function submit(upload){el('batch').disabled=true;el('upload').disabled=true;el('result').textContent='正在准备任务…';try{let opts=options(),r;if(upload){let f=el('file').files[0];if(!f)throw Error('请先选择产品图片');r=await fetch('/upload',{method:'POST',headers:{'Content-Type':f.type,'X-Render-Options':JSON.stringify(opts)},body:f})}else{r=await fetch('/batch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(opts)})}let data=await r.json();if(!r.ok)throw Error(data.error);el('result').textContent='新增 '+data.created+' 个任务，复用已有任务 '+data.existing+' 个。';await refresh()}catch(e){el('result').textContent=e.message}finally{el('batch').disabled=false;el('upload').disabled=false}}
el('batch').onclick=()=>submit(false);el('upload').onclick=()=>submit(true);
function cell(row,value){let td=document.createElement('td');td.textContent=value;row.append(td)}
async function refresh(){try{let r=await fetch('/status'),rows=await r.json();rows=rows.filter(j=>j.state!=='superseded');el('summary').textContent=rows.filter(j=>j.state==='done').length+' 已完成 / '+rows.length+' 个任务';let tbody=el('jobs');tbody.replaceChildren();for(let j of rows){let tr=document.createElement('tr');cell(tr,(names[j.template]||j.template)+' / '+j.width+'×'+j.height);cell(tr,states[j.state]||j.state);cell(tr,j.attempts);cell(tr,j.error||j.id);tbody.append(tr)}let done=rows.filter(j=>j.state==='done'),key=done.map(j=>j.id).join(',');if(key!==shown){shown=key;el('videos').replaceChildren();for(let j of done){let card=document.createElement('article'),title=document.createElement('h3'),v=document.createElement('video'),p=document.createElement('p');title.textContent=names[j.template]||j.template;v.controls=true;v.preload='metadata';v.src='/video/'+j.id;p.textContent=j.width+'×'+j.height+' · '+j.seconds+' 秒 · '+j.engine+' · H.264';card.append(title,v,p);el('videos').append(card)}}}catch(e){el('summary').textContent='连接失败：'+e.message}}
fetch('/config').then(r=>r.json()).then(c=>{el('vision').textContent='图片识别模型：'+c.vision_model+'。'+(c.vision_configured?'识别服务已配置，上传图片将发送至配置的服务。':'识别服务尚未配置；可以先使用示例模型生成视频。')});refresh();setInterval(refresh,5000);
</script></html>'''

def render_options(data):
    if not isinstance(data,dict): raise ValueError('Options must be an object')
    templates=data.get('templates',TEMPLATES)
    if not isinstance(templates,list) or not templates or any(t not in TEMPLATES for t in templates):
        raise ValueError('Select supported templates')
    for flag in ('portrait','production'):
        if flag in data and not isinstance(data[flag],bool): raise ValueError(f'{flag} must be boolean')
    engine=data.get('engine','eevee')
    if engine not in ('eevee','cycles'): raise ValueError('Unknown renderer')
    return dict(templates=list(dict.fromkeys(templates)),portrait=data.get('portrait',False),production=data.get('production',False),seconds=float(data.get('seconds',5)),engine=engine)

def serve(root=None,port=8766):
    root=root or ROOT/'artifacts'; root.mkdir(parents=True,exist_ok=True)
    analysis_lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def send(self,status,body,kind='application/json'):
            payload=body.encode(); self.send_response(status); self.send_header('Content-Type',kind+'; charset=utf-8'); self.send_header('Content-Length',str(len(payload))); self.end_headers(); self.wfile.write(payload)
        def do_GET(self):
            path=urlsplit(self.path).path
            if path=='/': return self.send(200,PAGE,'text/html')
            if path=='/config': return self.send(200,json.dumps({'vision_configured':bool(os.environ.get('VISION_ENDPOINT')),'vision_model':vision_model()}))
            if path=='/status':
                db=connect(root); rows=[]
                for r in db.execute('SELECT id,spec,state,attempts,error FROM jobs ORDER BY updated DESC'):
                    j=json.loads(r['spec']); rows.append({k:r[k] for k in ('id','state','attempts','error')}|{k:j[k] for k in ('template','width','height','seconds')}|{'engine':j.get('engine','eevee')})
                db.close(); return self.send(200,json.dumps(rows))
            if path.startswith('/video/'):
                key=path.removeprefix('/video/')
                if not re.fullmatch('[0-9a-f]{20}',key): return self.send(404,'{}')
                db=connect(root); row=db.execute("SELECT spec FROM jobs WHERE id=? AND state='done'",(key,)).fetchone(); db.close()
                if not row: return self.send(404,'{}')
                video=Path(json.loads(row['spec'])['directory'])/'video.mp4'
                if not video.is_file(): return self.send(404,'{}')
                size=video.stat().st_size; start,end=0,size-1; partial=self.headers.get('Range')
                if partial:
                    match=re.fullmatch(r'bytes=(\d*)-(\d*)',partial)
                    if not match or not any(match.groups()): return self.unsatisfied(size)
                    first,last=match.groups()
                    if first: start=int(first); end=min(int(last),size-1) if last else size-1
                    else: start=max(0,size-int(last))
                    if start>end or start>=size: return self.unsatisfied(size)
                self.send_response(206 if partial else 200); self.send_header('Content-Type','video/mp4'); self.send_header('Accept-Ranges','bytes'); self.send_header('Content-Length',str(end-start+1))
                if partial: self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                self.end_headers()
                try:
                    with video.open('rb') as f:
                        f.seek(start); remaining=end-start+1
                        while remaining:
                            block=f.read(min(256*1024,remaining))
                            if not block: break
                            self.wfile.write(block); remaining-=len(block)
                except (BrokenPipeError,ConnectionResetError): pass
                return
            self.send(404,'{}')
        def unsatisfied(self,size):
            self.send_response(416); self.send_header('Content-Range',f'bytes */{size}'); self.send_header('Content-Length','0'); self.end_headers()
        def do_POST(self):
            path=urlsplit(self.path).path
            if path not in ('/upload','/batch'): return self.send(404,'{}')
            origin=self.headers.get('Origin')
            if origin and origin!=f'http://127.0.0.1:{port}': return self.send(403,'{"error":"origin rejected"}')
            try: length=int(self.headers.get('Content-Length','0'))
            except ValueError: return self.send(400,'{"error":"Invalid content length"}')
            if not 0<length<=20*1024*1024: return self.send(413,'{"error":"Request limit: 20MB"}')
            if not analysis_lock.acquire(blocking=False): return self.send(409,'{"error":"另一项建模或图片分析正在进行，请稍后重试"}')
            temporary=None
            try:
                if path=='/batch':
                    if length>16384: raise ValueError('Options limit: 16KB')
                    data=json.loads(self.rfile.read(length)); opts=render_options(data)
                    manifest=build(root,{'module':float(data.get('module',2))})
                else:
                    import tempfile
                    suffix={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}.get(self.headers.get('Content-Type'))
                    if not suffix: return self.send(415,'{"error":"PNG/JPEG/WebP required"}')
                    opts=render_options(json.loads(self.headers.get('X-Render-Options','{}')))
                    with tempfile.NamedTemporaryFile(suffix=suffix,dir=root,delete=False) as f:
                        temporary=Path(f.name); f.write(self.rfile.read(length))
                    manifest=analyze(temporary,root)
                jobs=enqueue(root,manifest,**opts)
                self.send(200,json.dumps({'jobs':jobs,'created':sum(j['created'] for j in jobs),'existing':sum(not j['created'] for j in jobs)}))
            except Exception as exc: self.send(422,json.dumps({'error':str(exc)},ensure_ascii=False))
            finally:
                if temporary: temporary.unlink(missing_ok=True)
                analysis_lock.release()
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'http://127.0.0.1:{port}',flush=True); server.serve_forever()
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8766); args=parser.parse_args()
    serve(port=args.port)
