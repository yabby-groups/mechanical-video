"""Generate a portable local catalog of verified outputs and cached models."""
import html
import json
from pathlib import Path
from .cli import ROOT,connect

def generate(root):
    con=connect(root); items=[]
    for row in con.execute("SELECT id,spec FROM jobs WHERE state='done' ORDER BY updated"):
        spec=json.loads(row['spec']); folder=Path(spec['directory']); video=folder/'video.mp4'; report=folder/'video.verification.json'
        if video.exists() and report.exists():
            items.append({'id':row['id'],'template':spec['template'],'video':str(video.relative_to(root)),'scene':str((folder/'scene.blend').relative_to(root)),'manifest':spec['manifest'],'engine':spec.get('engine','eevee'),'verification':json.loads(report.read_text())})
    con.close()
    (root/'catalog.json').write_text(json.dumps(items,indent=2))
    cards=[]
    for item in items:
        cards.append(f'<article><h2>{html.escape(item["template"])}</h2><video controls preload="metadata" src="{item["video"]}"></video><p><a href="{item["scene"]}">Blender scene</a> · {item["verification"]["width"]} × {item["verification"]["height"]} · {html.escape(item["verification"]["duration"])} s · {html.escape(item["engine"])} · H.264</p></article>')
    (root/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Mechanical Video outputs</title><style>body{background:#101927;color:#def;font:16px system-ui;max-width:1100px;margin:40px auto}article{margin:30px 0}video{width:100%}a{color:#8df}</style><h1>Mechanical Video / verified outputs</h1>'+''.join(cards))
    print(root/'index.html')
if __name__=='__main__': generate(ROOT/'artifacts')
