import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from mechanical_video import av_auto_review as auto, production_run


class AutoReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'production'; self.root.mkdir()
        self.monitor = auto.Monitor([self.root], self.base/'reports', settle=0)

    def fake_report(self, source, output, **kwargs):
        output.mkdir()
        report = dict(status='OBSERVATIONS_FOUND', findings=[{}], coverage={'video_frames':30})
        (output/'report.json').write_text(json.dumps(report))
        (output/'index.html').write_text('report')
        (output/'media.mp4').write_bytes(source.read_bytes())
        return report

    def test_baseline_stability_revision_dedup_and_restart(self):
        old = self.root/'old.mp4'; old.write_bytes(b'old')
        self.monitor.tick()
        new = self.root/'new.mp4'; new.write_bytes(b'first')
        with patch('mechanical_video.av_technical_review.write_review', side_effect=self.fake_report) as scan:
            self.monitor.tick(); self.assertEqual(scan.call_count,0)
            new.write_bytes(b'second')
            self.monitor.tick(); self.assertEqual(scan.call_count,0)
            self.monitor.tick(); self.assertEqual(scan.call_count,1)
            self.monitor.review([new]); self.assertEqual(scan.call_count,1)
            auto.Monitor([self.root], self.monitor.output, settle=0).tick()
            self.assertEqual(scan.call_count,1)
            new.write_bytes(b'third')
            self.monitor.tick(); self.monitor.tick(); self.assertEqual(scan.call_count,2)
        state=json.loads((self.monitor.output/'state.json').read_text())
        self.assertEqual(state['files'][str(old)]['status'],'baseline')
        self.assertEqual(len(state['jobs']),2)
        self.assertTrue(all(not j['formal_acceptance'] for j in state['jobs'].values()))

    def test_mutating_input_is_not_completed(self):
        video=self.root/'new.mp4';video.write_bytes(b'first')
        def mutate(source, output, **kw):
            report=self.fake_report(source,output,**kw)
            video.write_bytes(b'changed during scan')
            return report
        with patch('mechanical_video.av_technical_review.write_review', side_effect=mutate):
            receipt=self.monitor.review([video])[0]
        self.assertEqual(receipt['status'],'failed')
        self.assertIn('source changed',receipt['error'])

    def test_failure_does_not_loop_or_accept(self):
        self.monitor.tick()
        video=self.root/'bad.mp4';video.write_bytes(b'broken')
        with patch('mechanical_video.av_technical_review.write_review', side_effect=ValueError('decode failed')) as scan:
            self.monitor.tick();self.monitor.tick();self.monitor.tick()
            self.assertEqual(scan.call_count,1)
        state=json.loads((self.monitor.output/'state.json').read_text())
        self.assertEqual(state['files'][str(video)]['status'],'failed')

    def test_bound_production_runs_review_automatically(self):
        video=self.root/'new.mp4'
        command=[sys.executable,'-c','from pathlib import Path;Path('+repr(str(video))+').write_bytes(b"fixture")']
        record=self.root/'director.json'
        record.write_text(json.dumps(dict(production_checks=dict(execution={'full-render':command},content_review=dict(execution={'full-render':command})),repair_controller=dict(tasks={'render':dict(outputs=['new.mp4'])},executions={'token':dict(task_id='render')}))))
        with patch.object(production_run,'evaluate',return_value={'status':'READY'}), patch('mechanical_video.repair_controller.start_execution',return_value='token'), patch('mechanical_video.repair_controller.finish_execution'), patch.object(auto,'DEFAULT_OUTPUT',self.monitor.output), patch('mechanical_video.av_technical_review.write_review',side_effect=self.fake_report):
            result,code=production_run.run(record,'full-render',command)
        self.assertEqual(code,0)
        self.assertEqual(result['automatic_technical_review']['status'],'complete')
        self.assertEqual(json.loads(record.read_text())['repair_controller']['tasks']['render']['automatic_technical_review']['reports'][0]['observations'],1)

    def test_failed_review_preserves_successful_command_and_nonzero_exit(self):
        command=[sys.executable,'-c','pass']
        record=self.root/'director.json'
        record.write_text(json.dumps(dict(production_checks=dict(execution={'full-render':command},content_review=dict(execution={'full-render':command})),repair_controller=dict(tasks={'render':dict(outputs=['missing.mp4'])},executions={'token':dict(task_id='render')}))))
        with patch.object(production_run,'evaluate',return_value={'status':'READY'}), patch('mechanical_video.repair_controller.start_execution',return_value='token'), patch('mechanical_video.repair_controller.finish_execution') as finish, patch.object(auto,'DEFAULT_OUTPUT',self.monitor.output):
            result,code=production_run.run(record,'full-render',command)
        self.assertEqual(code,2)
        self.assertEqual(result['returncode'],0)
        finish.assert_called_once_with(record.resolve(),'token',0)
        self.assertEqual(result['automatic_technical_review']['status'],'failed')

    def test_report_handed_to_independent_review(self):
        from mechanical_video.repair_controller import _review
        task=dict(id='render',stage='render',status='done',agent_id='producer',deps=[],inputs={},required_checks=['scene'],capabilities=[],automatic_technical_review={'status':'complete','formal_acceptance':False})
        state=dict(tasks={'render':task})
        _review(state,task,{'new.mp4':'hash'})
        reviewer=state['tasks']['render:review']
        self.assertEqual(reviewer['automatic_technical_reviews'][0],task['automatic_technical_review'])
        self.assertEqual(reviewer['status'],'pending')
        self.assertIn('producer',reviewer['excluded_agents'])

    def test_real_ffmpeg_auto_discovery(self):
        self.monitor.tick()
        video=self.root/'real.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=black:s=64x64:r=30:d=1','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t','1','-c:v','libx264','-c:a','aac',str(video)],check=True)
        self.monitor.tick();state=self.monitor.tick()
        receipt=state['files'][str(video)]['receipt']
        self.assertEqual(receipt['status'],'complete')
        self.assertEqual(receipt['coverage']['video_frames'],30)
        report=json.loads(Path(receipt['report']).read_text())
        self.assertTrue({'black','freeze','dropout'} <= {f['kind'] for f in report['findings']})
        self.assertEqual(report['source']['sha256'],auto.fingerprint(video))


if __name__=='__main__':unittest.main()
