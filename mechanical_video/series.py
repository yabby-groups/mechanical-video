"""Resumable, provenance-first documentary production. Run with --help."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

from .series_content import TITLES, OUTLINES, SCRIPTS, lines
from .voiceover import prepare, duration, stamp
from .runtime import exclusive_lock

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'series/3d-printer'
COMMIT = '7b32e405f0719881cca782500c822e01e3b16bf2'
RAW = f'https://raw.githubusercontent.com/VoronDesign/Voron-2/{COMMIT}/'

def read(path):
    return json.loads(Path(path).read_text())

def write(path, data):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2)); temp.replace(path)

def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def run(args, **kwargs):
    subprocess.run([str(x) for x in args], check=True, **kwargs)

def download(relative, target):
    """Keep partial transfers; validate zip/PDF before publishing as an asset."""
    import requests
    target=Path(target); target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if target.suffix=='.zip' and not zipfile.is_zipfile(target):
            target.replace(target.with_suffix('.zip.partial'))
        elif target.suffix=='.pdf' and not target.read_bytes().rstrip().endswith(b'%%EOF'):
            target.replace(target.with_suffix('.pdf.partial'))
        else: return
    partial=target.with_suffix(target.suffix+'.partial')
    offset=partial.stat().st_size if partial.exists() else 0
    while True:
        response=requests.get(RAW+relative,headers={'Range':f'bytes={offset}-{offset+1048575}'},timeout=(30,60))
        response.raise_for_status()
        if response.status_code==206:
            content_range=response.headers['Content-Range']
            actual_start=int(content_range.split()[1].split('-')[0])
            total=int(content_range.split('/')[-1])
            if actual_start!=offset: raise ValueError('Unexpected HTTP range offset; partial file preserved')
            with partial.open('ab') as out: out.write(response.content)
            offset+=len(response.content)
            print('Downloaded',relative,offset,'/',total,flush=True)
            if offset==total: break
        else:
            partial.write_bytes(response.content); break
    if target.suffix=='.zip' and not zipfile.is_zipfile(partial): raise ValueError('Incomplete CAD archive')
    if target.suffix=='.pdf' and not partial.read_bytes().rstrip().endswith(b'%%EOF'): raise ValueError('Incomplete PDF')
    tree_path=BASE/'knowledge_base/upstream-tree.json'
    if tree_path.exists():
        entry=next((e for e in read(tree_path)['tree'] if e['path']==relative),None)
        if entry:
            blob=partial.read_bytes()
            blob_sha=hashlib.sha1(f'blob {len(blob)}\0'.encode()+blob).hexdigest()
            if blob_sha!=entry['sha']: raise ValueError('Source Git blob hash mismatch; partial retained for diagnosis')
    partial.replace(target)

def init():
    for folder in ['knowledge_base','master_assembly/source','episodes','renders','output']:
        (BASE/folder).mkdir(parents=True,exist_ok=True)
    target=BASE/'series.json'
    if not target.exists():
        write(target,dict(name='拆解一台 3D 打印机',slug='3d-printer',season=1,
            product='Voron 2.4r2',cad_commit=COMMIT,completed_episodes=[],next_episode=1,
            explained_topics=[],used_shots=[],voice={'model':'qwen3-tts-flash','voice':'Ethan'},
            model_version=None,outputs={},format={'width':1080,'height':1920,'fps':30,'video':'h264','audio':'aac'},
            style='dark industrial / graphite / orange / cyan',music='Original procedural ambient, generated locally; no third-party samples'))
    return target

def plan():
    init()
    for number,title in enumerate(TITLES,1):
        folder=BASE/f'episodes/EP{number:02}'; folder.mkdir(exist_ok=True)
        target=folder/'episode.json'
        if not target.exists():
            write(target,dict(number=number,title=title,state='planned',master_commit=COMMIT,
                editorial_ready=number in SCRIPTS,minimum_duration=90,source='knowledge_base/Assembly_Manual_2.4r2.pdf'))
        episode=read(target)
        if episode.get('editorial_ready')!=(number in SCRIPTS):
            episode['editorial_ready']=number in SCRIPTS; write(target,episode)
        if 'knowledge_points' not in episode:
            episode.update(knowledge_points=OUTLINES[number-1],target_duration=[90,180],
                shot_plan=['整机定位','真实零件拆解','因果关系与运动示意','结构复位及下一集问题'],
                source_policy='Pinned official STEP and manual; label supplementary internal diagrams as schematic')
            write(target,episode)
        if number in SCRIPTS and not (folder/'script.md').exists():
            (folder/'script.md').write_text('\n'.join(lines(number))+'\n')
    write(BASE/'knowledge_base/editorial.json',dict(
        references=[{'url':RAW+'Manual/Assembly_Manual_2.4r2.pdf','scope':'Assembly, belt routing, frame, Z drives'},
        {'url':'https://vorondesign.com/voron2.4','scope':'Official configurator/BOM; configuration-dependent, not a universal purchased-parts list'},
        {'url':'https://www.klipper3d.org/Kinematics.html#corexy-robots','scope':'CoreXY sum/difference kinematics'},
        {'url':'https://www.klipper3d.org/Config_Reference.html#quad_gantry_level','scope':'Four-motor gantry levelling'}],
        corrections=['EP05 explains belts and rails; V2.4 Z is belt driven, not leadscrew driven.',
        'Toolhead content must follow the pinned STEP, not silently substitute current Stealthburner.',
        'Exploded placements and operation paths are educational animation, not a physical simulation.'],
        cad_brief='Import the official millimetre STEP without remodeling hidden structure. Retain named assembly hierarchy, occurrence transforms, local independent solids and source hashes. Unknown materials remain unknown. Color is display metadata, not a material certificate.'))

def group(name):
    rules=[('panels',['panel','door','skirt','deck','enclosure']),
        ('toolhead',['hotend','afterburner','extruder','toolhead','nozzle','clockwork','cw2','fan_duct']),
        ('z_drive',['z_drive','z_motor','z_idler','z_belt']),
        ('bed',['bed','heater','build_plate']),('motors',['motor','stepper','nema']),
        ('motion',['rail','mgn','belt','pulley','idler']),
        ('gantry',['gantry','x_axis','x-axis','y_axis','xy_joint','x_carriage','x_rail']),
        ('frame',['frame','extrusion','2020','horizontal','vertical'])]
    for n in reversed(name.lower().split('/')):
        for label,terms in rules:
            if any(t in n for t in terms): return label
    return 'other'

def assets():
    init()
    source=BASE/'master_assembly/source'; kb=BASE/'knowledge_base'
    for relative,target in [('CAD/Voron_2.4r2_Assembly_STEP.zip',source/'assembly.zip'),
        ('Manual/Assembly_Manual_2.4r2.pdf',kb/'Assembly_Manual_2.4r2.pdf'),('LICENSE',kb/'LICENSE'),('README.md',kb/'upstream-README.md')]:
        download(relative,target)
    import requests
    for name in ['bom_2.4.js','configurator_2.4.js']:
        target=kb/('official-'+name)
        if not target.exists():
            response=requests.get('https://vorondesign.com/js/'+name,timeout=30); response.raise_for_status()
            target.write_text(response.text)
    tables=json.loads(subprocess.check_output(['node','-e',
        "const fs=require('fs'),vm=require('vm');let s={};vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),s,{timeout:1000});process.stdout.write(JSON.stringify({bom:s.bom,upgrade_bom:s.upgrade_bom,upgrade_bom_24:s.upgrade_bom_24}));",
        str(kb/'official-bom_2.4.js')]))
    write(kb/'official-bom.json',dict(source='https://vorondesign.com/voron2.4',
        snapshot_date='2026-10-27',tables=tables,
        scope='Official base/upgrade BOM tables; size- and option-dependent adjustments are in the retained configurator script. Not asserted to be the exact STEP purchasing list.'))
    archive=source/'assembly.zip'
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            if member.filename.lower().endswith(('.step','.stp')):
                target=source/Path(member.filename).name
                if not target.exists():
                    with z.open(member) as src,target.open('wb') as dst: shutil.copyfileobj(src,dst)
    files=[dict(path=str(p.relative_to(BASE)),sha256=digest(p),bytes=p.stat().st_size,
        source=RAW+('CAD/Voron_2.4r2_Assembly_STEP.zip' if p.parent==source else 'Manual/'+p.name if p.suffix=='.pdf' else p.name))
        for p in [archive,kb/'Assembly_Manual_2.4r2.pdf',kb/'LICENSE',kb/'upstream-README.md']]
    files.extend(dict(path=str(p.relative_to(BASE)),sha256=digest(p),bytes=p.stat().st_size,
        source='https://vorondesign.com/js/'+p.name.removeprefix('official-'),snapshot_date='2026-10-27')
        for p in [kb/'official-bom_2.4.js',kb/'official-configurator_2.4.js'])
    write(BASE/'asset_manifest.json',dict(commit=COMMIT,license='GPL-3.0 as supplied in upstream LICENSE',
        attribution='Voron Design contributors',assets=files,material_policy='Unspecified unless documented; render colors do not establish composition'))
    return next(source.glob('*.step'),None) or next(source.glob('*.stp'))

def native_cad_acceptance(display_manifest):
    """Verify independently reimported native CAD sidecars without changing display assets."""
    folder=BASE/'master_assembly'
    path=folder/'cad-roundtrip-validation.json'
    if not path.exists():
        run([sys.executable,ROOT/'scripts/canonical_printer_brep.py'])
        run([sys.executable,ROOT/'scripts/validate_printer_parts.py','--canonical'])
    report=read(path)
    if not report.get('passed'): raise ValueError('Native CAD round-trip validation failed')
    if report['display_manifest_sha256']!=digest(display_manifest):
        raise ValueError('Native CAD mapping belongs to a different display model')
    if report['cad_manifest_sha256']!=digest(folder/'cad_assembly.json'):
        raise ValueError('Native CAD assembly manifest changed after validation')
    for item in report['results']:
        if digest(folder/item['step'])!=item['sha256']:
            raise ValueError('Native CAD part changed after validation: '+item['step'])
    return dict(passed=True,manifest='cad_assembly.json',manifest_sha256=report['cad_manifest_sha256'],
        independent_files=report['unique_step_files'],occurrences=report['total_occurrences'],
        disk_roundtrip_report='cad-roundtrip-validation.json',
        limitations='Three native BRep sidecars avoid defective STEP serialization. Display STL is unchanged and not manufacturing CAD.')


def model():
    try:
        result=_build_model()
        geometry=geometry_inventory(result)
        native=native_cad_acceptance(result)
        write(BASE/'master_assembly/validation.json',dict(passed=True,model_sha256=digest(result),
            geometry_sha256=geometry,source='official STEP',independent_solids=True,native_cad=native,
            scope='Display assets fixed; independent reusable CAD validated through cad_assembly.json'))
        return result
    except Exception as exc:
        diagnostic=BASE/'master_assembly/invalid-source.json'
        write(BASE/'master_assembly/validation.json',dict(passed=False,stage='CAD import/independent solid validation',
            error=type(exc).__name__+': '+str(exc),diagnostic=read(diagnostic) if diagnostic.exists() else None,
            source_preserved=True,substitute_model_used=False))
        raise

def geometry_inventory(manifest):
    """Check shared geometry bytes, not only paths in a model manifest."""
    data=read(manifest); names=sorted({p[k] for p in data['parts'] for k in ['step','mesh']})
    files={name:digest(manifest.parent/name) for name in names}
    inventory=dict(model_sha256=digest(manifest),files=files)
    target=manifest.parent/'geometry-assets.json'
    if target.exists() and read(target)!=inventory:
        raise ValueError('Shared model geometry assets changed; existing asset inventory preserved')
    if not target.exists(): write(target,inventory)
    return hashlib.sha256(json.dumps(inventory,sort_keys=True).encode()).hexdigest()

def _build_model():
    manifest=BASE/'master_assembly/assembly.json'
    if manifest.exists():
        data=read(manifest)
        if data['commit']!=COMMIT: raise ValueError('Pinned model changed; use a new series version')
        return manifest
    source_folder=BASE/'master_assembly/source'
    sources=list(source_folder.glob('*.step'))+list(source_folder.glob('*.stp'))
    if sources:
        source=sources[0]
    elif (source_folder/'assembly.zip').exists() and zipfile.is_zipfile(source_folder/'assembly.zip'):
        with zipfile.ZipFile(source_folder/'assembly.zip') as archive:
            member=next(m for m in archive.infolist() if m.filename.lower().endswith(('.step','.stp')))
            source=source_folder/Path(member.filename).name
            with archive.open(member) as src,source.open('wb') as dst: shutil.copyfileobj(src,dst)
    else:
        source=assets()
    from build123d import import_step, Location, export_stl, export_step
    print('Importing official STEP',flush=True)
    assembly=import_step(source)
    folder=manifest.parent; meshes=folder/'parts'; meshes.mkdir(exist_ok=True)
    parts=[]; nodes=[]; cache={}
    def visit(shape,parent_world,path):
        current=path+'/'+(shape.label or 'unnamed')
        world=parent_world*shape.location
        node=dict(id=f'n{len(nodes):05}',path=current,parent=path,local_position=list(shape.position),local_orientation=list(shape.orientation))
        nodes.append(node)
        if shape.children:
            for child in shape.children: visit(child,world,current)
            return
        # Construct a detached TopoDS occurrence without deepcopying anytree's
        # entire 2,000-part parent graph for every leaf.
        local=type(shape)(shape.wrapped.Located(Location().wrapped))
        local.label=shape.label
        # Export each occurrence independently. A temporary TShape wrapper's
        # integer hash is not a geometry identity: collisions/reused wrappers
        # must never replace a beam (or panel) with another leaf's geometry.
        key=node['id']
        if key not in cache:
            mesh_id=f'm{len(cache):05}'
            solids=local.solids()
            valid=bool(solids) and all(s.is_valid and s.volume>0 for s in solids)
            repair=None
            approximation=[]
            if not valid:
                before_volume=local.volume
                print('Healing source topology:',current,'solids:',len(solids),'volume:',before_volume,flush=True)
                repaired=local.fix()
                solids=repaired.solids()
                valid=bool(solids) and all(s.is_valid and s.volume>0 for s in solids)
                if not valid:
                    # Some upstream planar STEP faces carry inconsistent 2-D
                    # edge curves. Rebuild only those faces from the original
                    # 3-D wires, preserving outward normals and inner loops.
                    from build123d import Compound, Face, GeomType
                    from OCP.BRepCheck import BRepCheck_Analyzer
                    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
                    from OCP.BRepTools import BRepTools_ReShape
                    analyzer=BRepCheck_Analyzer(local.wrapped); replacement=BRepTools_ReShape()
                    count=0
                    for face in local.faces():
                        if analyzer.IsValid(face.wrapped) or face.geom_type!=GeomType.PLANE: continue
                        outer=face.outer_wire(); builder=BRepBuilderAPI_MakeFace(outer.wrapped,True)
                        for wire in face.wires():
                            if not wire.wrapped.IsSame(outer.wrapped): builder.Add(wire.wrapped)
                        new_face=builder.Face()
                        if face.normal_at().dot(Face(new_face).normal_at())<0: new_face.Reverse()
                        replacement.Replace(face.wrapped,new_face); count+=1
                    if count:
                        repaired=Compound.cast(replacement.Apply(local.wrapped)); repaired.label=local.label
                        solids=repaired.solids()
                        valid=bool(solids) and all(s.is_valid and s.volume>0 for s in solids)
                        repair=f'Rebuilt {count} invalid planar faces from original 3-D boundary wires with outward normals preserved'
                if not valid:
                    from .series_geometry import faceted_solid
                    from build123d import Compound
                    replacements=[]
                    export_step(local,meshes/'invalid-source.step')
                    write(folder/'invalid-source.json',dict(path=current,source_sha256=digest(source),
                        volume_mm3=before_volume,valid=False,stage='source-derived faceted fallback'))
                    for solid in repaired.solids():
                        if solid.is_valid and solid.volume>0: replacements.append(solid)
                        else:
                            replacement,evidence=faceted_solid(solid)
                            replacements.append(replacement); approximation.append(evidence)
                    repaired=Compound(children=replacements); repaired.label=local.label
                    solids=repaired.solids()
                    valid=bool(solids) and all(s.is_valid and s.volume>0 for s in solids)
                    repair='Invalid vendor solid replaced by an independently validated faceted BRep derived only from original CAD tessellation'
                volume_tolerance=.01 if approximation else 1e-5
                if valid and abs(repaired.volume-before_volume)<=max(.01,abs(before_volume)*volume_tolerance):
                    local=repaired
                    repair=(repair or 'OpenCascade ShapeFix topology repair')+f'; volume difference bounded by {volume_tolerance} relative tolerance'
                else:
                    export_step(local,meshes/'invalid-source.step')
                    write(folder/'invalid-source.json',dict(path=current,source_sha256=digest(source),
                        volume_mm3=before_volume,solid_count=len(solids),valid=False,
                        explanation='Preserved diagnostic geometry; never substituted into a validated master assembly'))
                    raise ValueError(f'Official CAD leaf failed geometric validation after ShapeFix: {current}; solids={len(solids)}, volume={before_volume}')
            stl=meshes/f'{mesh_id}.stl'; step=meshes/f'{mesh_id}.step'
            export_stl(local,stl,tolerance=.25,angular_tolerance=.25)
            export_step(local,step)
            cache[key]=dict(mesh=f'parts/{stl.name}',step=f'parts/{step.name}',solids=len(solids),volume_mm3=local.volume,valid=True,topology_repair=repair,display_approximation=approximation)
        placement=world.wrapped.Transformation()
        matrix=[[placement.Value(i,j) for j in range(1,5)] for i in range(1,4)]+[[0,0,0,1]]
        parts.append(dict(id=node['id'],name=shape.label,path=current,parent=path,
            group=group(current),matrix_mm=matrix,material='unknown; source CAD color only',
            source=f'{source.name}#{current}',**cache[key]))
        if len(parts)%100==0: print('Exported',len(parts),'occurrences',flush=True)
    visit(assembly,Location(),'')
    import OCP
    data=dict(version='voron-2.4r2-'+COMMIT[:12]+'-display3',geometry_version=3,commit=COMMIT,source_sha256=digest(source),cad_kernel=OCP.__version__,
        geometry_identity_policy='Independent export per source occurrence; no temporary TShape hash deduplication',
        units='mm',parts=parts,hierarchy=nodes,independent_solids=True,
        coordinate_policy='Part-local geometry with full world occurrence matrix; native STEP axes retained',
        material_policy='Unknown; inferred display groups only',
        animation_policy='Exploded views and movement paths are schematic, not simulated machine operation')
    write(manifest,data)
    # The manifest hash is shared by every episode and checked before encoding.
    state=read(init()); state['model_version']=data['version']; state['model_sha256']=digest(manifest)
    state['status']='model_ready'; state.pop('blocking_report',None); write(BASE/'series.json',state)
    write(BASE/'knowledge_base/cad_bom.json',dict(source='STEP occurrence inventory; not a procurement BOM',
        counts={name:sum(p['name']==name for p in parts) for name in sorted({p['name'] for p in parts})}))
    return manifest

def audio(number):
    plan(); folder=BASE/f'episodes/EP{number:02}'; script=folder/'script.md'
    if script.read_text().splitlines()!=lines(number): raise ValueError('Editorial source changed: create a new task version')
    narration=folder/'narration.wav'
    if (folder/'timeline.json').exists() and narration.exists(): return read(folder/'timeline.json')
    text,_,cache,clips=prepare(script,narration)
    cursor=0; chapters=[]; segments=[]
    for i,((clip,length),line) in enumerate(zip(clips,text)):
        gap=.28 if i%7 else .65
        end=cursor+length+gap
        chapters.append(dict(id=i,start=cursor,speech_end=cursor+length,end=end,narration=line,
            shot=f'EP{number:02}-S{i:03}',motion=['overview','panels','gantry','z_drive','toolhead','bed'][min(5,i*6//len(text))]))
        segment=cache/f'{i:03}.wav'
        run(['ffmpeg','-y','-v','error','-i',clip,'-af',f'apad=whole_dur={length+gap:.9f}',
            '-t',str(length+gap),'-ar','48000','-ac','1',segment])
        segments.append(segment); cursor=end
    if cursor<90: raise ValueError(f'Narration only {cursor:.1f}s; expand editorial content rather than slow/repeat footage')
    seconds=math.ceil(cursor*30)/30
    listing=cache/'concat.txt'; listing.write_text(''.join(f"file '{p.name}'\n" for p in segments))
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','1','-i',listing,'-af',f'apad=whole_dur={seconds}',
        '-t',str(seconds),'-c:a','pcm_s16le',narration])
    (folder/'subtitles.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(c["start"])} --> {stamp(c["speech_end"])}\n{c["narration"]}' for i,c in enumerate(chapters))+'\n')
    timeline=dict(seconds=seconds,spoken_seconds=sum(d for _,d in clips),chapters=chapters,
        voice={'model':'qwen3-tts-flash','voice':'Ethan'},fps=30,script_sha256=digest(script))
    write(folder/'timeline.json',timeline); write(folder/'storyboard.json',timeline)
    return timeline

def validate(path,folder,manifest):
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    sound=next(s for s in probe['streams'] if s['codec_type']=='audio')
    timeline=read(folder/'timeline.json'); seconds=float(probe['format']['duration'])
    assert seconds>=90 and abs(seconds-timeline['seconds'])<.15
    assert (video['width'],video['height'],video['r_frame_rate'],video['codec_name'])==(1080,1920,'30/1','h264')
    assert sound['codec_name']=='aac'
    previous=0
    for c in timeline['chapters']:
        assert c['start']>=previous and c['start']<c['speech_end']<=c['end']<=seconds+.02
        assert 0<len(c['narration'])<=20 and '\n' not in c['narration']
        previous=c['speech_end']
    motion=read(folder/'motion_audit.json')
    assert motion['moving_parts']>0 and motion['source_model_sha256']==digest(manifest)
    native=read(folder/'native-validation.json')
    assert native['passed'] and native['source_model_sha256']==digest(manifest)
    run(['ffmpeg','-v','error','-i',path,'-f','null','-'],stdout=subprocess.DEVNULL)
    return dict(passed=True,duration=seconds,width=1080,height=1920,fps=30,video='h264',audio='aac',
        full_decode='passed',subtitle_count=len(timeline['chapters']),subtitle_single_line_max20=True,
        model_sha256=digest(manifest),geometry_sha256=geometry_inventory(manifest),motion_audit=motion,native_scene_audit=native,voice=timeline['voice'],
        limitations=['Motion is illustrative, not dynamic simulation or a verified sliced print.',
            'CAD material identities are unspecified. Visual inspection is recorded separately.'])

def scene_topics(number,timeline):
    plans={
        1:[(0,'整机架构'),(7,'框架与围护'),(11,'固定热床 · 升降龙门'),(19,'四点Z轴皮带提升'),(23,'CoreXY水平运动'),(28,'供料 · 加热 · 成形'),(35,'运动与控制协作'),(43,'同一套基础装配')],
        2:[(0,'框架与外壳'),(4,'移开围护面板'),(8,'方正度与导轨基准'),(14,'连接件与载荷传递'),(24,'围护与工作环境'),(35,'检修 · 走线 · 间隙'),(43,'骨架与围护复位')],
        3:[(0,'CoreXY运动系统'),(7,'A/B皮带位移的和与差'),(14,'双电机协调定位'),(20,'导轨约束 · 皮带传力'),(26,'四点Z轴提升与调平'),(38,'逐层沉积的运动顺序')],
    }
    if number in plans: sections=plans[number]
    else:
        count=len(timeline['chapters'])
        sections=[(0,TITLES[number-1]),(7,OUTLINES[number-1][0]),(18,OUTLINES[number-1][1]),(28,OUTLINES[number-1][2]),(count-4,'各系统的协作关系')]
    chapters=timeline['chapters']; result=[]
    for i,(index,title) in enumerate(sections):
        following=sections[i+1][0] if i+1<len(sections) else len(chapters)
        result.append(dict(title=title,start=chapters[index]['start'],end=chapters[following]['start'] if following<len(chapters) else timeline['seconds']))
    return result

def render(number,preview_only=False):
    plan(); folder=BASE/f'episodes/EP{number:02}'; output=BASE/f'output/EP{number:02}.mp4'
    if number not in range(1,13): raise ValueError('Episode must be 1..12')
    if output.exists():
        if (folder/'validation.json').exists() and read(folder/'validation.json').get('passed'):
            expected=read(folder/'validation.json').get('video_sha256')
            if expected!=digest(output): raise ValueError('Completed output hash changed; preserved for inspection')
            print('Already complete, preserved:',output); return
        raise ValueError('Existing unverified output preserved; inspect before retry')
    episode=read(folder/'episode.json')
    with exclusive_lock(BASE/'production.lock'):
        try:
            episode['state']='audio'; write(folder/'episode.json',episode)
            timeline=audio(number)
            episode['state']='model'; write(folder/'episode.json',episode)
            manifest=model(); model_hash=digest(manifest)
            episode.update(model_sha256=model_hash,model_version=read(manifest)['version'])
            write(folder/'episode.json',episode)
            sources=[Path(__file__).with_name(n) for n in ['series.py','series_scene.py','series_content.py','series_geometry.py','series_audit.py','series_season.py','series_diagrams.py']]
            identity=dict(model=model_hash,timeline=digest(folder/'timeline.json'),sources={p.name:digest(p) for p in sources})
            task=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:20]
            render_folder=BASE/f'renders/EP{number:02}'/task
            archive=render_folder/'renderer'; archive.mkdir(parents=True,exist_ok=True)
            episode['render_task']=str(render_folder.relative_to(BASE)); write(folder/'episode.json',episode)
            for name in ['series.py','series_scene.py','series_content.py','series_geometry.py','series_audit.py','series_season.py','series_diagrams.py']:
                source=Path(__file__).with_name(name); target=archive/name
                if target.exists() and digest(target)!=digest(source): raise ValueError('Archived production source changed; create a new version')
                if not target.exists(): shutil.copy2(source,target)
            write(archive/'fingerprints.json',{p.name:digest(p) for p in archive.glob('*.py')})
            job=dict(episode=number,title=TITLES[number-1],manifest=str(manifest),model_sha256=model_hash,folder=str(render_folder),timeline=timeline,scenes=scene_topics(number,timeline))
            write(render_folder/'job.json',job); write(folder/'job.json',job)
            storyboard=dict(timeline,scenes=job['scenes'],model_sha256=model_hash,
                master_assembly=str(manifest.relative_to(BASE)),renderer=str((archive/'series_scene.py').relative_to(BASE)))
            storyboard['chapters']=[dict({k:v for k,v in c.items() if k!='motion'},scene=next(s['title'] for s in job['scenes'] if s['start']<=c['start']<s['end'])) for c in timeline['chapters']]
            write(folder/'storyboard.json',storyboard)
            blender=os.getenv('BLENDER_BIN') or '/Applications/Blender.app/Contents/MacOS/Blender'
            from .runtime import require_metal_device
            require_metal_device()
            with exclusive_lock(ROOT/'artifacts/render.lock',blocking=True):
                for mode in (['preview'] if preview_only else ['preview','production']):
                    episode['state']=mode; write(folder/'episode.json',episode)
                    with (render_folder/'blender.log').open('a') as log:
                        run([blender,'-b','--python-exit-code','1','-t','4','--python',archive/'series_scene.py','--',render_folder/'job.json',mode],stdout=log,stderr=subprocess.STDOUT)
                if not preview_only:
                    with (render_folder/'blender.log').open('a') as log:
                        run([blender,'-b','--python-exit-code','1','-t','4','--python',archive/'series_audit.py','--',render_folder/'job.json'],stdout=log,stderr=subprocess.STDOUT)
            if preview_only:
                episode['state']='preview_ready'; episode.pop('error',None)
                write(folder/'episode.json',episode)
                print('PREVIEW',render_folder/'preview',flush=True)
                return
            if digest(manifest)!=model_hash: raise ValueError('Shared model changed during render')
            shutil.copy2(render_folder/'motion_audit.json',folder/'motion_audit.json')
            shutil.copy2(render_folder/'native-validation.json',folder/'native-validation.json')
            episode['state']='composition'; write(folder/'episode.json',episode)
            compose(folder,timeline,render_folder)
            report=validate(folder/'encoding.mp4',folder,manifest)
            report['video_sha256']=digest(folder/'encoding.mp4')
            write(folder/'validation.json',report)
            shutil.copy2(folder/'encoding.mp4',folder/'final.mp4')
            shutil.copy2(folder/'final.mp4',output)
            (folder/'encoding.mp4').unlink()
            state=read(BASE/'series.json')
            state['completed_episodes']=sorted(set(state['completed_episodes']+[number]))
            state['next_episode']=next((n for n in range(1,13) if n not in state['completed_episodes']),None)
            state['explained_topics']=[point for n in state['completed_episodes'] for point in OUTLINES[n-1]]
            state['used_shots']+= [c['shot'] for c in timeline['chapters']]
            state['outputs'][f'EP{number:02}']=str(output.relative_to(ROOT)); state['status']='ready'
            write(BASE/'series.json',state)
            episode['state']='complete'; episode.pop('error',None)
            recovered={key:episode.pop(key) for key in ('failed_stage','blocked_by') if key in episode}
            if recovered: episode.setdefault('recovery_history',[]).append(recovered)
            write(folder/'episode.json',episode)
            print('COMPLETE',output,flush=True)
        except Exception as exc:
            episode.update(state='failed',failed_stage=episode['state'],error=type(exc).__name__+': '+str(exc),updated=time.time())
            write(folder/'episode.json',episode)
            write(folder/'validation.json',dict(passed=False,stage=episode['failed_stage'],error=episode['error'],
                final_video_exists=output.exists(),master_validation='../../master_assembly/validation.json'))
            raise

def compose(folder,timeline,render_folder=None):
    from .film_audio import ass_stamp
    ass='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,PingFang SC,44,&H00FFFFFF,&H00FFFFFF,&H00101822,&H90000000,0,0,0,0,100,100,0,0,1,3,1,2,40,40,200,1
Style: Label,PingFang SC,28,&H00E6CC99,&H00FFFFFF,&H00101822,&H90000000,0,0,0,0,100,100,0,0,1,2,0,8,45,45,170,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    for c in timeline['chapters']:
        ass+=f'Dialogue: 0,{ass_stamp(c["start"])},{ass_stamp(c["speech_end"])},Default,,0,0,0,,{c["narration"]}\n'
    ass+=f'Dialogue: 1,0:00:00.00,{ass_stamp(timeline["seconds"])},Label,,0,0,0,,官方2.4r2 CAD · 拆解位移及轨迹为示意\n'
    (folder/'captions.ass').write_text(ass)
    # Original quiet ambient bed: no external copyrighted music and no repeated video.
    music=folder/'music.wav'; seconds=timeline['seconds']
    if not music.exists():
        run(['ffmpeg','-y','-v','error','-f','lavfi','-i',
            f'aevalsrc=0.025*(sin(2*PI*110*t)+0.5*sin(2*PI*164.8138*t)+0.3*sin(2*PI*220*t))*(0.7+0.3*sin(2*PI*0.08*t)):s=48000:d={seconds}',
            '-af',f'afade=t=in:d=3,afade=t=out:st={seconds-4}:d=4',music])
    run(['ffmpeg','-y','-v','error','-framerate','30','-start_number','1','-i',(render_folder or folder)/'frames/%06d.jpg',
        '-i',folder/'narration.wav','-i',music,'-filter_complex',
        '[0:v]ass=captions.ass:fontsdir=/System/Library/Fonts[v];[1:a]loudnorm=I=-16:TP=-1.5:LRA=9[voice];[2:a]volume=0.18[bg];[voice][bg]amix=inputs=2:duration=first:normalize=0[a]',
        '-map','[v]','-map','[a]','-c:v','libx264','-threads','4','-preset','fast','-crf','19','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k','-ar','48000','-t',str(seconds),'-movflags','+faststart',folder/'encoding.mp4'],cwd=folder)
    run(['ffmpeg','-y','-v','error','-ss','2','-i',folder/'encoding.mp4','-frames:v','1',folder/'thumbnail.png'])

def main(argv=None):
    # Current episode production: scripts/production_gate.py; docs/production-preflight.md.
    # Historical holds below remain authoritative; this reference grants no continuation.
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('init'); s.add_argument('--name',choices=['3d-printer'],default='3d-printer')
    s=sub.add_parser('plan'); s.add_argument('--season',type=int,choices=[1],default=1)
    s=sub.add_parser('render'); s.add_argument('--preview-only',action='store_true'); g=s.add_mutually_exclusive_group(required=True); g.add_argument('--episode',type=int); g.add_argument('--episodes')
    s=sub.add_parser('continue'); s.add_argument('--count',type=int,default=1)
    sub.add_parser('status'); sub.add_parser('assets'); sub.add_parser('model')
    s=sub.add_parser('audio'); s.add_argument('--episode',type=int,required=True)
    a=p.parse_args(argv)
    if a.command=='init': print(init())
    elif a.command=='plan': plan()
    elif a.command=='assets': print(assets())
    elif a.command=='model': print(model())
    elif a.command=='audio': print(audio(a.episode)['seconds'])
    elif a.command=='status':
        plan(); print(json.dumps(read(BASE/'series.json'),ensure_ascii=False,indent=2))
        for path in sorted((BASE/'episodes').glob('*/episode.json')):
            data=read(path); print(path.parent.name,data['state'],data.get('error',''))
    else:
        plan()
        if a.command=='continue':
            if a.count<1: p.error('--count must be positive')
            complete=read(BASE/'series.json')['completed_episodes']
            numbers=[n for n in range(1,13) if n not in complete][:a.count]
        elif a.episode is not None: numbers=[a.episode]
        else:
            if '-' in a.episodes:
                start,end=map(int,a.episodes.split('-')); numbers=list(range(start,end+1))
            else: numbers=[int(n) for n in a.episodes.split(',')]
        if not numbers or any(n not in range(1,13) for n in numbers): p.error('Select episodes 1..12')
        for number in numbers: render(number,getattr(a,'preview_only',False))

if __name__=='__main__': main()
