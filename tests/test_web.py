"""HTTP acceptance with a real tiny H.264 fixture in an isolated directory."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import requests
from mechanical_video.cli import enqueue,connect

class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(); cls.root=Path(cls.temp.name)
        manifest=cls.root/'assembly.json'; manifest.write_text('{}')
        result=enqueue(cls.root,manifest,['closeup'],seconds=1)[0]; cls.key=result['id']
        con=connect(cls.root); spec=json.loads(con.execute('SELECT spec FROM jobs WHERE id=?',(cls.key,)).fetchone()[0])
        cls.video=Path(spec['directory'])/'video.mp4'
        subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=blue:s=16x16:r=30','-t','0.1','-c:v','libx264','-pix_fmt','yuv420p',str(cls.video)],check=True)
        con.execute("UPDATE jobs SET state='done'"); con.commit(); con.close()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
        cls.url=f'http://127.0.0.1:{port}'
        code=f'from pathlib import Path; from mechanical_video.web import serve; serve(Path({str(cls.root)!r}),{port})'
        cls.process=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                requests.get(cls.url+'/config',timeout=.2).raise_for_status(); break
            except requests.RequestException: time.sleep(.05)
        else:
            cls.process.terminate(); cls.process.wait(); cls.temp.cleanup(); raise RuntimeError('Test HTTP server did not start')
    @classmethod
    def tearDownClass(cls):
        cls.process.terminate(); cls.process.wait(timeout=5); cls.temp.cleanup()
    def test_video_supports_seeking_and_suffix_ranges(self):
        raw=self.video.read_bytes(); url=self.url+'/video/'+self.key
        full=requests.get(url,timeout=5); self.assertEqual(full.content,raw)
        chunk=requests.get(url,headers={'Range':'bytes=0-63'},timeout=5)
        self.assertEqual(chunk.status_code,206); self.assertEqual(chunk.content,raw[:64]); self.assertEqual(chunk.headers['Content-Range'],f'bytes 0-63/{len(raw)}')
        suffix=requests.get(url,headers={'Range':'bytes=-32'},timeout=5)
        self.assertEqual(suffix.content,raw[-32:])
        bad=requests.get(url,headers={'Range':f'bytes={len(raw)}-'},timeout=5)
        self.assertEqual(bad.status_code,416)
        self.assertEqual(requests.get(url,headers={'Range':'bytes=-0'},timeout=5).status_code,416)
    def test_status_has_product_metadata_and_rejects_invalid_requests(self):
        rows=requests.get(self.url+'/status',timeout=5).json(); self.assertEqual(rows[0]['template'],'closeup'); self.assertEqual(rows[0]['seconds'],1)
        bad=requests.post(self.url+'/batch',json={'templates':['explode'],'portrait':'false'},timeout=5)
        self.assertEqual(bad.status_code,422)
        bad=requests.post(self.url+'/upload',data=b'not an image',headers={'Content-Type':'text/plain'},timeout=5)
        self.assertEqual(bad.status_code,415)
        origin=requests.post(self.url+'/batch',json={},headers={'Origin':'http://other.invalid'},timeout=5)
        self.assertEqual(origin.status_code,403)
