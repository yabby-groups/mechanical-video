"""GPU-preflighted native Blender inventory capture; no rendering or retries."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from . import scene_fidelity
from .runtime import GPUUnavailable, exclusive_lock, require_metal_device

ROOT = Path(__file__).resolve().parents[1]


def capture(source, renderer, output, blender=None, frame=None, timeout=120, cad_objects=()):
    source, renderer, output = Path(source).resolve(), Path(renderer).resolve(), Path(output).resolve()
    inputs = {'source': scene_fidelity.file_ref(source), 'renderer': scene_fidelity.file_ref(renderer),
              'implementation': scene_fidelity.file_ref(scene_fidelity.__file__)}
    if source.suffix.lower() != '.blend' or timeout <= 0 or (frame is not None and type(frame) is not int):
        raise ValueError('Invalid capture inputs')
    if output.exists():
        raise ValueError('Output must be a new task directory')
    if not isinstance(cad_objects, (list, tuple)) or any(not isinstance(n, str) or not n for n in cad_objects):
        raise ValueError('Invalid CAD object names')
    # A sandbox without Metal must not launch Blender and consume a crash attempt.
    require_metal_device()
    executable = blender or os.environ.get('BLENDER_BIN') or shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender'
    with exclusive_lock(ROOT / 'render.lock'):
        output.mkdir(parents=True, exist_ok=False)
        worker = output / 'capture-worker.py'
        worker.write_bytes(Path(__file__).with_name('native_capture_worker.py').read_bytes())
        job = dict(inputs, project_root=str(ROOT), output=str(output), frame=frame, cad_objects=list(cad_objects),
                   worker=scene_fidelity.file_ref(worker))
        request = output / 'request.json'
        request.write_text(json.dumps(job, ensure_ascii=False, indent=2))
        command = [str(executable), '-b', '--disable-autoexec', '--python-exit-code', '1',
                   '--python', str(worker), '--', str(request)]
        result = {'status': 'BLOCKED', 'scope': 'Native saved-scene inventory only; no rendering or media acceptance',
                  'request_sha256': scene_fidelity.file_ref(request)['sha256'],
                  'command': command, 'log': str(output / 'blender.log')}
        with (output / 'blender.log').open('x') as log:
            try:
                process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False, timeout=timeout)
                result['returncode'] = process.returncode
                if process.returncode:
                    result['reason'] = 'Blender failed; preserve this task and diagnose before a new attempt'
                else:
                    inventory = json.loads((output / 'scene-inventory.json').read_text())
                    scene_fidelity.compare(inventory, inventory)  # Validate native schema/nonempty data, not just exit0.
                    unchanged = all(scene_fidelity.file_ref(ref['path'])['sha256'] == ref['sha256'] for ref in inputs.values())
                    if (not unchanged or inventory.get('source') != inputs['source']
                            or inventory.get('renderer') != inputs['renderer']
                            or inventory.get('implementation_sha256') != inputs['implementation']['sha256']
                            or any(not inventory['objects'].get(n, {}).get('cad_geometry') for n in cad_objects)):
                        result['reason'] = 'Capture input association changed'
                    else:
                        result.update(status='PASS', source_unchanged=True, objects=len(inventory['objects']),
                                      inventory=scene_fidelity.file_ref(output / 'scene-inventory.json'))
            except subprocess.TimeoutExpired:
                result['reason'] = 'Blender capture timed out; no automatic retry'
            except (OSError, ValueError, KeyError, TypeError):
                result['reason'] = 'Missing or invalid native inventory'
        (output / 'capture-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--renderer', type=Path, required=True, help='Frozen renderer identity; not executed')
    parser.add_argument('--output', type=Path, required=True, help='New capture task directory')
    parser.add_argument('--frame', type=int, help='Default: frame stored in the saved scene')
    parser.add_argument('--blender', help='Default: BLENDER_BIN, PATH, or installed macOS Blender')
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('--cad-object', action='append', default=[], help='Actual mesh name for evaluated CAD geometry; repeat for local mechanism')
    args = parser.parse_args(argv)
    try:
        result = capture(args.scene, args.renderer, args.output, args.blender, args.frame, args.timeout, args.cad_object)
    except GPUUnavailable:
        print(json.dumps({'status': 'GPU_ACCESS_REQUIRED', 'blender_started': False,
                          'next_action': 'Run this same command through the executor-approved host GPU path; keep sandbox configuration unchanged.'}))
        return 3
    except (OSError, ValueError, RuntimeError):
        print(json.dumps({'status': 'BLOCKED', 'reason': 'Invalid inputs, occupied render lock, or existing output; no automatic retry'}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
