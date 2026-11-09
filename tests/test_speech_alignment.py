import unittest
import numpy as np
from mechanical_video.speech_alignment import ctc_path, normalize


class SpeechAlignmentTests(unittest.TestCase):
    def emissions(self, sequence):
        p=np.full((len(sequence), 3), .001)
        for i,s in enumerate(sequence): p[i,s]=.998
        return np.log(p)

    def test_repeated_characters_require_blank(self):
        spans=ctc_path(self.emissions([0,1,1,0,1,2,0]),[1,1,2],0)
        self.assertEqual([(a,b) for a,b,_ in spans],[(1,3),(4,5),(5,6)])

    def test_added_silence_shifts_measured_events(self):
        a=ctc_path(self.emissions([1,1,0,2,0]),[1,2],0)
        b=ctc_path(self.emissions([0,0,0,1,1,0,2,0]),[1,2],0)
        self.assertEqual([(s+3,e+3) for s,e,_ in a],[(s,e) for s,e,_ in b])

    def test_impossible_or_invalid_alignment_rejected(self):
        for emissions,tokens in [(self.emissions([1]),[1,1]),(np.array([[np.nan,0,0]]),[1]),(self.emissions([1]),[0])]:
            with self.assertRaises(ValueError): ctc_path(emissions,tokens,0)

    def test_normalization_preserves_spoken_symbols(self):
        self.assertEqual(normalize('退回，压脚！3D。'), '退回压脚3d')

class MeasurementTests(unittest.TestCase):
    def setUp(self):
        import tempfile, json
        from pathlib import Path
        from mechanical_video.scene_fidelity import file_ref
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.audio=Path(self.tmp.name)/'a.wav';self.audio.write_bytes(b'fixed audio')
        self.path=Path(self.tmp.name)/'alignment.json'
        self.report=dict(method='forced_alignment',audio=file_ref(self.audio),duration=3,
            transcript='退回压脚',normalized_transcript='退回压脚',greedy_transcript='退回压脚',
            characters=[dict(text=c,start=i*.5,end=(i+1)*.5,confidence=.9) for i,c in enumerate('退回压脚')])
        self.events=[dict(id='release',phrase='退回',caption='退回',requirement='release',animation={'channel':'lock'},foley=[])]

    def measure(self):
        import json
        from mechanical_video.speech_alignment import measurement_from_alignment
        self.path.write_text(json.dumps(self.report))
        return measurement_from_alignment(self.events,self.path)

    def test_measured_intervals_feed_event_clock(self):
        from mechanical_video.event_timeline import build, verify
        measurement=self.measure()
        result=build(self.events,measurement,self.audio,self.path)
        self.assertTrue(verify(result))
        self.assertEqual(result['captions'][0]['end'],1)
        self.audio.write_bytes(b'changed')
        self.assertFalse(verify(result))

    def test_false_transcript_stale_audio_and_low_support_rejected(self):
        import copy
        original=copy.deepcopy(self.report)
        for mutate in ('recognition','confidence','stale'):
            self.report=copy.deepcopy(original)
            if mutate=='recognition':self.report['greedy_transcript']='完全不同'
            if mutate=='confidence':
                for c in self.report['characters']:c['confidence']=.001
            if mutate=='stale':self.report['audio']['sha256']='0'*64
            with self.assertRaises(ValueError):self.measure()

    def test_out_of_order_or_missing_phrase_rejected(self):
        self.events=[dict(id='a',phrase='压脚'),dict(id='b',phrase='退回')]
        with self.assertRaises(ValueError):self.measure()

    def test_malformed_character_intervals_rejected_before_export(self):
        import copy
        original=copy.deepcopy(self.report)
        for changes in ({'end':500},{'start':float('nan')},{'start':-1},{'end':0},{'confidence':float('nan')}):
            self.report=copy.deepcopy(original)
            self.report['characters'][0].update(changes)
            with self.assertRaises(ValueError):self.measure()
        self.report=original
        self.report['characters'][1]['start']=.1
        with self.assertRaises(ValueError):self.measure()

    def test_high_global_agreement_does_not_accept_unheard_event(self):
        self.report['greedy_transcript']='退回压'
        self.events=[dict(id='foot',phrase='脚')]
        with self.assertRaises(ValueError):self.measure()
