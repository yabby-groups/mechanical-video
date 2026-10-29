"""Check encoded gear-tooth movement in the stable front-view close-up."""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np


def main(folder, production):
    folder = folder.resolve()
    mode = 'production' if production else 'preview'
    video = folder/('EP01.mp4' if production else 'preview.mp4')
    raw = subprocess.check_output([
        'ffmpeg', '-v', 'error', '-ss', '8', '-i', str(video), '-t', '1.34',
        '-vf', 'fps=15,scale=270:480', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'
    ])
    images = np.frombuffer(raw, np.uint8).reshape(-1, 480, 270, 3).astype(float)
    if len(images) < 18:
        raise ValueError('Insufficient encoded gear close-up frames')

    def copper_mask(image):
        return ((image[:, :, 0] > 45) & (image[:, :, 0] > image[:, :, 1]*1.4)
                & (image[:, :, 0] > image[:, :, 2]*1.6))

    y, x = np.where(copper_mask(images[0]))
    if len(x) < 100:
        raise ValueError('Gear highlight was not found')
    cx, cy = (x.min()+x.max())/2, (y.min()+y.max())/2
    theta = np.arange(720)*2*np.pi/720
    profiles = []
    for image in images:
        mask = copper_mask(image)
        rings = []
        for radius in range(73, 85):
            px = np.clip(np.rint(cx+radius*np.cos(theta)).astype(int), 0, 269)
            py = np.clip(np.rint(cy+radius*np.sin(theta)).astype(int), 0, 479)
            rings.append(mask[py, px].astype(float))
        profiles.append(np.mean(rings, axis=0))

    scores = []
    for step in range(-7, 8):
        score = sum(float(np.mean((a-np.mean(a))*(np.roll(b, -step)-np.mean(b))))
                    for a, b in zip(profiles, profiles[1:]))
        scores.append((score, step*.5))
    score, angle = max(scores)
    kinematics = json.loads((folder/'gear-kinematics.json').read_text())
    expected = abs(kinematics['large_gear']['rate_rad_s'])*180/math.pi/15
    if score <= 0 or angle >= 0 or abs(abs(angle)-expected) > 1.25:
        raise ValueError(f'Encoded tooth direction or rate did not match: {angle} degrees')
    report = dict(passed=True, mode=mode, decoded_frames=len(images), sample_fps=15,
                  screen_rotation='counterclockwise', measured_degrees_per_sample=angle,
                  expected_magnitude_degrees_per_sample=expected,
                  scope='Copper-tooth image correlation at 8-9.34 seconds; screen y increases downward')
    (folder/f'{mode}-visual-direction.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]), '--production' in sys.argv[2:])
