"""Lossless event scheduling and disk-backed official HTM inspection."""
import gzip
import json
import pickle
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import numpy as np
from .htm_waveform import Config, Engine, sha

VIDEO_CONFIG = dict(inputDimensions=[786432], columnDimensions=[2048],
                    globalInhibition=True, potentialRadius=786432, potentialPct=.01, seed=42)
TM_CONFIG = dict(columnDimensions=[2048], cellsPerColumn=32)

def probe(path, *args):
    return json.loads(subprocess.check_output(['ffprobe','-v','error',*args,'-of','json',str(path)]))

def encode_rgb(rgb, valid):
    rgb = np.asarray(rgb, dtype=np.uint8)
    if rgb.shape != (64,64,3) or valid.shape != (64,64):
        raise ValueError('expected 64x64 RGB and validity mask')
    addresses = np.arange(64*64*3, dtype=np.uint32).reshape(64,64,3)*64
    return (addresses + rgb.astype(np.uint32)//4)[np.repeat(valid[:,:,None],3,axis=2)]

class Source:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.hash = sha(self.path)
        info = probe(path, '-show_streams','-show_format')
        v = next(s for s in info['streams'] if s['codec_type']=='video')
        if v.get('color_transfer') in ('smpte2084','arib-std-b67') or any('Mastering' in s.get('side_data_type','') for s in v.get('side_data_list',[])):
            raise ValueError('HDR is not supported; supply an SDR source')
        frames = probe(path,'-select_streams','v:0','-show_frames','-show_entries',
                       'frame=best_effort_timestamp_time,duration_time,pkt_duration_time')['frames']
        self.origin = float(info['format'].get('start_time',v.get('start_time',0)))
        self.pts = np.array([float(f['best_effort_timestamp_time'])-self.origin for f in frames])
        if not len(self.pts) or np.any(np.diff(self.pts)<=0):
            raise ValueError('video requires strictly increasing presentation timestamps')
        rotation = next((float(x['rotation']) for x in v.get('side_data_list',[]) if 'rotation' in x),0)
        w,h = v['width'],v['height']
        sar = v.get('sample_aspect_ratio','1:1')
        if sar not in ('N/A','0:1'):
            a,b = map(int,sar.split(':')); w = w*a/b
        if int(rotation)%180: w,h=h,w
        scale = min(64/w,64/h)
        sw,sh = max(1,round(w*scale)),max(1,round(h*scale))
        x,y=(64-sw)//2,(64-sh)//2
        self.valid=np.zeros((64,64),bool); self.valid[y:y+sh,x:x+sw]=True
        raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:v:0',
            '-vf',f'scale={sw}:{sh}:flags=bilinear,format=rgb24,pad=64:64:{x}:{y}:black,setsar=1',
            '-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','-'])
        self.rgb=np.frombuffer(raw,np.uint8).reshape(-1,64,64,3)
        if len(self.rgb)!=len(self.pts): raise ValueError('decoded frame/PTS count mismatch')
        last=float(frames[-1].get('duration_time',frames[-1].get('pkt_duration_time',0)))
        if last<=0: last=float(v.get('duration',0))-(self.pts[-1]-self.pts[0])
        if last<=0: raise ValueError('unknown final frame duration')
        self.ends=np.r_[self.pts[1:], self.pts[-1]+last]
        self.audio_config=None; self.samples=None; self.audio_events=[]; self.audio_error=None
        a=next((s for s in info['streams'] if s['codec_type']=='audio'),None)
        try:
            if a:
                self.audio_config=Config(int(a['sample_rate']),int(a['channels']))
                c=self.audio_config
                af=probe(path,'-select_streams','a:0','-show_frames','-show_entries','frame=best_effort_timestamp_time,nb_samples')['frames']
                raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-f','f32le','-acodec','pcm_f32le','-'])
                samples=np.frombuffer(raw,'<f4').reshape(-1,c.channels)
                # Respect container end trim (AAC decoders may return a padded final block).
                length=len(samples)
                if a.get('duration'):
                    length=min(length,round(float(a['duration'])*c.rate))
                self.samples=samples[:length]
                if not np.isfinite(self.samples).all() or np.any(abs(self.samples)>1):
                    raise ValueError('audio exceeds fixed PCM range')
                self.audio_start=float(af[0]['best_effort_timestamp_time'])-self.origin
                consumed=0
                for f in af:
                    expected=self.audio_start+consumed/c.rate
                    actual=float(f['best_effort_timestamp_time'])-self.origin
                    if abs(actual-expected)>2/c.rate: raise ValueError('discontinuous audio PTS unsupported')
                    consumed+=int(f['nb_samples'])
                for start,end,_ in c.frames(self.samples):
                    self.audio_events.append((self.audio_start+start/c.rate,self.audio_start+end/c.rate,start,end))
        except (ValueError, KeyError, IndexError, subprocess.CalledProcessError) as exc:
            self.audio_error=str(exc); self.audio_config=None; self.samples=None; self.audio_events=[]
        self.duration=max(float(self.ends[-1]),self.audio_events[-1][1] if self.audio_events else 0)
        self.metadata=dict(name=self.path.name,sha256=self.hash,video_frames=len(self.pts),
            audio_samples=len(self.samples) if self.samples is not None else 0,audio_config=vars(self.audio_config) if self.audio_config else None,audio_error=self.audio_error,
            duration=self.duration,origin=self.origin,rotation=rotation,valid_rect=[x,y,sw,sh],
            video_config=VIDEO_CONFIG,tm_config=TM_CONFIG,other_parameters='official defaults',
            pretrained=False)

def build_visual_template(path):
    """Build in a child process: official SP initialization holds the Python GIL."""
    from htm.bindings.algorithms import SpatialPooler, TemporalMemory
    sp=SpatialPooler(**VIDEO_CONFIG); tm=TemporalMemory(**TM_CONFIG)
    counts=np.zeros(2048,dtype=np.uint32); sp.getConnectedCounts(counts)
    if not np.all(counts>0):
        raise RuntimeError('Visual SP has disconnected columns; invalid receptive field/potential density')
    Path(path).write_bytes(pickle.dumps((sp,tm)))

class Models:
    def __init__(self): self.templates={}
    def new(self, config=None):
        from htm.bindings.algorithms import SpatialPooler, TemporalMemory
        from htm.bindings.sdr import SDR
        key=repr(config)
        if key not in self.templates:
            if config is None:
                with tempfile.TemporaryDirectory(prefix='htm-initial-') as directory:
                    path=Path(directory)/'unlearned.pkl'
                    subprocess.run([sys.executable,'-c',
                        'from mechanical_video.htm_av_core import build_visual_template; import sys; build_visual_template(sys.argv[1])',str(path)],check=True)
                    self.templates[key]=path.read_bytes()
            else:
                e=Engine(config); sp,tm=e.sp,e.tm
                self.templates[key]=pickle.dumps((sp,tm))
        sp,tm=pickle.loads(self.templates[key])
        return dict(sp=sp,tm=tm,input=SDR(config.size if config else 786432),
                    columns=SDR(512 if config else 2048),cells=8 if config else 32)

def compute(m, sparse, learning):
    m['input'].sparse=sparse
    m['sp'].compute(m['input'],learning,m['columns'])
    columns=m['columns'].sparse.copy()
    tm=m['tm']; tm.activateDendrites(learning)
    pc=tm.getPredictiveCells().sparse.copy(); predicted=np.unique(pc//m['cells'])
    tm.compute(m['columns'],learn=learning)
    active=tm.getActiveCells().sparse.copy()
    actual=np.unique(active//m['cells'])
    hits=np.intersect1d(columns,predicted)
    anomaly=1-len(hits)/len(columns) if len(columns) else 0.
    if not np.array_equal(columns,actual) or not np.isclose(anomaly,tm.anomaly,atol=1e-6):
        raise RuntimeError('official SP/TM invariants failed')
    return dict(input_sdr=sparse.tolist(),sp_output=columns.tolist(),tm_input=actual.tolist(),
        predicted_cells_for_current=pc.tolist(),predicted_columns_for_current=predicted.tolist(),
        active_cells=active.tolist(),winner_cells=tm.getWinnerCells().sparse.tolist(),
        anomaly=float(tm.anomaly),recomputed_anomaly=anomaly,prediction_hit_rate=1-anomaly)

class Store:
    def __init__(self,path):
        self.path=path; self.db=sqlite3.connect(path,check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS frames (pass INTEGER, lane TEXT, mode TEXT, idx INTEGER, start REAL, end REAL, anomaly REAL, hit REAL, detail BLOB, PRIMARY KEY(pass,lane,mode,idx))')
        self.db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)')
    def meta(self,key,value):
        self.db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',(key,json.dumps(value))); self.db.commit()
    def get_meta(self,key):
        row=self.db.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else None
    def put(self,p,l,m,f):
        self.db.execute('INSERT INTO frames VALUES (?,?,?,?,?,?,?,?,?)',(p,l,m,f['index'],f['start'],f['end'],f['anomaly'],f['prediction_hit_rate'],gzip.compress(json.dumps(f,separators=(',',':')).encode(),compresslevel=1)))
        self.db.commit()
    def detail(self,p,l,m,i):
        row=self.db.execute('SELECT detail FROM frames WHERE pass=? AND lane=? AND mode=? AND idx=?',(p,l,m,i)).fetchone()
        return json.loads(gzip.decompress(row[0])) if row else None
    def timeline(self,p,l,m):
        return [dict(index=i,start=s,end=e,anomaly=a,prediction_hit_rate=h) for i,s,e,a,h in self.db.execute('SELECT idx,start,end,anomaly,hit FROM frames WHERE pass=? AND lane=? AND mode=? ORDER BY idx',(p,l,m))]

class Lane:
    def __init__(self, source, models):
        self.source=source; self.models=models
        self.engines={'video':models.new(),'audio':models.new(source.audio_config) if source.audio_config else None}
        self.cursor={'video':0,'audio':0}; self.error={'audio':source.audio_error} if source.audio_error else {}
    def next_time(self,mode):
        i=self.cursor[mode]; s=self.source
        if mode in self.error: return float('inf')
        return (float(s.pts[i]) if i<len(s.pts) else float('inf')) if mode=='video' else (s.audio_events[i][1] if i<len(s.audio_events) else float('inf'))
    def step(self,mode,learning):
        s=self.source; i=self.cursor[mode]
        if mode=='video':
            sparse=encode_rgb(s.rgb[i],s.valid); start,end=float(s.pts[i]),float(s.ends[i])
            extras=dict(rgb=s.rgb[i].tolist(),valid=s.valid.tolist(),pts=start+s.origin)
        else:
            start,end,a,b=s.audio_events[i]; sparse=s.audio_config.encode(s.samples[a:b])
            extras=dict(start_sample=a,end_sample=b,waveform=s.samples[a:b].T.tolist(),pts=start+s.origin)
        result=compute(self.engines[mode],sparse,learning)
        result.update(index=i,start=start,end=end,learning=learning,sequence_start=i==0,**extras)
        self.cursor[mode]+=1
        return result
    def restart(self,zero=False):
        for mode,e in self.engines.items():
            if e:
                if zero: self.engines[mode]=self.models.new(None if mode=='video' else self.source.audio_config)
                else: e['tm'].reset()
        self.cursor={'video':0,'audio':0}; self.error={'audio':self.source.audio_error} if self.source.audio_error else {}

def compare(rows_a,rows_b,start,end,offset=0):
    """Piecewise-constant metrics; compare only jointly covered intervals."""
    sums={'a':0.,'b':0.,'hit_a':0.,'hit_b':0.}; covered=0.; i=j=0; segments=[]
    while i<len(rows_a) and j<len(rows_b):
        a,b=rows_a[i],rows_b[j]
        lo=max(start,a['start'],b['start']+offset); hi=min(end,a['end'],b['end']+offset)
        if hi>lo:
            d=hi-lo; covered+=d
            for key,val in [('a',a['anomaly']),('b',b['anomaly']),('hit_a',a['prediction_hit_rate']),('hit_b',b['prediction_hit_rate'])]: sums[key]+=d*val
            segments.append(dict(start=lo,end=hi,anomaly_delta=b['anomaly']-a['anomaly'],hit_delta=b['prediction_hit_rate']-a['prediction_hit_rate']))
        if a['end']<=b['end']+offset: i+=1
        else: j+=1
    means={k:v/covered if covered else None for k,v in sums.items()}
    return dict(covered_duration=covered,means=means,delta=means['b']-means['a'] if covered else None,segments=segments)
