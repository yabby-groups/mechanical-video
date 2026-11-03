"""Executed only by native_capture in a new, fingerprinted Blender task."""
import json
from pathlib import Path
import sys


def main():
    import bpy
    request = Path(sys.argv[sys.argv.index('--') + 1])
    job = json.loads(request.read_text())
    sys.path.insert(0, job['project_root'])
    from mechanical_video.scene_fidelity import file_ref, write_inventory
    for name in ('source', 'renderer', 'implementation', 'worker'):
        ref = job[name]
        if file_ref(ref['path']) != ref:
            raise ValueError('Capture input changed: ' + name)
    bpy.ops.wm.open_mainfile(filepath=job['source']['path'], load_ui=False, use_scripts=False)
    if job['frame'] is not None:
        bpy.context.scene.frame_set(job['frame'])
    inventory = write_inventory(Path(job['output']) / 'scene-inventory.json', bpy.context.scene,
                                job['source']['path'], job['renderer']['path'])
    print('NATIVE_CAPTURE_COMPLETE', len(inventory['objects']), flush=True)


if __name__ == '__main__':
    main()
