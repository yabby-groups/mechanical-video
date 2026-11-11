"""Timecoded technical observations with explicit limits, not a perceptual verdict."""
import argparse
from dataclasses import asdict, dataclass
import hashlib
import html
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import numpy as np
from .htm_av_core import Source, probe
from .htm_waveform import decode

KINDS=('black','freeze','flash','dropout','clipping')
NAMES={'black':'近黑画面','freeze':'画面停滞','flash':'短时亮度闪变','dropout':'音频静音段','clipping':'满幅削波特征'}
LIMITS={
 'black':'黑场、淡入淡出可能是有意设计；仅确认近黑像素现象。',
 'freeze':'静态镜头、低运动画面可能正常；不据此断言播放器卡帧。',
 'flash':'闪光或短促转场可能有意；不等同于光敏安全评估。',
 'dropout':'呼吸停顿、静音或无声声道可能正常；不证明漏字或录音故障。',
 'clipping':'检测数字满幅平台；不能检出低电平的历史削波或所有爆音。'}

@dataclass(frozen=True)
class Policy:
    version: str='av-technical-v3'
    black_level: float=12.
    black_fraction: float=.98
    black_min_seconds: float=.10
    freeze_difference: float=.10
    freeze_min_seconds: float=.50
    flash_jump: float=45.
    flash_return_difference: float=20.
    flash_max_seconds: float=.16
    silence_db: float=-65.
    silence_min_seconds: float=.08
    clip_level: float=.995
    clip_min_run: int=8
    clip_flat_tolerance: float=1e-6
    clip_min_fraction: float=.01
    htm_anomaly_threshold: float=.8

DEFAULT=Policy()

def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def policy_hash(policy):
    return hashlib.sha256(json.dumps(asdict(policy),sort_keys=True).encode()).hexdigest()

def intervals(mask,starts,ends,minimum=0.,gap=0.):
    """Union contiguous flagged observations; preserve native interval endpoints."""
    output=[]
    for flag,a,b in zip(mask,starts,ends):
        if not flag:continue
        a,b=float(a),float(b)
        if output and a<=output[-1][1]+gap+1e-7:output[-1][1]=max(b,output[-1][1])
        else:output.append([a,b])
    return [r for r in output if r[1]-r[0]>=minimum-1e-7]

def union_duration(rows):
    if not rows:return 0.
    merged=[]
    for a,b in sorted(rows):
        if merged and a<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],b)
        else:merged.append([a,b])
    return sum(b-a for a,b in merged)

def analyze_arrays(rgb,valid,starts,ends,samples=None,rate=None,audio_start=0.,policy=DEFAULT):
    """Every source frame and sample is consumed; observations remain context-sensitive."""
    rgb=np.asarray(rgb);starts=np.asarray(starts,float);ends=np.asarray(ends,float)
    if rgb.ndim!=4 or rgb.shape[1:]!=(64,64,3) or valid.shape!=(64,64):raise ValueError('invalid video geometry')
    if len(rgb)!=len(starts) or len(ends)!=len(starts) or not len(rgb) or np.any(ends<=starts) or np.any(np.diff(starts)<=0):raise ValueError('invalid frame intervals')
    pixels=rgb[:,valid,:].astype(np.float32)
    if pixels.shape[1]==0:raise ValueError('no valid pixels')
    luma=np.einsum('nvc,c->nv',pixels,np.array([.2126,.7152,.0722],np.float32))
    brightness=luma.mean(axis=1)
    black_fraction=(luma<=policy.black_level).mean(axis=1)
    difference=np.r_[np.nan,np.mean(np.abs(np.diff(pixels,axis=0)),axis=(1,2))]
    findings=[]
    def add(kind,a,b,evidence,channel=None):
        item=dict(kind=kind,start=float(a),end=float(b),status='OBSERVED_REQUIRES_CONTEXT',
            description=NAMES[kind],evidence=evidence,limitation=LIMITS[kind],channel=channel,
            severity=None,automatic_repair=False)
        findings.append(item)
    for a,b in intervals(black_fraction>=policy.black_fraction,starts,ends,policy.black_min_seconds):
        selected=(starts<b)&(ends>a)
        add('black',a,b,dict(min_black_fraction=float(black_fraction[selected].min()),pixel_level=policy.black_level,analysis_resolution='64x64 valid RGB pixels'))
    # The equal pair includes its preceding frame. A one-frame shot is not a freeze.
    equal=difference[1:]<=policy.freeze_difference
    boundaries=np.flatnonzero(np.diff(np.r_[False,equal,False].astype(int)))
    for lo,hi in zip(boundaries[::2],boundaries[1::2]):
        a,b=starts[lo],ends[hi]
        if b-a<policy.freeze_min_seconds-1e-7:continue
        add('freeze',a,b,dict(max_internal_mean_rgb_difference=float(difference[lo+1:hi+1].max()),threshold=policy.freeze_difference))
    pulses=[]
    for i in range(1,len(rgb)-1):
        jump=float(brightness[i]-brightness[i-1])
        if abs(jump)<policy.flash_jump:continue
        for j in range(i+1,len(rgb)):
            if starts[j]-starts[i]>policy.flash_max_seconds+1e-7:break
            if abs(float(brightness[j]-brightness[i-1]))<=policy.flash_return_difference:
                delta=brightness[i:j]-brightness[i-1]
                if np.all(np.sign(delta)==np.sign(jump)) and np.min(abs(delta))>=policy.flash_jump:
                    pulses.append((float(starts[i]),float(starts[j]),float(np.max(abs(delta)))))
                break
    merged=intervals([True]*len(pulses),[p[0] for p in pulses],[p[1] for p in pulses])
    for a,b in merged:add('flash',a,b,dict(max_mean_luma_excursion=max(d for x,y,d in pulses if x<b and y>a),return_window=policy.flash_max_seconds))
    audio_rows=[]
    if samples is not None:
        samples=np.asarray(samples)
        if samples.ndim!=2 or not len(samples) or not rate or rate<=0 or not np.isfinite(samples).all():raise ValueError('invalid native PCM')
        for i in range((len(samples)*1000+rate*10-1)//(rate*10)):
            lo=i*rate//100;hi=min(len(samples),(i+1)*rate//100)
            frame=samples[lo:hi]
            rms=np.sqrt(np.mean(np.square(frame.astype(np.float64)),axis=0))
            peak=np.max(abs(frame),axis=0)
            fraction=np.mean(abs(frame)>=policy.clip_level,axis=0)
            runs=[]
            for ch in range(samples.shape[1]):
                mask=abs(frame[:,ch])>=policy.clip_level
                # Require a same-sign rail plateau, not just a loud sine-wave peak.
                starts_run=np.r_[True,(mask[1:]!=mask[:-1])|(np.sign(frame[1:,ch])!=np.sign(frame[:-1,ch]))|(np.abs(np.diff(frame[:,ch]))>policy.clip_flat_tolerance)]
                boundaries=np.r_[np.flatnonzero(starts_run),len(mask)]
                runs.append(max((int(b-a) for a,b in zip(boundaries[:-1],boundaries[1:]) if mask[a]),default=0))
            audio_rows.append(dict(start=audio_start+lo/rate,end=audio_start+hi/rate,
                start_sample=lo,end_sample=hi,rms_db=(20*np.log10(np.maximum(rms,1e-12))).tolist(),
                peak=peak.tolist(),rail_fraction=fraction.tolist(),max_rail_run=runs))
        ast=np.array([r['start'] for r in audio_rows]);aen=np.array([r['end'] for r in audio_rows])
        for ch in range(samples.shape[1]):
            db=np.array([r['rms_db'][ch] for r in audio_rows]); fractions=np.array([r['rail_fraction'][ch] for r in audio_rows]);runs=np.array([r['max_rail_run'][ch] for r in audio_rows])
            for a,b in intervals(db<=policy.silence_db,ast,aen,policy.silence_min_seconds):
                sel=(ast<b)&(aen>a)
                add('dropout',a,b,dict(max_rms_db=float(db[sel].max()),threshold_db=policy.silence_db,frame_ms=10),ch)
            for a,b in intervals((fractions>=policy.clip_min_fraction)&(runs>=policy.clip_min_run),ast,aen,gap=.02):
                sel=(ast<b)&(aen>a)
                add('clipping',a,b,dict(max_rail_fraction=float(fractions[sel].max()),max_flat_rail_samples=int(runs[sel].max()),flat_tolerance=policy.clip_flat_tolerance,level=policy.clip_level),ch)
    findings.sort(key=lambda r:(r['start'],r['kind'],-1 if r['channel'] is None else r['channel']))
    for i,f in enumerate(findings):f['id']=f'TECH-{i+1:04d}'
    return dict(findings=findings,video_metrics=[dict(index=i,start=float(a),end=float(b),mean_luma=float(brightness[i]),black_fraction=float(black_fraction[i]),mean_rgb_difference=None if i==0 else float(difference[i])) for i,(a,b) in enumerate(zip(starts,ends))],audio_metrics=audio_rows,
        coverage=dict(video_frames=len(rgb),audio_samples=len(samples) if samples is not None else 0,audio_channels=samples.shape[1] if samples is not None else 0))

def attach_htm(database,source_hash,lane='A',pass_number=None,threshold=.8):
    """Read only fingerprint-matched records; never interpret novelty as a defect."""
    path=Path(database).resolve()
    if not path.is_file():raise ValueError('HTM history missing')
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    try:
        passes=[int(k.split(':')[1]) for (k,) in db.execute("SELECT key FROM metadata WHERE key LIKE 'pass:%'")]
        p=pass_number if pass_number is not None else max(passes)
        row=db.execute('SELECT value FROM metadata WHERE key=?',(f'pass:{p}',)).fetchone()
        if not row:raise ValueError('HTM pass missing')
        meta=json.loads(row[0]);src=meta['sources'].get(lane)
        if not src or src['sha256']!=source_hash:raise ValueError('HTM source hash mismatch')
        config=src.get('video_config',{})
        if config.get('potentialRadius')!=786432:raise ValueError('unvalidated or zero-connected visual configuration')
        sequences={};candidates=[];processed={}
        for mode in ('video','audio'):
            rows=[dict(index=i,start=a,end=b,anomaly=x,prediction_hit_rate=h) for i,a,b,x,h in db.execute('SELECT idx,start,end,anomaly,hit FROM frames WHERE pass=? AND lane=? AND mode=? ORDER BY idx',(p,lane,mode))]
            sequences[mode]=rows;processed[mode]=len(rows)
            expected=src['video_frames'] if mode=='video' else (int(np.ceil(src['audio_samples']*1000/(src['audio_config']['rate']*src['audio_config']['frame_ms']))) if src['audio_config'] else 0)
            if len(rows)>expected or any(r['index']!=i for i,r in enumerate(rows)):raise ValueError('invalid HTM timeline coverage')
            for a,b in intervals([r['index']>0 and r['anomaly']>=threshold for r in rows],[r['start'] for r in rows],[r['end'] for r in rows],.03 if mode=='audio' else .1):
                candidates.append(dict(kind='htm_novelty',mode=mode,start=a,end=b,status='UNQUALIFIED_NOVELTY',threshold=threshold))
        return dict(status='NOVELTY_ONLY',database=str(path),pass_number=p,lane=lane,source_sha256=source_hash,
            initial_learning_state=meta.get('learning'),learning_state_note='Online history may include paused setting changes; not frozen inference',usage='supporting context only; no defect vote or automatic pass',
            threshold_is_calibrated=False,processed=processed,expected_video_frames=src['video_frames'],
            candidates=candidates,timeline=sequences)
    finally:db.close()

def make_report(source,policy=DEFAULT,htm_database=None,lane='A',pass_number=None):
    begun=time.monotonic();src=Source(source)
    samples=src.samples;cfg=src.audio_config;audio_start=getattr(src,'audio_start',0.)
    audio_error=src.audio_error
    # The encoder refuses out-of-range PCM, but the saturation detector must inspect it.
    if audio_error and 'fixed PCM range' in audio_error:
        cfg,samples=decode(source)
        streams=probe(source,'-show_streams')['streams'];a=next(s for s in streams if s['codec_type']=='audio')
        if a.get('duration'):samples=samples[:round(float(a['duration'])*cfg.rate)]
        audio_start=float(a.get('start_time',0))-src.origin;audio_error=None
    data=analyze_arrays(src.rgb,src.valid,src.pts,src.ends,samples,cfg.rate if cfg else None,audio_start,policy)
    htm=dict(status='NOT_ATTACHED',reason='No matching HTM history supplied; deterministic inspection does not require it.')
    if htm_database:
        try:htm=attach_htm(htm_database,src.hash,lane,pass_number,policy.htm_anomaly_threshold)
        except (ValueError,KeyError,sqlite3.Error) as exc:htm=dict(status='REJECTED',reason=str(exc))
    for finding in data['findings']:
        mode='audio' if finding['kind'] in ('dropout','clipping') else 'video'
        overlap=[c for c in htm.get('candidates',[]) if c['mode']==mode and c['start']<finding['end'] and c['end']>finding['start']]
        finding['htm_context']=dict(novelty_overlap=bool(overlap),intervals=overlap,meaning='co-occurrence only, not corroborated defect truth')
    return dict(schema_version=1,review_kind='bounded_technical_review',
        status='INCOMPLETE' if audio_error else ('OBSERVATIONS_FOUND' if data['findings'] else 'NO_OBSERVATIONS_IN_CHECKED_SCOPE'),
        source=dict(path=str(Path(source).resolve()),sha256=src.hash,name=Path(source).name,duration=src.duration),
        policy=asdict(policy),policy_sha256=policy_hash(policy),implementation_sha256=digest(__file__),
        qualification='UNQUALIFIED_FOR_PRODUCTION',formal_acceptance=False,automatic_repair=False,
        coverage=dict(**data['coverage'],frame_order='all native PTS',video_spatial_analysis='64x64 RGB; not full-resolution spatial QA',audio_rate=cfg.rate if cfg else None,audio_error=audio_error),
        unchecked=['mechanical correctness','caption/action alignment','narration completeness','speech intelligibility','audiovisual synchrony','audience appeal','all other defect types'],
        findings=data['findings'],metrics=dict(video=data['video_metrics'],audio=data['audio_metrics']),htm=htm,
        elapsed_seconds=time.monotonic()-begun)

def render_html(report):
    payload=json.dumps(report,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>视频技术审查</title><style>
body{font:14px/1.6 system-ui;background:#f3f6f5;color:#213a36;max-width:1200px;margin:30px auto;padding:0 20px}h1{font-size:25px}header,section{background:white;border:1px solid #dfe8e4;border-radius:12px;padding:22px;margin:16px 0}video{width:100%;height:360px;background:#15232a;border-radius:8px}button,a{color:#167968}button{background:#eff8f5;border:1px solid #c7dfd6;border-radius:6px;padding:8px;cursor:pointer}table{width:100%;border-collapse:collapse}th,td{text-align:left;border-bottom:1px solid #e4ece9;padding:12px;vertical-align:top}small,p{color:#68817a}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:300px;overflow:auto}#rows:empty:after{content:'已检查范围内未发现符合阈值的现象；这不是整片合格结论。'}@media(max-width:700px){table,tbody,tr,td{display:block}thead{display:none}video{height:280px}}
</style><header><h1>视频技术审查</h1><p id="identity"></p><b id="status"></b><p>当前为技术现象审查。需结合创作意图区分故障与正常片段；不提供整片通过结论。</p></header>
<section><video id="player" src="media.mp4" controls preload="metadata"></video><p id="coverage"></p></section>
<section><h2>定位与证据</h2><table><thead><tr><th>位置</th><th>发现</th><th>测量证据</th><th>解释边界</th></tr></thead><tbody id="rows"></tbody></table></section>
<section><h2>HTM 辅助观察</h2><p id="htmStatus"></p><p>预测新颖度不自动变成缺陷。未重合的 HTM 可疑片段仍保留，供补查。</p><details><summary>查看 HTM 可疑片段</summary><pre id="novelty"></pre></details></section>
<section><h2>未覆盖能力</h2><p id="unchecked"></p><a href="report.json" download>下载完整 JSON</a><details><summary>配置与覆盖记录</summary><pre id="meta"></pre></details></section>
<script>const $=id=>document.getElementById(id);const report='''+payload+''';$('identity').textContent=report.source.name+' · SHA-256 '+report.source.sha256;$('status').textContent=report.status;$('coverage').textContent=`覆盖 ${report.coverage.video_frames} 个视频帧 / ${report.coverage.audio_samples} 个音频样本 · 分析画面 64×64 · ${report.coverage.audio_rate||'无音轨'} Hz`;
for(const f of report.findings){const tr=document.createElement('tr'),pos=document.createElement('td'),b=document.createElement('button');b.textContent=f.start.toFixed(3)+'–'+f.end.toFixed(3)+' s';b.onclick=()=>{$('player').currentTime=Math.max(0,f.start-.25);$('player').play().catch(()=>{})};pos.append(b);const name=document.createElement('td');name.textContent=f.description+(f.channel===null?'':' · 声道 '+(f.channel+1));const e=document.createElement('td');e.textContent=JSON.stringify(f.evidence);const l=document.createElement('td');l.textContent=f.limitation;tr.append(pos,name,e,l);$('rows').append(tr)}$('htmStatus').textContent=report.htm.status;$('novelty').textContent=JSON.stringify(report.htm.candidates||[],null,2);$('unchecked').textContent=report.unchecked.join(' / ');$('meta').textContent=JSON.stringify({policy:report.policy,coverage:report.coverage,qualification:report.qualification,implementation:report.implementation_sha256},null,2);</script></html>'''

def write_review(source,output,display_name=None,**kwargs):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    report=make_report(source,**kwargs)
    if display_name:report['source']['name']=display_name
    shutil.copy2(source,output/'media.mp4')
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
    (output/'index.html').write_text(render_html(report))
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('video');p.add_argument('--output',required=True);p.add_argument('--htm-database');p.add_argument('--lane',default='A',choices=['A','B']);p.add_argument('--pass-number',type=int)
    a=p.parse_args();r=write_review(a.video,a.output,htm_database=a.htm_database,lane=a.lane,pass_number=a.pass_number)
    print(json.dumps({k:r[k] for k in ('status','coverage','qualification','elapsed_seconds')},ensure_ascii=False))
if __name__=='__main__':main()
