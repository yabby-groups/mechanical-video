"""Exercise every archived scene pose without treating placeholder images as output."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mechanical_video.runtime import exclusive_lock


def main(folder):
    folder = folder.resolve()
    placeholder = (folder/'preview/000001.jpg').resolve()
    if not placeholder.read_bytes().endswith(b'\xff\xd9'):
        raise ValueError('Preview placeholder is not a complete JPEG')
    job = json.loads((folder/'job.json').read_text())
    with tempfile.TemporaryDirectory(prefix='ep01-kinematics-', dir='/private/tmp') as temp:
        temp = Path(temp)
        frames = temp/'frames'
        frames.mkdir()
        for frame in range(1, 3001):
            (frames/f'{frame:06}.jpg').symlink_to(placeholder)
        job['folder'] = str(temp)
        (temp/'job.json').write_text(json.dumps(job))
        with exclusive_lock(ROOT/'artifacts/render.lock', blocking=True):
            subprocess.run(['/Applications/Blender.app/Contents/MacOS/Blender', '-b', '-t', '2',
                            '--python-exit-code', '1', '--python', str(folder/'renderer/scene.py'),
                            '--', str(temp/'job.json'), 'production'], check=True)
        audit = json.loads((temp/'production-audit.json').read_text())
        gear = audit['gear_continuity']
        if len(gear) != 2999:
            raise ValueError('Incomplete 30fps kinematics preflight')
        report = dict(passed=True, frames=3000, gear_pairs=len(gear),
                      scope='Archived scene poses and matrices only; no production pixels rendered',
                      maximum_contact_speed_error_m_s=max(abs(row[name][2]+.0025) for row in gear
                          for name in ('drive_contact_m_s', 'idler_contact_m_s')),
                      maximum_marker_speed_error_m_s=max(abs(row['filament_marker_speed_m_s']+.0025) for row in gear),
                      maximum_shaft_angular_error_rad_s=max(row['shaft_angular_error_rad_s'] for row in gear),
                      inspector_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        (folder/'production-kinematics-preflight.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]))
