import copy
import json
import tempfile
import unittest
from pathlib import Path
from mechanical_video.event_timeline import build, verify, gate_errors
from mechanical_video.scene_fidelity import file_ref


class EventTimelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.audio = Path(self.tmp.name)/'speech.wav'; self.audio.write_bytes(b'fixture-audio')
        self.evidence = Path(self.tmp.name)/'alignment.json'; self.evidence.write_text('fixture evidence')
        self.events = [dict(id='release', requirement='rewind', phrase='解除锁止', caption='解除锁止', animation={'channel':'lock'}, foley=[])]
        self.measurement = dict(audio=file_ref(self.audio), evidence=file_ref(self.evidence), duration=2,
                                method='forced_alignment', spans=[dict(event_id='release', text='解除锁止', start=.25, end=1.75)])

    def build(self):
        return build(self.events, self.measurement, self.audio, self.evidence)

    def test_all_consumers_share_measured_event(self):
        result=self.build(); self.assertTrue(verify(result))
        self.assertEqual(result['events'][0]['start'], .25)
        self.assertEqual(result['captions'][0]['end'], 1.75)
        result['events'][0]['end']=1.9
        self.assertFalse(verify(result))

    def test_no_estimates_stale_audio_or_missing_actions(self):
        original=copy.deepcopy(self.measurement)
        for mutation in [dict(method='paragraph_ratio'), dict(spans=[]), dict(duration=float('nan'))]:
            self.measurement={**original, **mutation}
            with self.assertRaises(ValueError): self.build()
        self.measurement=original
        result=self.build(); self.audio.write_bytes(b'new speech')
        self.assertFalse(verify(result))

    def test_phrase_caption_and_duplicate_span_rejected(self):
        self.events[0]['phrase']='相反动作'
        with self.assertRaises(ValueError): self.build()
        self.events[0]['phrase']='解除锁止'; self.events[0]['caption']='字'*21
        with self.assertRaises(ValueError): self.build()
        self.events[0]['caption']='解除锁止'; self.measurement['spans']*=2
        with self.assertRaises(ValueError): self.build()

    def test_gate_rejects_different_caption_or_motion_clock(self):
        base=Path(self.tmp.name); timeline=self.build()
        assets={'narration_audio':file_ref(self.audio)}
        def save(name,data):
            path=base/(name+'.json');path.write_text(json.dumps(data))
            assets[name]=file_ref(path)
        save('event_timeline',timeline)
        save('content_contract',{'requirements':[{'id':'rewind'}]})
        save('timeline',{'duration':timeline['duration'],'captions':timeline['captions']})
        for name,field in [('motion','animation'),('foley_timeline','foley')]:
            save(name,{'event_bindings':[dict(event_id=e['id'],start=e['start'],end=e['end'],binding=e[field]) for e in timeline['events']]})
        self.assertEqual(gate_errors({'assets':assets},base),[])
        shifted=copy.deepcopy(timeline['captions']);shifted[0]['start']=0
        save('timeline',{'duration':2,'captions':shifted})
        self.assertTrue(gate_errors({'assets':assets},base))
        save('timeline',{'duration':2,'captions':timeline['captions']})
        save('motion',{'event_bindings':[]})
        self.assertTrue(gate_errors({'assets':assets},base))
