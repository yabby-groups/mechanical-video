"""Prepare local playback and validate evidence-attested reviews; never infer viewing."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess

MODALITIES = ('video', 'audio', 'captions', 'continuity')
QUESTIONS = ('opening', 'first_cause', 'new_information', 'retellable_answer',
             'like_value', 'save_value', 'follow_reason', 'ending')


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def full_coverage(ranges, duration):
    """Union of explicit intervals must cover the entire exact file, without gaps."""
    if not isinstance(ranges, list) or not ranges:
        return False
    checked = []
    for item in ranges:
        if (not isinstance(item, list) or len(item) != 2 or
                not all(number(x) for x in item) or not 0 <= item[0] < item[1] <= duration):
            return False
        checked.append(item)
    end = 0
    for start, stop in sorted(checked):
        if start > end + 0.001:
            return False
        end = max(end, stop)
    return end >= duration - 0.001


def validate(review, media_hash, duration, producer_ids):
    """Validate attestations, not whether a person actually watched/listened.

    Caller supplies producers from the frozen task, never from reviewer claims.
    Hashes bind local evidence; they do not authenticate reviewer identity.
    """
    missing = []
    if not isinstance(review, dict):
        return {'status': 'NEEDS_REVIEW', 'missing': ['review object'], 'coverage': dict.fromkeys(MODALITIES, False)}
    if review.get('media_sha256') != media_hash:
        missing.append('exact media hash')
    if not number(duration) or duration <= 0 or review.get('duration') != duration:
        missing.append('exact media duration')
    reviewer = review.get('reviewer', {})
    if not isinstance(reviewer, dict):
        reviewer = {}
    identity = reviewer.get('id')
    if (not isinstance(identity, str) or not identity.strip() or not producer_ids or
            not isinstance(producer_ids, list) or identity in producer_ids or reviewer.get('independent') is not True):
        missing.append('independent reviewer and frozen producer IDs')
    if reviewer.get('method') not in ('realtime_av_playback', 'continuous_av_model'):
        missing.append('continuous audiovisual review method')
    if not reviewer.get('tool') or not reviewer.get('completed_at'):
        missing.append('actual review tool and completion time')
    evidence = review.get('evidence', [])
    valid_evidence = {}
    if isinstance(evidence, list):
        for entry in evidence:
            if not isinstance(entry, dict):
                continue
            path = Path(entry.get('path') or '')
            if path.is_file() and entry.get('sha256') == digest(path):
                valid_evidence[str(path)] = True
    if not valid_evidence:
        missing.append('existing hash-bound playback/reviewer evidence')
    coverage = {}
    observations = review.get('coverage', {})
    if not isinstance(observations, dict):
        observations = {}
    for modality in MODALITIES:
        entry = observations.get(modality, {})
        if not isinstance(entry, dict):
            entry = {}
        coverage[modality] = (number(duration) and duration > 0 and
                              full_coverage(entry.get('ranges'), duration) and
                              entry.get('observed') is True and bool(entry.get('notes')) and
                              isinstance(entry.get('evidence'), str) and entry.get('evidence') in valid_evidence)
        if not coverage[modality]:
            missing.append('full ' + modality + ' coverage')
    answers = review.get('answers', {})
    if not isinstance(answers, dict):
        answers = {}
    comprehension_failed = False
    for key in QUESTIONS:
        item = answers.get(key, {})
        if not isinstance(item, dict):
            item = {}
        stamp = item.get('time')
        if (not number(stamp) or not number(duration) or not 0 <= stamp < duration or
                not item.get('observation') or not isinstance(item.get('evidence'), str) or item.get('evidence') not in valid_evidence or
                item.get('verdict') not in ('clear', 'unclear', 'absent')):
            missing.append('timecoded answer: ' + key)
        if key in ('first_cause', 'retellable_answer') and item.get('verdict') in ('unclear', 'absent'):
            comprehension_failed = True
    issues = review.get('issues', [])
    invalid_issues = not isinstance(issues, list)
    critical = False
    if not invalid_issues:
        for item in issues:
            if not isinstance(item, dict):
                invalid_issues = True
                continue
            if item.get('status') not in ('open', 'closed') or item.get('severity') not in ('P0', 'P1', 'P2', 'P3'):
                invalid_issues = True
            if item.get('status') != 'closed' and item.get('severity') in ('P0', 'P1'):
                critical = True
            if not item.get('issue_id') or not item.get('description'):
                invalid_issues = True
    if invalid_issues:
        missing.append('valid issue records')
    status = 'REWORK' if critical or comprehension_failed else ('NEEDS_REVIEW' if missing else 'COMPLETE')
    return {'status': status, 'missing': missing, 'coverage': coverage,
            'critical_issue': critical, 'comprehension_failed': comprehension_failed,
            'scope': 'Evidence-attested review; not authenticated proof of human perception or platform growth.'}


def prepare(video, output, producer_ids):
    video, output = Path(video).resolve(), Path(output).resolve()
    if not producer_ids or not all(isinstance(x, str) and x.strip() for x in producer_ids):
        raise ValueError('Frozen producer identities are required')
    if not video.is_file():
        raise FileNotFoundError(video)
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(video)],
                           check=True, capture_output=True, text=True)
    data = json.loads(probe.stdout)
    duration = float(data['format']['duration'])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Invalid media duration')
    output.mkdir(parents=True, exist_ok=False)
    # Independent copy, no renderer, no hardlink back to protected media.
    shutil.copyfile(video, output / 'media.mp4')
    media_hash = digest(video)
    if digest(output / 'media.mp4') != media_hash:
        raise ValueError('Copied media hash mismatch')
    task = {'media_sha256': media_hash, 'duration': duration, 'source': str(video),
            'producer_ids': producer_ids, 'has_audio': any(x.get('codec_type') == 'audio' for x in data['streams']),
            'status': 'NEEDS_REVIEW', 'formal_acceptance': False}
    (output / 'task.json').write_text(json.dumps(task, indent=2))
    template = {'media_sha256': media_hash, 'duration': duration,
                'reviewer': {'id': None, 'independent': False, 'method': None, 'tool': None, 'completed_at': None},
                'evidence': [], 'coverage': {key: {'observed': False, 'ranges': [], 'notes': None, 'evidence': None} for key in MODALITIES},
                'answers': {key: {'time': None, 'observation': None, 'verdict': None, 'evidence': None} for key in QUESTIONS},
                'issues': []}
    (output / 'review-template.json').write_text(json.dumps(template, indent=2))
    page = '''<!doctype html><meta charset="utf-8"><title>Continuous AV review</title>
<style>body{font:16px system-ui;max-width:1000px;margin:24px auto;background:#20232a;color:white}video{max-height:70vh;width:100%}textarea{width:100%;height:160px}button{padding:10px;margin:8px}</style>
<h1>连续画面与听审</h1><p>待审包，不是通过报告。按正常速度从头观看并听审；拖动、静音、播放事件均不能证明评审者看懂。</p>
<video id="v" src="media.mp4" controls preload="metadata"></video><p id="stamp"></p>
<p>检查：开头是否提出可见问题；首次因果何时清楚；每段新增信息；能否复述；点赞/收藏价值；后续关注理由；结尾是否兑现。</p>
<textarea id="notes" placeholder="记录时间码、具体观察、看不懂的关系及最小修改。导出后由独立评审者填写review-template.json，绑定本日志哈希。"></textarea>
<button id="mark">记录当前时间码</button><button id="save">导出观察日志</button>
<script>
const events=[];const v=document.getElementById('v');
for(const e of ['play','pause','seeking','seeked','ratechange','volumechange','ended'])v.addEventListener(e,()=>events.push({event:e,time:v.currentTime,rate:v.playbackRate,muted:v.muted,volume:v.volume,at:new Date().toISOString()}));
v.addEventListener('timeupdate',()=>document.getElementById('stamp').textContent=v.currentTime.toFixed(3)+' / '+v.duration.toFixed(3)+'秒');
document.getElementById('mark').onclick=()=>document.getElementById('notes').value+=String.fromCharCode(10)+v.currentTime.toFixed(3)+'秒：';
document.getElementById('save').onclick=()=>{const data={media_sha256:HASH,events,notes:document.getElementById('notes').value,scope:'Playback events and reviewer notes only; not proof of attention or comprehension.'};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download='playback-observations.json';a.click();URL.revokeObjectURL(a.href);};
</script>'''.replace('HASH', json.dumps(media_hash))
    (output / 'review.html').write_text(page)
    return task


def finalize(review_path, task_path, base_path, output, kind):
    """Import an independent completed review into a NEW report, never edit history."""
    task = json.loads(Path(task_path).read_text())
    if digest(Path(task_path).parent / 'media.mp4') != task['media_sha256']:
        raise ValueError('Review packet media changed')
    review = json.loads(Path(review_path).read_text())
    base = json.loads(Path(base_path).read_text())
    hash_key = 'sha256' if kind == 'video' else 'video_sha256'
    if base.get(hash_key) != task['media_sha256'] or base.get('duration') != task['duration']:
        raise ValueError('Baseline report must describe the exact packet video')
    result = validate(review, task['media_sha256'], task['duration'], task['producer_ids'])
    if result['status'] == 'REWORK':
        report = dict(base)
        report.update(perceptual_review=review, producer_ids=task['producer_ids'],
                      status='REWORK', total=None, formal_acceptance=False,
                      blocking_gaps=result['missing'], review_kind='independent_review_found_defect')
        report['issues'] = list(base.get('issues', [])) + list(review.get('issues', []))
        with Path(output).open('x') as target:
            json.dump(report, target, ensure_ascii=False, indent=2)
        return report
    if result['status'] != 'COMPLETE':
        raise ValueError('Review not complete: ' + json.dumps(result))
    entries = review.get('video_dimensions' if kind == 'video' else 'dimensions', {})
    from .video_qa import WEIGHTS as video_weights, gate as video_gate
    from .audience_qa import WEIGHTS as audience_weights, gate as audience_gate
    weights = video_weights if kind == 'video' else audience_weights
    evidence_paths = {e['path'] for e in review['evidence']}
    for name in weights:
        # The audio dimension must come from the existing independent audio report.
        if kind == 'video' and name == 'audio':
            continue
        entry = entries.get(name, {})
        stamp = entry.get('time')
        refs = entry.get('evidence')
        if (not number(entry.get('score')) or not 0 <= entry['score'] <= 100 or
                not number(stamp) or not 0 <= stamp < task['duration'] or
                not isinstance(refs, list) or not refs or
                not all(isinstance(ref, str) and ref in evidence_paths for ref in refs) or
                not entry.get('rationale')):
            raise ValueError('Missing timecoded scoring evidence: ' + name)
    report = dict(base)
    report.update(perceptual_review=review, producer_ids=task['producer_ids'],
                  review_kind='independent_evidence_attested_av', formal_acceptance=False,
                  review_source_sha256=digest(review_path), blocking_gaps=[])
    if kind == 'video':
        scores = {name: entries[name]['score'] for name in weights if name != 'audio'}
        scores['audio'] = None
        if base.get('audio_qa_report'):
            from .video_qa import audio_score
            scores['audio'] = audio_score(json.loads(Path(base['audio_qa_report']).read_text()), task['media_sha256'])
        issues = list(base.get('issues', [])) + list(review.get('issues', []))
        status, total = video_gate(scores, [i for i in issues if i.get('status') != 'closed'])
        report.update(scores=scores, issues=issues, status=status, total=total)
    else:
        status, total = audience_gate(entries, result['coverage'])
        report.update(dimensions=entries, coverage=result['coverage'], status=status, total=total)
    if status != 'PASS':
        report['blocking_gaps'] = ['scoring/independent audio evidence or unresolved issues; inspect report']
    with Path(output).open('x') as target:
        json.dump(report, target, ensure_ascii=False, indent=2)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    packet = sub.add_parser('prepare')
    packet.add_argument('video', type=Path)
    packet.add_argument('--output', required=True, type=Path)
    packet.add_argument('--producer-id', action='append', required=True)
    check = sub.add_parser('validate')
    check.add_argument('review', type=Path)
    check.add_argument('--task', type=Path, required=True)
    imported = sub.add_parser('finalize')
    imported.add_argument('review', type=Path)
    imported.add_argument('--task', type=Path, required=True)
    imported.add_argument('--base-report', type=Path, required=True)
    imported.add_argument('--output', type=Path, required=True)
    imported.add_argument('--kind', choices=('video', 'audience'), required=True)
    args = p.parse_args()
    if args.command == 'finalize':
        report = finalize(args.review, args.task, args.base_report, args.output, args.kind)
        print(json.dumps({'status': report['status'], 'formal_acceptance': False}))
        return {'PASS': 0, 'REWORK': 2, 'NEEDS_REVIEW': 3, 'FAIL': 4}[report['status']]
    if args.command == 'prepare':
        print(json.dumps(prepare(args.video, args.output, args.producer_id)))
        return 3
    task = json.loads(args.task.read_text())
    media = args.task.parent / 'media.mp4'
    if digest(media) != task['media_sha256']:
        raise ValueError('Review packet media changed')
    result = validate(json.loads(args.review.read_text()), task['media_sha256'], task['duration'], task['producer_ids'])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return {'COMPLETE': 0, 'REWORK': 2, 'NEEDS_REVIEW': 3}[result['status']]


if __name__ == '__main__':
    raise SystemExit(main())
