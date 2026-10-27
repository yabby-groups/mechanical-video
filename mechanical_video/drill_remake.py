"""Re-edit preserved drill shots around measured, short Ethan narration clips."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from .voiceover import prepare
from .film_audio import caption_lines, compose
from .runtime import exclusive_lock

SECTIONS = [
    ('动力从哪里来', 0, ['一把电钻，怎样把电变成力量？','关键不只在电机。','我们沿着动力传递的方向拆开看。','从电池出发，最后到达钻头。','内部用通用结构解释原理。','具体布局和尺寸属于推测。']),
    ('先断开供电', 1, ['先取下电池，断开动力来源。','这样才能继续拆开外壳。','电池与机身之间的触点，','负责把电能送进电钻。']),
    ('电池提供能量', 7, ['电池包为什么装有多节电芯？','串联可以提高供电电压。','电压和可输出电流，','共同影响电机能得到的功率。','保护电路监测异常状态，','必要时切断供电。','这里的电芯数量只是示意。']),
    ('打开动力通路', 2, ['电流接下来流向哪里？','打开机壳，就能看见控制区域。','外壳不仅方便握持，','也把电机和传动机构固定在一起。']),
    ('开关与控制', 6, ['按下扳机，并非直接推动钻头。','它先向控制电路发出指令。','控制电路调节送给电机的电能，','因此可以改变旋转速度。','换向开关改变旋转方向，','让钻进和退出都能完成。']),
    ('电机产生旋转', 5, ['电机为什么会转起来？','通电后的磁场相互作用，','在转子上形成旋转力矩。','转子带动电机轴转动，','把电能转成机械运动。','但电机转得快，','还不等于钻头有足够的拧紧力量。']),
    ('减速与增扭', 4, ['所以，中间还需要减速机构。','这里用行星齿轮来解释。','中心齿轮推动周围的行星轮。','外侧齿圈约束它们的运动。','行星架把运动传向输出端。','输出转速降低时，','在功率损耗之外，扭矩可以增大。','这就是用速度换取拧转能力。','多级传动可以进一步降低转速。']),
    ('主轴与夹头输出', 3, ['减速后的力量怎样交给钻头？','输出主轴把扭矩传到夹头。','轴承支撑主轴，帮助稳定旋转。','转动夹头外套，','夹爪便能夹紧钻头的柄部。','夹得牢，动力才能可靠传出去。','调节环则用于设定拧紧力矩。','达到设定值时，离合机构打滑，','有助于减少螺钉被过度拧紧。']),
    ('串起整条动力链', 8, ['现在，把这条动力链串起来。','电池供电，控制电路调节，','电机旋转，齿轮减速增扭，','最后由主轴和夹头带动钻头。','每一层都在解决不同的问题。','看懂它们怎样配合，','就能理解电钻为何既能快转，','又能在需要时输出更大的扭矩。']),
]

def main():
    root=Path(__file__).resolve().parents[1]
    sources=[Path(__file__),root/'mechanical_video/voiceover.py',root/'mechanical_video/film_audio.py']
    identity={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:16]
    folder=root/'artifacts/films'/f'cordless-drill-principles-ethan-{key}'
    folder.mkdir(parents=True,exist_ok=True)
    archive=folder/'production'; archive.mkdir(exist_ok=True)
    for p in sources:
        target=archive/p.name
        if target.exists() and target.read_bytes()!=p.read_bytes(): raise ValueError('Archive changed')
        if not target.exists(): shutil.copy2(p,target)
    (archive/'fingerprints.json').write_text(json.dumps(identity,indent=2))
    script=folder/'narration.zh.txt'
    lines=[line for _,_,group in SECTIONS for line in group]
    for line in lines: caption_lines(line)
    script.write_text('\n'.join(lines)+'\n')
    _,_,cache,clips=prepare(script,folder/'film.mp4',model='qwen3-tts-flash',voice='Ethan')
    spoken=sum(length for _,length in clips)
    if spoken<80: raise ValueError('Expand narration instead of padding to 90 seconds')
    old=root/'artifacts/films/cordless-drill-90s/storyboard.json'
    previous=json.loads(old.read_text())
    video=root/'artifacts/videos/b87d83ab5937e6b36b8b/video.mp4'
    story={'voice':'Ethan','model':'qwen3-tts-flash','speech_cache':str(cache),'spoken_seconds':spoken,'chapters':[], 'shots':[], 'source_video':str(video)}
    cursor=0.; index=0
    for title,source,group in SECTIONS:
        start=cursor
        for line in group:
            length=clips[index][1]
            story['chapters'].append(dict(start=cursor,speech_end=cursor+length,end=cursor+length+.25,narration=line,title=title,source_chapter=source))
            cursor+=length+.25; index+=1
        c=previous['chapters'][source]
        story['shots'].append(dict(title=title,start=start,end=cursor,source_start=c['start'],source_end=c['end'],source_chapter=source))
    if cursor<90: raise ValueError('Formal film must last at least 90 seconds')
    story_path=folder/'storyboard.json'; story_path.write_text(json.dumps(story,ensure_ascii=False,indent=2))
    output=folder/'cordless-drill-principles-ethan.mp4'
    with exclusive_lock(root/'artifacts/render.lock',blocking=True):
        if not output.exists():
            shots=[]
            for i,shot in enumerate(story['shots']):
                target=folder/f'shot-{i:02}.mp4'; shots.append(target)
                length=shot['end']-shot['start']; source_length=shot['source_end']-shot['source_start']
                # Play each archived shot once at normal speed, then hold its exploded
                # structure while the explanation continues. No loop or speech retiming.
                command=['ffmpeg','-y','-v','error','-ss',str(shot['source_start']),'-t',str(source_length),'-i',str(video),'-an','-vf',f'tpad=stop_mode=clone:stop_duration={max(0,length-source_length)+.1},trim=duration={length},setpts=PTS-STARTPTS','-r','30','-c:v','libx264','-threads','4','-preset','fast','-crf','18',str(target)]
                subprocess.run(command,check=True)
            listing=folder/'shots.txt'; listing.write_text(''.join(f"file '{p.name}'\n" for p in shots))
            silent=folder/'picture-edit.mp4'
            subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','1','-i',str(listing),'-c','copy',str(silent)],check=True)
            compose(silent,story_path,output)
        report=json.loads(output.with_suffix('.verification.json').read_text())
        report.update(subtitle_count=len(lines),max_caption_characters=max(map(len,lines)),single_line=True,overlap=False,source_video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),visual_timing='Each source shot once at normal speed, then structure hold; speech unmodified')
        (folder/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(output,flush=True)

if __name__=='__main__': main()
