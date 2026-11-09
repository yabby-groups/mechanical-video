import copy,json,tempfile,unittest
from pathlib import Path
from mechanical_video import action_alignment as checker
from mechanical_video.scene_fidelity import file_ref

class ActionAlignmentTests(unittest.TestCase):
 def setUp(self):
  self.motion={'fps':2,'frames':6,'poses':[{'time':i/2,'extension':5-i,'lock':0} for i in range(6)]}
  self.timeline={'duration':3,'captions':[{'text':'收回尺带','start':0,'end':3}]}
  self.policy={'schema_version':1,'requirements':[{'id':'release','assertions':[{'caption_text':'收回尺带','channel':'extension','relation':'decreasing','min_change':1}]}]}
 def result(self):return checker.evaluate(self.motion,self.timeline,self.policy)
 def test_correct_action(self):self.assertEqual(self.result()['status'],'PASS')
 def test_wrong_direction_blocks(self):
  for p in self.motion['poses']:p['extension']=p['time']
  self.assertEqual(self.result()['status'],'BLOCKED')
 def test_no_motion_blocks(self):
  for p in self.motion['poses']:p['extension']=3
  self.assertEqual(self.result()['status'],'BLOCKED')
 def test_held_lock_state_requires_actual_contact(self):
  self.policy['requirements'][0]['assertions']=[dict(caption_text='收回尺带',channel='lock',relation='held_above',bound=.99,min_fraction=.8)]
  self.assertEqual(self.result()['status'],'BLOCKED')
 def test_missing_nonfinite_frame_or_channel_blocks(self):
  for value in [None,float('nan'),True]:
   m=copy.deepcopy(self.motion);m['poses'][2]['extension']=value
   with self.subTest(value=value),self.assertRaises(ValueError):checker.evaluate(m,self.timeline,self.policy)
  self.motion['poses'].pop()
  with self.assertRaises(ValueError):self.result()
 def test_ambiguous_caption_is_not_silently_chosen(self):
  self.timeline['captions']*=2
  with self.assertRaises(ValueError):self.result()
 def test_verify_recomputes_and_binds_inputs(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for name,value in [('motion',self.motion),('timeline',self.timeline),('policy',self.policy)]:
    (root/name).write_text(json.dumps(value))
   report=checker.inspect(root/'motion',root/'timeline',root/'policy')
   assets={name:file_ref(root/filename) for name,filename in [('motion','motion'),('timeline','timeline'),('action_alignment_policy','policy')]}
   self.assertTrue(checker.verify(report,assets,['release']))
   self.assertFalse(checker.verify(report,assets,['release','lock']))
   report['checks'][0]['last']=100
   self.assertFalse(checker.verify(report,assets,['release']))
