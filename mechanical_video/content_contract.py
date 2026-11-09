"""Fail-closed topic/causal proof associations before costly production.

This validates evidence and requirement traceability, not semantic truth or perception.
"""
import hashlib
import json
import math
import subprocess
from pathlib import Path


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def evaluate(checks, base, stage):
    errors = []
    assets = checks.get('assets', {})
    if not isinstance(assets, dict):
        return ['content contract: missing assets']

    def path_of(ref):
        path = Path(ref['path'])
        return path if path.is_absolute() else Path(base) / path

    def linked(ref):
        try:
            return isinstance(ref, dict) and path_of(ref).is_file() and sha(path_of(ref)) == ref['sha256']
        except (KeyError, TypeError, OSError, ValueError):
            return False

    contract_ref = assets.get('content_contract')
    if not linked(contract_ref):
        return ['content contract: missing/stale frozen intent']
    try:
        contract = json.loads(path_of(contract_ref).read_text())
        brief_ref = contract.get('brief')
        if contract.get('schema_version') != 1 or not isinstance(contract.get('question'), str) or not contract['question'].strip():
            raise ValueError('question')
        if brief_ref != assets.get('approved_brief') or not linked(brief_ref):
            return ['content contract: original brief missing/stale/unbound']
        brief = path_of(brief_ref).read_text()
        requirements = contract['requirements']
        if not isinstance(requirements, list) or not requirements:
            raise ValueError('requirements')
        ids = []
        for requirement in requirements:
            rid = requirement.get('id')
            if not isinstance(rid, str) or not rid.strip() or rid in ids:
                raise ValueError('requirement IDs')
            ids.append(rid)
            quote = requirement.get('brief_quote')
            if not isinstance(quote, str) or not quote.strip() or quote not in brief:
                errors.append('content contract: requirement not grounded in original brief: ' + rid)
            if not requirement.get('observable') or not requirement.get('source_parts'):
                errors.append('content contract: missing observable/source parts: ' + rid)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return ['content contract: invalid intent document']
    review = checks.get('content_review', {})
    if not isinstance(review, dict) or review.get('contract_sha256') != contract_ref['sha256']:
        return errors + ['content contract: review not bound to intent']
    fingerprints = {k:v.get('sha256') for k,v in assets.items() if isinstance(v, dict)}
    if review.get('asset_fingerprints') != fingerprints:
        errors.append('content contract: stale reviewed assets')
    if (not review.get('producer') or not review.get('reviewer') or
            review.get('producer') == review.get('reviewer')):
        errors.append('content contract: independent intent/mechanism reviewer missing')
    refs = review.get('evidence', [])
    if not isinstance(refs, list) or not refs or not all(linked(ref) for ref in refs):
        errors.append('content contract: actual review evidence missing/stale')
    script_id = review.get('script_asset')
    script_ref = assets.get(script_id) if isinstance(script_id, str) else None
    if not linked(script_ref):
        return errors + ['content contract: frozen narration draft missing/stale']
    try:
        script = path_of(script_ref).read_text()
    except (OSError, UnicodeError):
        return errors + ['content contract: cannot read narration draft']
    proofs = review.get('requirements', [])
    if not isinstance(proofs, list):
        return errors + ['content contract: requirement proofs missing']
    proof_ids = [p.get('id') for p in proofs if isinstance(p, dict) and isinstance(p.get('id'), str)]
    if len(proof_ids) != len(set(proof_ids)) or set(proof_ids) != set(ids):
        errors.append('content contract: omitted/duplicate/substituted requirements')
    numeric = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
    clip_durations = {}
    def duration(ref):
        key = ref['sha256']
        if key not in clip_durations:
            try:
                result = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path_of(ref))], capture_output=True, text=True, timeout=30, check=True)
                data = json.loads(result.stdout)
                value = float(data['format']['duration'])
                if not math.isfinite(value) or value <= 0 or not any(s.get('codec_type') == 'video' for s in data['streams']):
                    raise ValueError('not video')
                subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path_of(ref)), '-map', '0:v:0', '-f', 'null', '-'], capture_output=True, timeout=60, check=True)
                clip_durations[key] = value
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                clip_durations[key] = 0
        return clip_durations[key]

    for rid in ids:
        proof = next((p for p in proofs if isinstance(p, dict) and p.get('id') == rid), {})
        quote = proof.get('script_quote')
        if not isinstance(quote, str) or not quote.strip() or quote not in script:
            errors.append('content contract: answer absent from narration: ' + rid)
        if proof.get('verdict') != 'clear' or proof.get('source_consistent') is not True:
            errors.append('content contract: causal proof unresolved: ' + rid)
        # Require context, state change and source relationship; declarations
        # alone cannot be considered a local mechanism proof.
        states = proof.get('observations', [])
        if not isinstance(states, list):
            states = []
        if (not isinstance(states, list) or len(states) < 2 or
                not all(isinstance(s, dict) and numeric(s.get('time')) and s['time'] >= 0
                        and bool(s.get('observation')) and linked(s.get('evidence')) for s in states) or
                len({s.get('time') for s in states if isinstance(s, dict)}) < 2):
            errors.append('content contract: actual before/after observations missing: ' + rid)
        clip_id = proof.get('clip_asset')
        clip = assets.get(clip_id) if isinstance(clip_id, str) else None
        if not linked(clip) or path_of(clip).suffix.lower() not in ('.mp4', '.mov', '.mkv'):
            errors.append('content contract: encoded local mechanism clip missing: ' + rid)
        clip_duration = duration(clip) if linked(clip) else 0
        if not clip_duration:
            errors.append('content contract: local clip is not decodable video: ' + rid)
        interval = proof.get('clip_interval')
        if (not isinstance(interval, list) or len(interval) != 2 or
                not all(numeric(x) for x in interval) or not 0 <= interval[0] < interval[1] <= clip_duration or
                any(not interval[0] <= s.get('time', -1) <= interval[1] for s in states if isinstance(s, dict) and numeric(s.get('time')))):
            errors.append('content contract: observation outside local clip: ' + rid)
        if not proof.get('causal_explanation') or not proof.get('input_linkage') or not proof.get('output_result'):
            errors.append('content contract: incomplete input/contact/output chain: ' + rid)
        if stage == 'delivery':
            final = proof.get('final_interval')
            required = checks.get('required_interval')
            final_ref = assets.get('final_media')
            if (not linked(final_ref) or proof.get('final_media_sha256') != final_ref['sha256'] or
                    not isinstance(final, list) or len(final) != 2 or not all(numeric(x) for x in final) or
                    not isinstance(required, list) or len(required) != 2 or not all(numeric(x) for x in required) or
                    not required[0] <= final[0] < final[1] <= required[1] or
                    not linked(proof.get('final_evidence'))):
                errors.append('content contract: final causal payoff not traced: ' + rid)
    return errors
