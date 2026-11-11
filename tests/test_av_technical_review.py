import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import numpy as np
from mechanical_video.av_technical_review import analyze_arrays, intervals, attach_htm, DEFAULT, render_html
from mechanical_video.av_review_benchmark import score_events, validate_manifest, wilson

class ReviewTests(unittest.TestCase):
    def setup_video(self):
        n=90;rgb=np.zeros((n,64,64,3),np.uint8)
        for i in range(n):rgb[i]=50+i%40
        starts=np.arange(n)/30;ends=starts+1/30
        return rgb,np.ones((64,64),bool),starts,ends
    def test_visual_physical_events_and_end_coverage(self):
        rgb,valid,starts,ends=self.setup_video();rgb[12:21]=0;rgb[33:57]=rgb[33];rgb[70:72]=255
        r=analyze_arrays(rgb,valid,starts,ends)
        kinds={f['kind'] for f in r['findings']};self.assertEqual(kinds,{'black','freeze','flash'})
        black=next(f for f in r['findings'] if f['kind']=='black');self.assertAlmostEqual(black['start'],.4);self.assertAlmostEqual(black['end'],.7)
        self.assertEqual(r['coverage']['video_frames'],90)
    def test_freeze_breaks_at_motion_and_preserves_first_frame(self):
        rgb,valid,starts,ends=self.setup_video()
        rgb[:30]=80;rgb[30:60]=100;rgb[60:]=120
        findings=[f for f in analyze_arrays(rgb,valid,starts,ends)['findings'] if f['kind']=='freeze']
        self.assertEqual([(f['start'],round(f['end'],6)) for f in findings],[(0.,1.),(1.,2.),(2.,3.)])
        self.assertTrue(all(f['evidence']['max_internal_mean_rgb_difference']==0 for f in findings))

    def test_padding_ignored_and_hard_cut_not_flash(self):
        rgb,valid,starts,ends=self.setup_video();valid[:,:30]=False;rgb[:,:,:30]=0;rgb[45:,:,30:]=180
        r=analyze_arrays(rgb,valid,starts,ends)
        self.assertFalse(any(f['kind'] in ('black','flash') for f in r['findings']))
    def test_native_stereo_silence_and_clipping(self):
        rgb,valid,starts,ends=self.setup_video();rate=11025;t=np.arange(rate*3)/rate
        x=np.stack([.2*np.sin(2*np.pi*223*t),.2*np.sin(2*np.pi*331*t)],axis=1)
        x[rate:round(rate*1.3),0]=0;x[round(rate*1.8):round(rate*2),1]=1
        r=analyze_arrays(rgb,valid,starts,ends,x,rate,audio_start=.25)
        silence=[f for f in r['findings'] if f['kind']=='dropout'];clip=[f for f in r['findings'] if f['kind']=='clipping']
        self.assertEqual(len(silence),1);self.assertEqual(silence[0]['channel'],0);self.assertAlmostEqual(silence[0]['start'],1.25,places=2)
        self.assertEqual(len(clip),1);self.assertEqual(clip[0]['channel'],1)
        self.assertEqual(sum(r['end_sample']-r['start_sample'] for r in r['audio_metrics']),len(x))
        self.assertEqual(r['audio_metrics'][-1]['end_sample'],len(x))
    def test_full_volume_sine_is_not_flat_rail_clipping(self):
        rgb,valid,starts,ends=self.setup_video();rate=48000;t=np.arange(rate*3)/rate
        for frequency in (50,440,577):
            samples=(.999*np.sin(2*np.pi*frequency*t))[:,None]
            r=analyze_arrays(rgb,valid,starts,ends,samples,rate)
            self.assertFalse(any(f['kind']=='clipping' for f in r['findings']),frequency)

    def test_intended_still_and_pause_are_not_auto_defects(self):
        rgb,valid,starts,ends=self.setup_video();rgb[:]=100
        r=analyze_arrays(rgb,valid,starts,ends,np.zeros((144000,1)),48000)
        self.assertTrue(r['findings'])
        self.assertTrue(all(f['status']=='OBSERVED_REQUIRES_CONTEXT' and not f['automatic_repair'] and f['severity'] is None for f in r['findings']))
    def test_event_matching_one_to_one(self):
        r=lambda a,b:dict(start=a,end=b)
        score=score_events([r(1,2),r(1,2),r(5,6)],[r(1,2)])
        self.assertEqual((score['tp'],score['fp'],score['fn']),(1,2,0))
        self.assertLess(wilson(4,4)[0],.6)
    def test_source_disjoint_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a';p.write_bytes(b'1')
            from mechanical_video.av_technical_review import digest
            cases=[dict(id='a',family='shared',split='development',path='a',sha256=digest(p),labels=[],duration=1),dict(id='b',family='shared',split='test',path='a',sha256=digest(p),labels=[],duration=1)]
            with self.assertRaisesRegex(ValueError,'leakage'):validate_manifest(dict(cases=cases),d)
    def test_htm_identity_and_invalid_visual_model(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'history.sqlite';db=sqlite3.connect(path)
            db.execute('CREATE TABLE metadata(key TEXT,value TEXT)')
            db.execute('INSERT INTO metadata VALUES (?,?)',('pass:1',json.dumps(dict(sources={'A':dict(sha256='good',video_config={'potentialRadius':16})}))))
            db.commit();db.close()
            with self.assertRaisesRegex(ValueError,'hash mismatch'):attach_htm(path,'wrong')
            with self.assertRaisesRegex(ValueError,'visual configuration'):attach_htm(path,'good')
    def test_interval_tail(self):
        self.assertEqual(intervals([False,True,True],[0,.1,.2],[.1,.2,.3],.1),[[.1,.3]])

if __name__=='__main__':unittest.main()
