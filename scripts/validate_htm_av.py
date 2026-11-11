"""Real source coverage and controlled changes; no perceptual quality verdict."""
import json
import argparse
import time
from pathlib import Path
import numpy as np
from mechanical_video.htm_av_core import Lane, compute, encode_rgb
from mechanical_video.htm_av_live import Session, DEFAULT_VIDEO, report_html
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',required=True)
args=parser.parse_args()
root=Path(args.output)
s=Session(DEFAULT_VIDEO,DEFAULT_VIDEO,root)
while s.status=='initializing': time.sleep(.2)
if s.status!='ready':raise RuntimeError(s.error)
start=time.monotonic()
with s.lock:
    while s.step_event(): pass
elapsed=time.monotonic()-start
state=s.state(); timeline=s.timelines()
checks={}
for key,lane in s.lanes.items():
    v=s.store.timeline(1,key,'video');a=s.store.timeline(1,key,'audio')
    assert len(v)==1382 and len(a)==4607
    assert lane.cursor==dict(video=1382,audio=4607) and not lane.error
    consumed=0
    for mode,rows in [('video',v),('audio',a)]:
        for row in rows:
            f=s.store.detail(1,key,mode,row['index'])
            assert f['sp_output']==f['tm_input']
            assert abs(f['anomaly']-f['recomputed_anomaly'])<1e-6
            if mode=='audio':consumed+=f['end_sample']-f['start_sample']
            if key=='B':assert f==s.store.detail(1,'A',mode,row['index'])
    assert consumed==2211200
    checks[key]=dict(video_frames=len(v),audio_frames=len(a),samples=consumed,errors=lane.error,
        first_pts=v[0]['start'],last_pts=v[-1]['start'],end=v[-1]['end'])
# Controlled input edits: local color, copied preceding frame, replaced transition.
# Each pair begins from independent copies of the exact same unlearned weights.
variants={}
src=s.sources['A']
for kind in ('copied_frame','local_color','replacement_transition'):
    a=Lane(src,s.models);b=Lane(src,s.models);rows=[]
    for i in range(30):
        rgb=src.rgb[i].copy()
        if i==10:
            if kind=='copied_frame':rgb=src.rgb[i-1].copy()
            elif kind=='local_color':rgb[20:40,20:40,0]=255-rgb[20:40,20:40,0]
            else:rgb[src.valid]=[255,0,0]
        fa=a.step('video',True);fb=compute(b.engines['video'],encode_rgb(rgb,src.valid),True)
        input_equal=fa['input_sdr']==fb['input_sdr']
        assert input_equal==(i!=10)
        rows.append(dict(index=i,pts=float(src.pts[i]),input_equal=input_equal,anomaly_a=fa['anomaly'],anomaly_b=fb['anomaly'],sp_equal=fa['sp_output']==fb['sp_output']))
    variants[kind]=rows
(root/'controlled-variants.json').write_text(json.dumps(variants,indent=2))
report=dict(status='TECHNICAL_CHECKS_PASSED',source=str(DEFAULT_VIDEO),source_sha256=src.hash,
    initialization_seconds=s.initialization_seconds,paired_processing_wall_seconds=elapsed,
    paired_media_seconds=src.duration,paired_realtime_factor=src.duration/elapsed,
    total_video_frames=2764,video_frames_per_second=2764/elapsed,
    exact_independent_AB_equal=True,coverage=checks,
    limitation='Same-source test copy, not a reference hit. Novelty is not quality. Browser verification recorded separately.')
(root/'acceptance.json').write_text(json.dumps(report,indent=2))
(root/'timeline.json').write_text(json.dumps(dict(state=state,timeline=timeline)))
(root/'comparison.html').write_bytes(report_html(state,timeline))
print(json.dumps(report,indent=2),flush=True)
