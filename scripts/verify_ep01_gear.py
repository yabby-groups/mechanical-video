"""Independent delivery and feed-motion checks for the corrected EP01."""
import argparse, hashlib, json, re, sqlite3, subprocess
from pathlib import Path
from PIL import Image, ImageDraw

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(folder,production=False):
    root=Path(__file__).resolve().parents[1]
    hashes=json.loads((folder/'renderer/fingerprints.json').read_text())
    for name,h in hashes.items():
        if name in ('master','source_scene'): continue
        assert digest(folder/'renderer'/name)==h
    job=json.loads((folder/'job.json').read_text())
    assert digest(Path(job['source_scene']))==job['source_scene_sha256']
    model=root/'series/3d-printer/master_assembly/assembly.json'
    assert digest(model)==job['model_sha256']==hashes['master']
    parts=json.loads(model.read_text())['parts']
    assert all(p['valid'] and p['volume_mm3']>0 and (model.parent/p['mesh']).is_file() for p in parts)
    baseline=json.loads((folder/'preservation-baseline.json').read_text())
    assert all(digest(root/p)==h for p,h in baseline['files'].items())
    c=sqlite3.connect(f'file:{root}/series/3d-printer-v2/queue.sqlite?mode=ro',uri=True)
    assert [list(r) for r in c.execute('select * from episodes order by number')]==baseline['queue']
    blocks=(folder/'narration.zh.srt').read_text().strip().split('\n\n')
    assert len(blocks)==8
    captions=[]
    for block in blocks:
        lines=block.splitlines(); assert len(lines)==3 and 0<len(lines[2])<=20
        captions.append(len(lines[2]))
    audio=json.loads((folder/'audio-timeline.json').read_text())
    assert audio['voice']=='Moon' and audio['model']=='qwen3-tts-flash' and 25<=audio['spoken_seconds']<=40
    mode='production' if production else 'preview'
    audit=json.loads((folder/f'{mode}-audit.json').read_text())
    assert audit['source_parts']==len(parts)==1428
    assert len(audit['continuity'])==(2999 if production else 1499)
    assert audit['hard_cuts']==audit['visibility_changes']==0
    gears=audit['gear_continuity']
    assert len(gears)==len(audit['continuity'])
    kinematics=json.loads((folder/'gear-kinematics.json').read_text())
    speed=kinematics['feed_speed_m_s']
    assert speed==.0025 and kinematics['preview_sample_fps']==15 and kinematics['large_gear_tooth_cycles_hz']<.4*kinematics['preview_sample_fps']
    contact_error=max(abs(row[name][2]+speed) for row in gears for name in ('drive_contact_m_s','idler_contact_m_s'))
    marker_error=max(abs(row['filament_marker_speed_m_s']+speed) for row in gears)
    shaft_error=max(row['shaft_angular_error_rad_s'] for row in gears)
    assert contact_error<.00002 and marker_error<.00002 and shaft_error<.01
    verification=json.loads((folder/f'{mode}-verification.json').read_text())
    assert verification['passed'] and verification['full_decode']=='passed'
    video=folder/('EP01.mp4' if production else 'preview.mp4')
    assert digest(video)==verification['video_sha256']
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]))
    v=next(x for x in probe['streams'] if x['codec_type']=='video')
    a=next(x for x in probe['streams'] if x['codec_type']=='audio')
    assert (v['width'],v['height'],v['codec_name'],v['r_frame_rate'],int(v['nb_frames']),a['codec_name'])==(1080,1920,'h264','30/1',3000,'aac')
    assert abs(float(v['duration'])-100)<.05

    frames=sorted((folder/('frames' if production else 'preview')).glob('*.jpg'))
    assert len(frames)==(3000 if production else 1500)
    assert all(p.read_bytes().endswith(b'\xff\xd9') for p in frames)
    report=dict(passed=True,mode=mode,archived_scripts='hashes matched',source_scene='hash matched',cad='1428 positive-volume valid source records and meshes present; reused prior CAD validation, not regenerated',preservation='baseline hashes and entire queue unchanged',caption_count=len(blocks),maximum_caption_characters=max(captions),spoken_seconds=audio['spoken_seconds'],continuity_pairs=len(audit['continuity']),maximum_camera_step=max(x['camera_step'] for x in audit['continuity']),maximum_part_translation_step=max(x['part_step'] for x in audit['continuity']),gear_pairs=len(gears),target_feed_m_s=-speed,large_gear_tooth_cycles_hz=kinematics['large_gear_tooth_cycles_hz'],preview_sample_fps=kinematics['preview_sample_fps'],maximum_contact_speed_error_m_s=contact_error,maximum_marker_speed_error_m_s=marker_error,maximum_shaft_angular_error_rad_s=shaft_error,visual_acceptance='pending user review')
    (folder/f'{mode}-independent-verification.json').write_text(json.dumps(report,indent=2))
    return report

def sheets(folder):
    frames=sorted((folder/'preview').glob('*.jpg')); out=folder/'review-sheets'; out.mkdir(exist_ok=True)
    for k in range(0,len(frames),100):
        sheet=Image.new('RGB',(1350,2600),'#18202a'); draw=ImageDraw.Draw(sheet)
        for j,p in enumerate(frames[k:k+100]):
            with Image.open(p) as im: sheet.paste(im.resize((135,240)),((j%10)*135,(j//10)*260))
            draw.text(((j%10)*135+2,(j//10)*260+241),f'{(int(p.stem)-1)/30:.2f}s',fill='white')
        sheet.save(out/f'{k//100:02}.jpg',quality=92)
    return str(out)
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('folder',type=Path); p.add_argument('--production',action='store_true'); p.add_argument('--sheets',action='store_true'); a=p.parse_args()
    print(json.dumps(verify(a.folder,a.production),indent=2))
    if a.sheets: print(sheets(a.folder))
