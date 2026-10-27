"""Read-only host diagnostics; never installs system packages."""
import json
import platform
import shutil
import subprocess
from pathlib import Path

def report():
    tools={}
    for name in ['python3','uv','ffmpeg','ffprobe','node','brew']:
        exe=shutil.which(name)
        if exe:
            args=[exe,'--version'] if name not in ('ffmpeg','ffprobe') else [exe,'-version']
            r=subprocess.run(args,capture_output=True,text=True)
            tools[name]={'path':exe,'version':(r.stdout or r.stderr).splitlines()[0]}
        else: tools[name]={'available':False}
    blender=shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender'
    tools['blender']={'path':blender,'exists':Path(blender).exists()}
    import build123d
    return {'system':platform.platform(),'architecture':platform.machine(),'python':platform.python_version(),'build123d':build123d.__version__,'tools':tools,'render_concurrency':1,'default_engine':'Eevee','triposr':'disabled, runtime compatibility unverified'}
if __name__=='__main__': print(json.dumps(report(),indent=2))
