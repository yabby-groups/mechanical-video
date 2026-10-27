import unittest
from mechanical_video.drill_remake import SECTIONS
from mechanical_video.film_audio import caption_lines

class DrillRemakeTests(unittest.TestCase):
    def test_power_chain_shots_and_short_speech_units(self):
        self.assertEqual([i for _,i,_ in SECTIONS],[0,1,7,2,6,5,4,3,8])
        for _,_,lines in SECTIONS:
            for line in lines:
                self.assertEqual(caption_lines(line),[line])
