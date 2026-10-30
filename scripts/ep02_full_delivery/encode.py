"""Encode the approved EP02 full revision after every native frame exists.

Owns only editor outputs. Never edits renderer archives, frames, or source CAD.
Run --prepare while rendering, then --encode once the source sequence is ready.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'series/3d-printer-v2/revisions/EP02/approved-full-90d7695b1599bcb663a6'
BASE = ROOT / 'series/3d-printer-v2/revisions/EP02/b0d7b1803fe781968c2e'
MODEL = ROOT / 'series/3d-printer-v2/models/source-repair-280890c41faa1c14/assembly.json'
APPROVAL = ROOT / 'series/3d-printer-v2/revisions/EP02/corrected-panel-motion-20261030/user-preview-accepted.json'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temporary.replace(path)


def seconds(value):
    h, m, s = value.replace(',', '.').split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


def audit_subtitles(path, duration):
    entries = []
    previous = 0
    for block in path.read_text().strip().split('\n\n'):
        lines = block.splitlines()
        if len(lines) != 3:
            raise ValueError('Subtitle must have one text line: ' + repr(block))
        start, end = map(seconds, lines[1].split(' --> '))
        text = lines[2]
        if not (previous <= start < end <= duration and 0 < len(text) <= 20):
            raise ValueError('Invalid subtitle length or interval: ' + repr(block))
        previous = end
        entries.append(dict(id=int(lines[0]), start=start, end=end, text=text, chars=len(text)))
    if not entries:
        raise ValueError('No subtitles')
    return dict(count=len(entries), max_chars=max(e['chars'] for e in entries),
                single_line=True, no_overlap=True, entries=entries,
                alignment='Original measured Kai clip boundaries; not forced alignment or listening evidence')


def current_inputs(folder):
    job = load(folder / 'job.json')
    fingerprints = load(folder / 'fingerprints.json')
    paths = dict(scene=folder / 'scene.py', job=folder / 'job.json',
                 model=MODEL, source_scene=Path(job['source_scene']),
                 audio=BASE / 'mixed-audio.wav', subtitles=BASE / 'narration.zh.srt',
                 approval=APPROVAL)
    hashes = {name: digest(path) for name, path in paths.items()}
    for name in ('scene', 'model', 'source_scene'):
        if hashes[name] != fingerprints[name + '_sha256']:
            raise ValueError('Renderer fingerprint changed: ' + name)
    if hashes['model'] != job['model_sha256']:
        raise ValueError('Job model differs from source model')
    if Path(job['folder']).resolve() != folder or job['frames'] != 3210 or job['duration'] != 107:
        raise ValueError('Unexpected job folder/timeline')
    if fingerprints['native_fps'] != 30 or fingerprints['source_resolution'] != [540, 960]:
        raise ValueError('Unexpected source sampling/resolution')
    return job, paths, hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=DEFAULT)
    parser.add_argument('--encode', action='store_true')
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    folder = args.folder.resolve()
    job, paths, hashes = current_inputs(folder)
    subtitles = audit_subtitles(paths['subtitles'], job['duration'])
    plan = dict(inputs={name: str(path) for name, path in paths.items()}, input_sha256=hashes,
                source=dict(frame_directory=str(folder / 'preview'), expected_frames=3210,
                            native_fps=30, native_resolution=[540, 960]),
                output=dict(path=str(folder / 'EP02.mp4'), duration=107, fps=30,
                            resolution=[1080, 1920], video='h264', audio='aac',
                            upscaled_from_source=True),
                subtitle_style='Heiti SC; single line; <=20 characters; MarginV=58',
                illustrative_label='Movement and force schematic, not simulation; transparent print label at49–69s',
                acceptance='Encoding and signal evidence only. Human preview approval is separate from audio understanding and full-film QA.')
    plan_file = folder / 'encode-plan.json'
    if plan_file.exists() and load(plan_file) != plan:
        raise ValueError('Encoding inputs changed since preparation; create a new revision')
    if not plan_file.exists():
        save(plan_file, plan)
    archive = folder / 'encode.py'
    if archive.exists() and digest(archive) != digest(Path(__file__)):
        raise ValueError('Archived encoder changed; create a new revision')
    if not archive.exists():
        shutil.copy2(Path(__file__), archive)
    save(folder / 'subtitle-audit.json', subtitles)
    expected = [f'{i:06}.jpg' for i in range(1, 3211)]
    actual = sorted(p.name for p in (folder / 'preview').glob('*.jpg'))
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    readiness = dict(state='READY_FOR_ENCODING' if not missing and not extra else 'WAITING_FOR_RENDER',
                     expected=3210, present=len(actual), missing_count=len(missing),
                     first_missing=missing[:8], extra=extra,
                     native_source=[540, 960], fps=30)
    save(folder / 'encode-readiness.json', readiness)
    print(json.dumps(readiness), flush=True)
    if not args.encode:
        return
    if missing or extra:
        raise SystemExit('Waiting: source sequence is not complete; no output encoded')
    from PIL import Image
    inventory = {}
    for name in expected:
        frame = folder / 'preview' / name
        with Image.open(frame) as image:
            if image.size != (540, 960) or image.format != 'JPEG':
                raise ValueError('Unexpected source image: ' + name)
        inventory[name] = digest(frame)
    save(folder / 'encoded-frame-inventory.json', dict(frame_directory='preview',
         native_fps=30, source_resolution=[540, 960], frames=inventory,
         scene_sha256=hashes['scene'], model_sha256=hashes['model']))
    final = folder / 'EP02.mp4'
    verification_file = folder / 'encoding-verification.json'
    if final.exists():
        if verification_file.exists() and load(verification_file)['sha256'] == digest(final):
            print('Existing encoded output preserved: ' + str(final))
            return
        raise ValueError('Existing output without matching verification; preserve and review')
    for name in ('audio', 'subtitles'):
        target = folder / ('mixed-audio.wav' if name == 'audio' else 'narration.zh.srt')
        if target.exists() and digest(target) != hashes[name]:
            raise ValueError('Editor asset differs from pinned baseline: ' + name)
        if not target.exists():
            shutil.copy2(paths[name], target)
    srt = folder / 'narration.zh.srt'
    font = '/System/Library/Fonts/STHeiti Medium.ttc'
    vf = (f"scale=1080:1920,subtitles='{srt}':force_style='FontName=Heiti SC,FontSize=7,Alignment=2,MarginL=18,MarginR=18,MarginV=58',"
          f"drawtext=fontfile='{font}':text='运动与受力为示意 非仿真':fontsize=28:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=8:x=45:y=100,"
          f"drawtext=fontfile='{font}':text='源CAD装配 受力为示意':fontsize=26:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=6:x=45:y=150:enable='not(between(t,49,69))',"
          f"drawtext=fontfile='{font}':text='透明剖视与已有打印件为示意':fontsize=26:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=6:x=45:y=150:enable='between(t,49,69)'")
    temporary = folder / 'EP02.encoding.mp4'
    command = ['ffmpeg', '-y', '-v', 'warning', '-framerate', '30', '-start_number', '1',
               '-i', str(folder / 'preview/%06d.jpg'), '-i', str(folder / 'mixed-audio.wav'),
               '-map', '0:v:0', '-map', '1:a:0', '-vf', vf, '-t', '107', '-frames:v', '3210',
               '-r', '30', '-c:v', 'libx264', '-threads', '4', '-preset', 'fast', '-crf', '19',
               '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '48000', '-movflags', '+faststart', str(temporary)]
    with (folder / 'encode.log').open('a') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(temporary)]))
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    if (video['codec_name'], video['width'], video['height'], video['avg_frame_rate'], int(video['nb_frames'])) != ('h264', 1080, 1920, '30/1', 3210):
        raise ValueError('Encoded video format mismatch')
    if audio['codec_name'] != 'aac' or abs(float(probe['format']['duration']) - 107) > .05:
        raise ValueError('Encoded duration/audio mismatch')
    with (folder / 'full-decode.log').open('w') as log:
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(temporary), '-f', 'null', '-'], stdout=log, stderr=subprocess.STDOUT, check=True)
    temporary.replace(final)
    save(verification_file, dict(path=str(final), sha256=digest(final), probe=probe,
        full_audio_video_decode='passed', source_frames=3210, source_fps=30,
        native_source_resolution=[540, 960], output_resolution=[1080, 1920], upscaled=True,
        input_sha256=hashes, encoder_sha256=digest(archive),
        subtitle_count=subtitles['count'], subtitle_max_chars=subtitles['max_chars'],
        timeline='107 seconds, unchanged measured Kai mix and subtitle boundaries',
        mechanical_audio_audience_acceptance='Not inferred from encoding; independent QA required'))
    print('Encoded and fully decoded: ' + str(final), flush=True)


if __name__ == '__main__':
    main()
