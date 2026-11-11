import json
import tempfile
import time
import unittest
from unittest.mock import patch
import subprocess
from pathlib import Path
import numpy as np
from mechanical_video.htm_av_core import encode_rgb, Source, Models, Lane, compare, Store, compute
from mechanical_video.htm_av_live import Session

class EncodingTests(unittest.TestCase):
    def test_fixed_color_and_addresses(self):
        valid=np.ones((64,64),bool)
        for color,bins in [([0,0,0],[0,0,0]),([255,128,3],[63,32,0]),([0,255,0],[0,63,0])]:
            rgb=np.full((64,64,3),color,np.uint8); bits=encode_rgb(rgb,valid)
            self.assertEqual(len(bits),12288); self.assertEqual(len(np.unique(bits)),len(bits))
            np.testing.assert_array_equal(bits[:3],np.arange(3)*64+bins)
        rgb=np.zeros((64,64,3),np.uint8); before=encode_rgb(rgb,valid)
        rgb[3,5,2]=255; after=encode_rgb(rgb,valid)
        self.assertEqual(np.count_nonzero(before!=after),1)
        self.assertEqual(after[(3*64+5)*3+2],((3*64+5)*3+2)*64+63)
    def test_gradient_mask_and_color(self):
        valid=np.zeros((64,64),bool);valid[:,20:44]=True
        rgb=np.repeat(np.arange(64,dtype=np.uint8)[None,:,None]*4,64,axis=0);rgb=np.repeat(rgb,3,axis=2)
        bits=encode_rgb(rgb,valid);self.assertEqual(len(bits),64*24*3)
        np.testing.assert_array_equal(bits%64,np.tile(np.repeat(np.arange(20,44),3),64))
        red=np.zeros((64,64,3),np.uint8);green=red.copy();red[:,:,0]=150;green[:,:,1]=76
        self.assertFalse(np.array_equal(encode_rgb(red,valid),encode_rgb(green,valid)))
    def test_weighted_overlap(self):
        def r(s,e,a):return dict(start=s,end=e,anomaly=a,prediction_hit_rate=1-a)
        x=compare([r(0,1,0),r(1,3,1)],[r(0,3,.5)],.5,2)
        self.assertAlmostEqual(x['means']['a'],2/3);self.assertAlmostEqual(x['delta'],-1/6)
        self.assertIsNone(compare([r(0,1,0)],[r(2,3,1)],0,3)['delta'])
        self.assertEqual(compare([r(0,1,0)],[r(2,3,1)],0,3,-2)['delta'],1)

try:
    import htm.bindings.algorithms
    NATIVE = True
except ImportError:
    NATIVE = False

@unittest.skipUnless(NATIVE, 'official native HTM environment required')
class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(); cls.root=Path(cls.tmp.name)
        cls.base=cls.root/'base.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=96x64:rate=30:duration=0.3','-f','lavfi','-i','sine=sample_rate=48000:duration=0.3','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(cls.base)],check=True)
        cls.models=Models(); cls.source=Source(cls.base)
        cls.factory_patch=patch('mechanical_video.htm_av_live.Models',return_value=cls.models)
        cls.factory_patch.start()
    @classmethod
    def tearDownClass(cls):
        cls.factory_patch.stop(); cls.tmp.cleanup()
    def test_visual_connections_and_input_dependence(self):
        a,b=self.models.new(),self.models.new()
        counts=np.zeros(2048,dtype=np.uint32);a['sp'].getConnectedCounts(counts)
        self.assertTrue(np.all(counts>0), 'every visual column must receive real input')
        valid=np.ones((64,64),bool)
        black=compute(a,encode_rgb(np.zeros((64,64,3),np.uint8),valid),False)
        white=compute(b,encode_rgb(np.full((64,64,3),255,np.uint8),valid),False)
        self.assertNotEqual(black['sp_output'],white['sp_output'], 'SP must respond to controlled color changes')

    def test_decode_and_identical_models(self):
        s=self.source;self.assertEqual(len(s.pts),9);self.assertEqual(len(s.samples),14400)
        self.assertEqual(int(s.valid.sum()),64*43)
        a,b=Lane(s,self.models),Lane(s,self.models)
        for mode in ('video','audio'):
            while np.isfinite(a.next_time(mode)):
                fa,fb=a.step(mode,True),b.step(mode,True)
                self.assertEqual(fa,fb)
                self.assertEqual(fa['sp_output'],fa['tm_input'])
                self.assertAlmostEqual(fa['anomaly'],fa['recomputed_anomaly'],places=6)
        self.assertEqual(a.cursor,dict(video=9,audio=30))
    def test_rotation_vfr_offset_and_silent(self):
        rotated=self.root/'rotated.mp4'
        subprocess.run(['ffmpeg','-v','error','-display_rotation:v:0','90','-i',str(self.base),'-c','copy',str(rotated)],check=True)
        r=Source(rotated);self.assertEqual(r.rgb.shape[0],9);self.assertEqual(r.metadata['valid_rect'][2:], [43,64])
        vfr=self.root/'vfr.mp4'
        subprocess.run(['ffmpeg','-v','error','-i',str(self.base),'-vf',"setpts='if(lt(N,4),N,2*N-4)/(30*TB)'",'-an','-fps_mode','vfr',str(vfr)],check=True)
        v=Source(vfr);self.assertIsNone(v.audio_config);self.assertEqual(len(v.pts),9);self.assertGreater(len(np.unique(np.round(np.diff(v.pts),5))),1)
        offset=self.root/'offset.mp4'
        subprocess.run(['ffmpeg','-v','error','-i',str(self.base),'-itsoffset','0.1','-i',str(self.base),'-map','0:v:0','-map','1:a:0','-c','copy',str(offset)],check=True)
        o=Source(offset);self.assertGreater(o.audio_start,.07);self.assertGreater(o.audio_events[0][1],o.audio_start)
    def test_hdr_rejected_and_audio_mismatch(self):
        hdr=self.root/'hdr.mp4'
        subprocess.run(['ffmpeg','-v','error','-i',str(self.base),'-c','copy','-bsf:v','h264_metadata=colour_primaries=9:transfer_characteristics=16:matrix_coefficients=9',str(hdr)],check=True)
        with self.assertRaisesRegex(ValueError,'HDR'): Source(hdr)
        other=self.root/'other.mp4'
        subprocess.run(['ffmpeg','-v','error','-i',str(self.base),'-c:v','copy','-ar','44100',str(other)],check=True)
        session=Session(self.base,other,self.root/'mismatch')
        deadline=time.monotonic()+180
        while session.status=='initializing' and time.monotonic()<deadline:time.sleep(.05)
        self.assertEqual(session.status,'ready',session.error)
        self.assertIn('disabled',session.timelines()['comparison']['audio'])
        session.control('settings',dict(offset=.1))
        session.control('step',dict(mode='audio'))
        self.assertEqual(session.lanes['B'].cursor,dict(video=0,audio=0))
        session.control('restart',{})
        session.control('settings',dict(offset=.2))
        self.assertEqual(session.timelines(pass_number=1)['offset'],.1)
        self.assertEqual(session.timelines(pass_number=2)['offset'],.2)

    def test_store_read_only_history(self):
        st=Store(self.root/'history.sqlite');l=Lane(self.source,self.models);f=l.step('video',True)
        before=l.engines['video']['sp'].getIterationLearnNum();st.put(1,'A','video',f)
        self.assertEqual(st.detail(1,'A','video',0),f);self.assertEqual(len(st.timeline(1,'A','video')),1)
        self.assertEqual(before,l.engines['video']['sp'].getIterationLearnNum())
        l.restart();self.assertEqual(before,l.engines['video']['sp'].getIterationLearnNum())
        l.restart(True);self.assertEqual(l.engines['video']['sp'].getIterationLearnNum(),0)
    def test_session_scheduler_pause_and_settings(self):
        session=Session(self.base,self.base,self.root/'session')
        deadline=time.monotonic()+180
        while session.status=='initializing' and time.monotonic()<deadline:time.sleep(.05)
        self.assertEqual(session.status,'ready',session.error)
        session.control('step',dict(mode='video'))
        self.assertEqual(session.lanes['A'].cursor['video'],1)
        self.assertEqual(session.lanes['A'].cursor['audio'],0)
        count=session.events
        session.state();session.timelines();self.assertEqual(session.events,count)
        session.control('play',{})
        with self.assertRaises(ValueError):session.control('settings',dict(learning=False))
        session.control('pause',{});session.control('settings',dict(learning=False))
        while session.step_event():pass
        self.assertEqual(session.lanes['A'].cursor,dict(video=9,audio=30))
        self.assertEqual(session.lanes['A'].cursor,session.lanes['B'].cursor)
        self.assertEqual(session.timelines()['comparison']['video']['delta'],0)
        session.control('restart',{});self.assertIsNotNone(session.store.detail(1,'A','video',0))

if __name__=='__main__':unittest.main()
