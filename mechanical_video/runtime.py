"""Project-local leases and immutable render inputs."""
from contextlib import contextmanager
import fcntl
import hashlib
from pathlib import Path
import runpy
import ctypes
import sys

class GPUUnavailable(RuntimeError):
    pass

def require_metal_device():
    """Fail before Blender startup when this process cannot access Metal."""
    if sys.platform != 'darwin':
        return
    try:
        metal=ctypes.CDLL('/System/Library/Frameworks/Metal.framework/Metal')
        metal.MTLCreateSystemDefaultDevice.restype=ctypes.c_void_p
        device=metal.MTLCreateSystemDefaultDevice()
    except (OSError, AttributeError) as exc:
        raise GPUUnavailable('Metal device probe failed; run the pipeline with GPU access') from exc
    if not device:
        raise GPUUnavailable('No Metal device visible; run the pipeline with GPU access')

RENDER_FILES=('blender_scene.py','audit_scene.py','narration.py')
SOURCE=Path(__file__).resolve().parent

@contextmanager
def exclusive_lock(path,blocking=False):
    with path.open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError as exc:
            raise RuntimeError(f'Project lease is already held: {path.name}') from exc
        try: yield
        finally: fcntl.flock(lock,fcntl.LOCK_UN)

def source_fingerprints():
    return {name:hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() for name in RENDER_FILES}

def snapshot_sources(folder,expected):
    target=folder/'renderer'; target.mkdir(parents=True,exist_ok=True)
    for name in RENDER_FILES:
        payload=(SOURCE/name).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=expected[name]:
            raise ValueError('Render source changed while enqueuing; retry enqueue')
        path=target/name
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest()!=expected[name]:
                raise ValueError(f'Archived renderer was modified: {name}')
        else: path.write_bytes(payload)

def render_sources(folder,spec):
    expected=spec.get('renderer_files')
    if not expected: return SOURCE  # Legacy assets remain usable.
    if set(expected)!=set(RENDER_FILES): raise ValueError('Invalid renderer manifest')
    target=folder/'renderer'
    for name,digest in expected.items():
        path=target/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError(f'Archived renderer missing or modified: {name}')
    return target

def caption_video(folder,spec):
    module=runpy.run_path(str(render_sources(folder,spec)/'narration.py'))
    module['attach'](folder,spec['template'],spec['seconds'])
