import unittest
from pathlib import Path
from mechanical_video.drill_film import storyboard

class DrillFilmTests(unittest.TestCase):
    def test_actual_speech_offsets_and_final_explosion(self):
        parts=[dict(name='housing_left',group='shell',explode=[5,-90,18]),
               dict(name='inferred_cell_1',group='battery',explode=[-40,0,-75]),
               dict(name='keyless_chuck_sleeve',group='shell',explode=[-130,0,15]),
               dict(name='stage_1_sun',group='gear',explode=[-47,-30,0]),
               dict(name='motor_rotor',group='motor',explode=[80,65,0]),
               dict(name='trigger',group='control',explode=[-40,-42,-20])]
        lengths=[5,6,7,8,9,10,11,12,13]
        story=storyboard(parts,[(Path('unused'),n) for n in lengths],seconds=94)
        pause=(94-sum(lengths))/9
        cursor=0
        for c,length in zip(story['chapters'],lengths):
            self.assertAlmostEqual(c['start'],cursor)
            self.assertAlmostEqual(c['speech_end']-c['start'],length)
            cursor+=length+pause
        self.assertEqual(story['chapters'][-1]['end'],94)
        self.assertEqual(set(story['chapters'][-1]['visible_parts']),{p['name'] for p in parts})
        self.assertEqual(story['chapters'][3]['visible_parts'],['keyless_chuck_sleeve'])
        for part in parts:
            track=story['tracks_mm'][part['name']]
            self.assertEqual(track[0],[0,[0,0,0]])
            self.assertEqual(track[-1],[94,part['explode']])
            self.assertEqual([t for t,_ in track],sorted(t for t,_ in track))
        # Battery leaves as one pack before the cells separate in their own chapter.
        track=story['tracks_mm']['inferred_cell_1']
        self.assertEqual(track[2][1],[0,0,-45])
        self.assertEqual(track[3][1],[0,0,-45])
    def test_overlong_narration_fails_before_render(self):
        with self.assertRaisesRegex(ValueError,'exceeds target'):
            storyboard([],[(Path('unused'),11)]*9,seconds=94)
