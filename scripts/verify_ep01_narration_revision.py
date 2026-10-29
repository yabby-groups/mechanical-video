"""Verify the archived EP01 revision and its rendered media."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(folder, stage):
    root = Path(__file__).resolve().parents[1]
    archive = folder / 'renderer'
    hashes = json.loads((archive / 'fingerprints.json').read_text())
    for name, expected in hashes.items():
        if name not in ('master', 'source_scene'):
            assert digest(archive / name) == expected, name
    job = json.loads((folder / 'job.json').read_text())
    assert digest(Path(job['source_scene'])) == hashes['source_scene']
    assert job['model_sha256'] == hashes['master']
    assert digest(root / 'series/3d-printer/master_assembly/assembly.json') == hashes['master']
    assert (root / 'series/3d-printer-v2/editorial-hold.json').is_file()
    director = json.loads((archive / 'director.json').read_text())
    audio = json.loads((folder / 'audio-timeline.json').read_text())
    assert (audio['model'], audio['voice']) == ('qwen3-tts-flash', 'Moon')
    assert [e['text'] for e in audio['events']] == [e['text'] for e in director['narration']]
    for i, event in enumerate(audio['events']):
        assert event['end'] < (audio['events'][i + 1]['start'] if i + 1 < len(audio['events']) else 100)
    blocks = (folder / 'narration.zh.srt').read_text().strip().split('\n\n')
    assert all(len(b.splitlines()) == 3 and 0 < len(b.splitlines()[2]) <= 20 for b in blocks)
    assert ''.join(b.splitlines()[2] for b in blocks) == ''.join(e['text'] for e in audio['events'])
    audit = json.loads((folder / f'{stage}-audit.json').read_text())
    expected_pairs = 1499 if stage == 'preview' else 2999
    assert audit['source_parts'] == 1428 and audit['hard_cuts'] == audit['visibility_changes'] == 0
    assert len(audit['continuity']) == len(audit['gear_continuity']) == expected_pairs
    gears = audit['gear_continuity']
    contact = max(abs(row[name][2] + .0025) for row in gears for name in ('drive_contact_m_s', 'idler_contact_m_s'))
    marker = max(abs(row['filament_marker_speed_m_s'] + .0025) for row in gears)
    shaft = max(row['shaft_angular_error_rad_s'] for row in gears)
    assert contact < .00002 and marker < .00002 and shaft < .01
    video = folder / ('preview.mp4' if stage == 'preview' else 'EP01.mp4')
    previous = json.loads((folder / f'{stage}-verification.json').read_text())
    assert previous['passed'] and previous['full_decode'] == 'passed' and digest(video) == previous['video_sha256']
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video)]))
    v = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    a = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    assert (v['codec_name'], v['width'], v['height'], v['r_frame_rate'], int(v['nb_frames']), a['codec_name']) == ('h264', 1080, 1920, '30/1', 3000, 'aac')
    assert abs(float(probe['format']['duration']) - 100) < .1
    frames = folder / ('preview' if stage == 'preview' else 'frames')
    stride = 2 if stage == 'preview' else 1
    assert sorted(p.name for p in frames.glob('*.jpg')) == [f'{n:06}.jpg' for n in range(1, 3001, stride)]
    for path in frames.glob('*.jpg'):
        with path.open('rb') as image:
            image.seek(-2, 2)
            assert image.read() == b'\xff\xd9', path
    return dict(passed=True, stage=stage, video_sha256=digest(video), subtitle_count=len(blocks),
                maximum_subtitle_chars=max(len(b.splitlines()[2]) for b in blocks),
                spoken_seconds=audio['spoken_seconds'], frame_pairs=expected_pairs,
                contact_error_m_s=contact, marker_error_m_s=marker, shaft_error_rad_s=shaft,
                full_decode=previous['full_decode'], subjective_acceptance='pending')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    parser.add_argument('--stage', choices=('preview', 'production'), default='preview')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    report = json.dumps(verify(args.folder, args.stage), indent=2)
    if args.write:
        (args.folder / f'{args.stage}-independent-verification.json').write_text(report + '\n')
    print(report)
