import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mechanical_video import series
from mechanical_video.series_content import TITLES, lines


class SeriesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)/'series'
        self.patcher=patch.object(series,'BASE',self.base); self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_plan_preserves_completed_episode_and_series_history(self):
        series.plan()
        state=series.read(self.base/'series.json'); state['completed_episodes']=[1]
        state['next_episode']=2; series.write(self.base/'series.json',state)
        path=self.base/'episodes/EP01/episode.json'
        episode=series.read(path); episode['state']='complete'; series.write(path,episode)
        series.plan()
        self.assertEqual(series.read(path)['state'],'complete')
        self.assertEqual(series.read(self.base/'series.json')['next_episode'],2)
        self.assertEqual(len(list((self.base/'episodes').glob('*/episode.json'))),12)

    def test_existing_output_cannot_be_overwritten_without_acceptance(self):
        series.plan(); output=self.base/'output/EP01.mp4'; output.write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError,'preserved'): series.render(1)
        self.assertEqual(output.read_bytes(),b'keep')

    def test_completed_render_is_idempotent_without_provider_or_blender(self):
        series.plan(); output=self.base/'output/EP01.mp4'; output.write_bytes(b'keep')
        series.write(self.base/'episodes/EP01/validation.json',{'passed':True,'video_sha256':series.digest(output)})
        with patch.object(series,'audio',side_effect=AssertionError('must not resubmit')):
            series.render(1)
        self.assertEqual(output.read_bytes(),b'keep')

    def test_subtitles_are_short_and_machine_specific(self):
        self.assertEqual(len(TITLES),12)
        for number in [1,2,3]:
            self.assertGreater(len(lines(number)),40)
            self.assertTrue(all(0<len(line)<=20 and '\n' not in line for line in lines(number)))
        self.assertIn('这里不是丝杆抬升热床的结构。',lines(1))

    def test_unknown_episode_never_fabricates_script(self):
        with self.assertRaisesRegex(ValueError,'no placeholder'): lines(13)

    def test_full_season_has_authored_scripts_and_ordered_scene_sections(self):
        for number in range(1,13):
            text=lines(number)
            self.assertGreater(sum(map(len,text)),500)
            timeline={'chapters':[{'start':i*3} for i in range(len(text))],'seconds':len(text)*3}
            sections=series.scene_topics(number,timeline)
            self.assertEqual(sections[0]['start'],0)
            self.assertEqual(sections[-1]['end'],timeline['seconds'])
            self.assertTrue(all(a['end']==b['start'] for a,b in zip(sections,sections[1:])))

    def test_changed_narration_refuses_reuse(self):
        series.plan(); (self.base/'episodes/EP01/script.md').write_text('changed')
        with self.assertRaisesRegex(ValueError,'Editorial source changed'): series.audio(1)

    def test_cad_failure_is_persisted_without_video_or_completion(self):
        series.plan()
        with patch.object(series,'audio',return_value={'seconds':90}),patch.object(series,'model',side_effect=ValueError('Invalid source CAD')):
            with self.assertRaisesRegex(ValueError,'Invalid source CAD'): series.render(1)
        episode=series.read(self.base/'episodes/EP01/episode.json')
        self.assertEqual((episode['state'],episode['failed_stage']),('failed','model'))
        self.assertFalse(series.read(self.base/'episodes/EP01/validation.json')['passed'])
        self.assertFalse((self.base/'output/EP01.mp4').exists())
        self.assertEqual(series.read(self.base/'series.json')['completed_episodes'],[])

    def test_faceted_fallback_must_form_an_independent_valid_solid(self):
        from build123d import Box
        from mechanical_video.series_geometry import faceted_solid
        result,evidence=faceted_solid(Box(2,3,4))
        self.assertTrue(result.is_valid)
        self.assertAlmostEqual(result.volume,24,places=5)
        self.assertLess(evidence['relative_volume_convergence'],.01)

    def test_periodic_meshing_rebuild_keeps_exact_cone_geometry(self):
        from build123d import Cone,Face,GeomType
        from mechanical_video.series_geometry import repair_periodic_meshing
        source=Cone(3,2,5); original=Face.tessellate; raised=[]
        def missing_one_face(face,*args):
            if face.geom_type==GeomType.CONE and not raised:
                raised.append(True)
                raise AttributeError('Missing source triangulation')
            return original(face,*args)
        with patch.object(Face,'tessellate',missing_one_face):
            result,evidence=repair_periodic_meshing(source)
        self.assertTrue(result.is_valid)
        self.assertAlmostEqual(result.volume,source.volume,places=6)
        self.assertEqual(len(evidence),1)
        self.assertAlmostEqual(evidence[0]['original_area_mm2'],evidence[0]['rebuilt_area_mm2'],places=6)

    def test_shared_geometry_tampering_blocks_reuse(self):
        folder=self.base/'master_assembly'; folder.mkdir(parents=True)
        for name in ['part.step','part.stl']: (folder/name).write_bytes(b'original')
        manifest=folder/'assembly.json'
        series.write(manifest,{'parts':[{'step':'part.step','mesh':'part.stl'}]})
        expected=series.geometry_inventory(manifest)
        self.assertEqual(series.geometry_inventory(manifest),expected)
        (folder/'part.stl').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'geometry assets changed'): series.geometry_inventory(manifest)


    def test_native_cad_readback_evidence_rejects_modified_sidecar(self):
        folder=self.base/'master_assembly'; folder.mkdir(parents=True)
        display=folder/'assembly.json'; display.write_text('{}')
        canonical=folder/'cad_assembly.json'; canonical.write_text('{}')
        part=folder/'part.brep'; part.write_bytes(b'validated geometry')
        series.write(folder/'cad-roundtrip-validation.json',dict(passed=True,
            display_manifest_sha256=series.digest(display),cad_manifest_sha256=series.digest(canonical),
            unique_step_files=1,total_occurrences=1,
            results=[{'step':'part.brep','sha256':series.digest(part)}]))
        self.assertTrue(series.native_cad_acceptance(display)['passed'])
        part.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'part changed'):
            series.native_cad_acceptance(display)


if __name__=='__main__': unittest.main()
