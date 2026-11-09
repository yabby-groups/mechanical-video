import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from mechanical_video import production_gate, production_run


class ControllerIntegrationTests(unittest.TestCase):
    def test_v4_not_promoted_to_new_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); command=['not-executed']
            record={'production_checks':{'schema_version':4,'execution':{'narration':command},
                    'content_review':{'execution':{'narration':command}}}}
            path=base/'record.json';path.write_text(json.dumps(record))
            with patch.object(production_run.subprocess,'run') as launch:
                report, code=production_run.run(path,'narration',command)
            self.assertEqual(code,1);launch.assert_not_called()
            self.assertIn('v5 required', ' '.join(report['reasons']))

    def test_v5_requires_controller_even_with_content_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            record={'production_checks':{'schema_version':5}}
            with patch('mechanical_video.content_contract.evaluate',return_value=[]):
                result=production_gate.evaluate(record,Path(tmp),'narration',require_version=5)
            self.assertEqual(result['status'],'BLOCKED')
            self.assertIn('missing repair_controller v1',result['reasons'])

    def test_programmatic_production_enqueue_cannot_bypass_record(self):
        from mechanical_video.cli import enqueue
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'controller-bound'):
                enqueue(Path(tmp),Path(tmp)/'manifest.json',['shell'],production=True)
