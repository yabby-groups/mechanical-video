"""Persistent Director dispatch ledger. Never invokes collaboration/provider tools.

Agent IDs and receipts are trusted session attestations, not authentication.
All mutations lock a sidecar and atomically replace the director record.
"""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile

CHAIN = ('original-intent', 'minimal-sample', 'independent-check',
         'measured-narration-timeline', 'preflight', 'render',
         'independent-post-review', 'delivery')
REVIEW_STAGES = {'independent-check', 'independent-post-review'}


def _is_review(task):
    return task.get('kind') == 'review' or (task.get('kind') != 'repair' and task['stage'] in REVIEW_STAGES)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _path(base, value):
    return (Path(base) / value).resolve()


def _overlap(left, right):
    return left == right or left in right.parents or right in left.parents


def _refs(base, refs):
    if not isinstance(refs, dict):
        raise ValueError('fingerprints must be a mapping')
    for path, digest in refs.items():
        if not isinstance(digest, str) or _sha(_path(base, path)) != digest:
            raise ValueError('missing or stale evidence: ' + path)


@contextmanager
def _transaction(path):
    path = Path(path).resolve()
    with path.with_suffix(path.suffix + '.repair.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        record = json.loads(path.read_text())
        bound = record.get('repair_controller', {}).get('record_path')
        if bound and bound != str(path):
            raise ValueError('resume the canonical controller record; copied versions cannot dispatch')
        yield record, path.parent
        fd, temporary = tempfile.mkstemp(prefix='.repair-', dir=path.parent)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(record, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def initialize(path, tasks=None, capabilities=None, capability_benchmarks=None):
    """Create once; repeated initialization never resets budgets/issues/running work.

    Task: id, stage, owner, deps, inputs {path:sha256}, outputs [exclusive paths],
    required_checks [names], capabilities [names], optional command [argv].
    """
    with _transaction(path) as (record, base):
        if 'repair_controller' in record:
            return deepcopy(record['repair_controller'])
        default_workflow = tasks is None
        if tasks is None:
            tasks = [dict(id=stage, stage=stage, owner='Director' if i == 0 else
                          ('Reviewer' if stage in REVIEW_STAGES else 'Producer'),
                          deps=[] if i == 0 else [CHAIN[i-1]], inputs={}, outputs=[],
                          required_checks=[stage], capabilities=(['continuous_av', 'audio'] if stage in REVIEW_STAGES else []))
                     for i, stage in enumerate(CHAIN)]
            by_id = {task['id']: task for task in tasks}
            for producer, reviewer in [('original-intent', 'independent-check'),
                    ('minimal-sample', 'independent-check'),
                    ('measured-narration-timeline', 'preflight'), ('render', 'independent-post-review')]:
                by_id[producer]['review_by'] = reviewer
            by_id['preflight'].update(kind='review', owner='Reviewer')
            by_id['delivery'].update(kind='handoff', owner='Director')
        tasks = deepcopy(tasks)
        ids = [t['id'] for t in tasks]
        if len(set(ids)) != len(ids):
            raise ValueError('duplicate task id')
        outputs = set()
        for task in tasks:
            task.setdefault('deps', [])
            task.setdefault('inputs', {})
            task.setdefault('outputs', [])
            task.setdefault('required_checks', [task['stage']])
            task.setdefault('capabilities', [])
            if not task.get('owner') or not task['required_checks']:
                raise ValueError('owner and required checks required')
            if any(d not in ids or d == task['id'] for d in task['deps']):
                raise ValueError('invalid dependency')
            _refs(base, task['inputs'])
            normalized = {_path(base, p) for p in task['outputs']}
            if (any(_overlap(a,b) for a in outputs for b in normalized)
                    or len(normalized) != len(task['outputs'])
                    or any(a != b and _overlap(a,b) for a in normalized for b in normalized)):
                raise ValueError('outputs must have exclusive ownership')
            outputs |= normalized
            task['status'] = 'pending'
        pending, visited = set(ids), set()
        while pending:
            ready = {t['id'] for t in tasks if t['id'] in pending and set(t['deps']) <= visited}
            if not ready:
                raise ValueError('cyclic task DAG')
            pending -= ready
            visited |= ready
        for task in tasks:
            target = task.get('review_by')
            if target:
                reviewer = __import__('builtins').next((t for t in tasks if t['id'] == target), None)
                if not reviewer or not _is_review(reviewer):
                    raise ValueError('review_by must name an explicit independent review task')
                ancestors, frontier = set(), list(reviewer['deps'])
                by_id = {t['id']: t for t in tasks}
                while frontier:
                    dependency = frontier.pop()
                    if dependency not in ancestors:
                        ancestors.add(dependency); frontier.extend(by_id[dependency]['deps'])
                if task['id'] not in ancestors:
                    raise ValueError('explicit reviewer must depend on its producer')
            if task.get('kind') == 'handoff' and (task['stage'] != 'delivery' or task['outputs']):
                raise ValueError('terminal handoff cannot create unreviewed assets')
        state = dict(schema_version=1, record_path=str(Path(path).resolve()),
                     unattended=default_workflow or record.get('production_checks', {}).get('schema_version', 0) >= 5,
                     tasks={t['id']: t for t in tasks}, issues={},
                     capabilities=list(capabilities or []), capability_benchmarks=deepcopy(capability_benchmarks or {}), agents={}, handoffs=0,
                     completions={}, events=[])
        for collection in (record.get('issues', []), record.get('open_issues', []), record.get('prior_version_issues', []), record.get('production_checks', {}).get('issues', [])):
            if isinstance(collection, list):
                for issue in collection:
                    if isinstance(issue, dict) and issue.get('issue_id'):
                        key = issue['issue_id']
                        prior = state['issues'].get(key, {})
                        imported = deepcopy(issue)
                        imported['repair_attempts'] = max(prior.get('repair_attempts', 0), issue.get('repair_attempts', 0))
                        imported['rounds_without_improvement'] = max(prior.get('rounds_without_improvement', 0), issue.get('rounds_without_improvement', 0))
                        imported.setdefault('status', 'open')
                        state['issues'][key] = imported
        record['repair_controller'] = state
        return deepcopy(state)


def _capability_errors(state, required, base):
    errors = []
    missing = set(required) - set(state['capabilities'])
    if {'continuous_av', 'audio'} <= set(required):
        adapters = {state.get('capability_benchmarks', {}).get(name, {}).get('adapter')
                    for name in ('continuous_av', 'audio')}
        if len(adapters - {None}) > 1:
            errors.append('audio and continuous video must use the same benchmarked acceptance adapter')
    for capability in set(required) & {'continuous_av', 'audio'}:
        benchmark = state.get('capability_benchmarks', {}).get(capability, {})
        try:
            _refs(base, benchmark.get('evidence', {}))
            if not benchmark.get('evidence') or not benchmark.get('adapter') or not {'action_contradiction', 'occlusion', 'speech_desync'} <= set(benchmark.get('detected', [])):
                raise ValueError('unbenchmarked sensory capability: ' + capability)
            report_path = __import__('builtins').next(iter(benchmark['evidence']))
            report = json.loads(_path(base, report_path).read_text())
            if report.get('adapter') != benchmark['adapter'] or not {'action_contradiction', 'occlusion', 'speech_desync'} <= set(report.get('detected', [])):
                raise ValueError('sensory benchmark mismatch')
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append(str(exc))
    if missing:
        errors.append('capabilities unavailable: ' + ', '.join(sorted(missing)))
    return errors


def _blockers(state, task, base, seen=None):
    seen = set() if seen is None else seen
    if task['id'] in seen:
        return []
    seen.add(task['id'])
    errors = []
    if any(state['tasks'][d]['status'] != 'done' for d in task['deps']):
        errors.append('dependencies incomplete')
    for dependency in task['deps']:
        upstream = state['tasks'][dependency]
        errors.extend(_blockers(state, upstream, base, seen))
        try:
            _refs(base, upstream.get('result', {}).get('outputs', {}))
            _refs(base, upstream.get('result', {}).get('evidence', {}))
        except (OSError, ValueError, TypeError) as exc:
            errors.append(str(exc))
    required = list(task['capabilities'])
    if state.get('unattended') and not _is_review(task) and task['stage'] in ('minimal-sample', 'measured-narration-timeline', 'render', 'delivery'):
        required = sorted(set(required) | {'continuous_av', 'audio'})
    errors.extend(_capability_errors(state, required, base))
    try:
        _refs(base, task['inputs'])
    except (OSError, ValueError, TypeError) as exc:
        errors.append(str(exc))
    issue = state['issues'].get(task.get('issue_id'))
    if issue and (issue['repair_attempts'] >= 3 or issue['rounds_without_improvement'] >= 2) and task.get('kind') == 'repair' and task['status'] == 'pending':
        errors.append('repair strategy limit reached')
    return errors


def next(path):
    """Read readiness without dispatching anything."""
    record = json.loads(Path(path).read_text())
    state, base = record['repair_controller'], Path(path).resolve().parent
    if state.get('record_path') and state['record_path'] != str(Path(path).resolve()):
        raise ValueError('resume the canonical controller record; copied versions cannot dispatch')
    ready, blocked = [], {}
    for task in state['tasks'].values():
        if task['status'] == 'blocked':
            blocked[task['id']] = ['failed/incomplete check; owned repair required']
        if task['status'] != 'pending':
            continue
        errors = _blockers(state, task, base)
        if errors:
            blocked[task['id']] = errors
        else:
            ready.append(deepcopy(task))
    capability_errors = _capability_errors(state, ['continuous_av', 'audio'], base) if state.get('unattended') else []
    for task in state['tasks'].values():
        if task['status'] == 'done':
            errors = _blockers(state, task, base)
            try:
                _refs(base, task.get('result', {}).get('outputs', {}))
                _refs(base, task.get('result', {}).get('evidence', {}))
            except (OSError, ValueError, TypeError) as exc:
                errors.append(str(exc))
            if errors:
                blocked[task['id']] = sorted(set(errors))
    workflow_status = ('DEPENDENCY_BLOCKED' if capability_errors else
        ('COMPLETE' if not blocked and all(t['status'] == 'done' for t in state['tasks'].values())
         and all(i['status'] == 'closed' for i in state['issues'].values()) else 'IN_PROGRESS'))
    return {'workflow_status': workflow_status,
            'dependency_owner': 'Director' if capability_errors else None,
            'dependency_errors': capability_errors,
            'ready': ready, 'blocked': blocked,
            'running': [deepcopy(t) for t in state['tasks'].values() if t['status'] == 'running']}


def claim(path, task_id, agent_id, dispatch_receipt, dispatch_kind='spawn'):
    """Director records the actual tool result; reserve fourth spawn for review."""
    with _transaction(path) as (record, base):
        state = record['repair_controller']
        if record.get('hold') or record.get('editorial_hold') or record.get('production_checks', {}).get('holds'):
            raise ValueError('active hold')
        task = state['tasks'][task_id]
        if task['status'] != 'pending':
            raise ValueError('task is not pending; uncertain running tasks cannot be redispatched')
        errors = _blockers(state, task, base)
        if errors:
            raise ValueError('; '.join(errors))
        if not isinstance(agent_id, str) or not agent_id.strip() or not isinstance(dispatch_receipt, dict) or not dispatch_receipt:
            raise ValueError('real agent id and tool dispatch receipt required')
        if dispatch_receipt.get('agent_id') != agent_id:
            raise ValueError('receipt agent mismatch')
        review = _is_review(task)
        if review and agent_id in task.get('excluded_agents', []):
            raise ValueError('producer cannot independently review')
        # Review lineage includes producing ancestors, including rewritten review dependencies.
        ancestors, frontier = set(), list(task['deps'])
        while frontier:
            dependency = frontier.pop()
            if dependency not in ancestors:
                ancestors.add(dependency)
                frontier.extend(state['tasks'][dependency]['deps'])
        if review and any(state['tasks'][d].get('agent_id') == agent_id and not _is_review(state['tasks'][d]) for d in ancestors):
            raise ValueError('producer cannot review own upstream work')
        # Generic review stages also exclude every direct dependency producer.
        if review and any(state['tasks'][d].get('agent_id') == agent_id for d in task['deps']):
            raise ValueError('producer cannot independently review')
        if state['handoffs'] >= 20:
            raise ValueError('handoff budget exhausted')
        agents = state['agents']
        for identity, entry in agents.items():
            entry.setdefault('receipts', [deepcopy(t['dispatch_receipt']) for t in state['tasks'].values()
                                         if t.get('agent_id') == identity and t.get('dispatch_receipt')])
        if dispatch_kind == 'director':
            if (review or task['owner'] != 'Director'
                    or dispatch_receipt != {'agent_id': agent_id, 'source': 'active_session', 'role': 'Director'}
                    or (state.get('director_id') not in (None, agent_id))
                    or (agent_id in agents and not agents[agent_id].get('director'))):
                raise ValueError('Director execution requires the active session and cannot review')
            state['director_id'] = agent_id
            agents.setdefault(agent_id, {'director': True, 'followups': 0, 'receipts': [deepcopy(dispatch_receipt)]})
        elif dispatch_kind == 'spawn':
            spawned = sum(not entry.get('director') for entry in agents.values())
            if agent_id in agents or spawned >= (4 if review else 3):
                raise ValueError('spawn budget exhausted or review slot reserved')
            agents[agent_id] = {'followups': 0, 'receipts': [deepcopy(dispatch_receipt)]}
        elif dispatch_kind == 'followup':
            if agent_id not in agents or agents[agent_id].get('director') or agents[agent_id]['followups'] >= 1:
                raise ValueError('followup budget exhausted')
            agents[agent_id]['followups'] += 1
            agents[agent_id]['receipts'].append(deepcopy(dispatch_receipt))
        elif dispatch_kind == 'reuse':
            if agent_id not in agents or agents[agent_id].get('director') or dispatch_receipt not in agents[agent_id]['receipts']:
                raise ValueError('reuse requires identical actual prior dispatch receipt')
        else:
            raise ValueError('dispatch_kind must be director, spawn, followup or reuse')
        if any(t['status'] == 'running' and t.get('agent_id') == agent_id for t in state['tasks'].values()):
            raise ValueError('agent already has running task')
        occupied = {_path(base, p) for t in state['tasks'].values() if t['status'] == 'running' for p in t['outputs']}
        if occupied & {_path(base, p) for p in task['outputs']}:
            raise ValueError('output already owned by running task')
        state['handoffs'] += 1
        task.update(status='running', agent_id=agent_id, dispatch_receipt=deepcopy(dispatch_receipt))
        state['events'].append({'event': 'claim', 'task_id': task_id, 'agent_id': agent_id})
        return deepcopy(task)


def _review(state, task, outputs):
    if task.get('kind') == 'handoff':
        if task['stage'] != 'delivery' or outputs:
            raise ValueError('terminal handoff cannot create unreviewed assets')
        return
    if task.get('review_by') and task.get('kind') != 'repair':
        review = state['tasks'][task['review_by']]
        if review['status'] != 'pending' or not _is_review(review):
            raise ValueError('explicit independent reviewer is not pending')
        review['inputs'].update(deepcopy(outputs))
        review['required_checks'] = sorted(set(review['required_checks']) | set(task['required_checks']))
        review.setdefault('excluded_agents', []).append(task['agent_id'])
        review.setdefault('subjects', []).append(task['id'])
        return
    review_id = task['id'] + ':review'
    state['tasks'][review_id] = dict(id=review_id, stage=task['stage'], kind='review',
        owner='Independent Reviewer', deps=[task['id']], inputs=deepcopy(outputs), outputs=[],
        required_checks=list(task['required_checks']), capabilities=list(task.get('review_capabilities', task['capabilities'])),
        status='pending', excluded_agents=[task['agent_id']], producer=task['agent_id'],
        issue_id=task.get('issue_id'), subject=task['id'])
    # Existing dependents must wait for this actual independent review.
    for other in list(state['tasks'].values()):
        if other['id'] != review_id and task['id'] in other['deps']:
            other['deps'] = [review_id if d == task['id'] else d for d in other['deps']]


def complete(path, task_id, agent_id, completion_id, outputs=None, checks=None,
             verdict='pass', failures=None, improvement=None, evidence=None):
    """A failed review creates stable issue + unique-owner local repair task.

    Failure entries require issue_id, owner, required_checks, severity, evidence
    {path:sha}. Reviewer PASS requires all checks and same-version evidence.
    """
    payload = dict(task_id=task_id, agent_id=agent_id, outputs=outputs or {},
                   checks=checks or [], verdict=verdict, failures=failures or [],
                   improvement=improvement, evidence=evidence or {})
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    with _transaction(path) as (record, base):
        state = record['repair_controller']
        if not completion_id:
            raise ValueError('completion id required')
        prior = state['completions'].get(completion_id)
        if prior:
            if prior['digest'] != digest:
                raise ValueError('completion id reused with different result')
            return deepcopy(prior['result'])
        task = state['tasks'][task_id]
        if task['status'] != 'running' or task['agent_id'] != agent_id:
            raise ValueError('completion does not match running assignment')
        errors = _blockers(state, task, base)
        if errors:
            raise ValueError('; '.join(errors))
        if state['handoffs'] >= 20:
            raise ValueError('handoff budget exhausted')
        if verdict not in ('pass', 'fail', 'needs-review'):
            raise ValueError('invalid verdict')
        _refs(base, task['inputs'])
        _refs(base, payload['outputs'])
        _refs(base, payload['evidence'])
        if {_path(base, p) for p in payload['outputs']} != {_path(base, p) for p in task['outputs']}:
            raise ValueError('completion outputs differ from exclusive ownership')
        review = _is_review(task)
        if verdict == 'pass' and not set(task['required_checks']) <= set(payload['checks']):
            raise ValueError('required checks incomplete')
        if review and verdict == 'pass' and not payload['evidence']:
            raise ValueError('independent review evidence required')
        if verdict in ('fail', 'needs-review') and not payload['failures']:
            raise ValueError('failed or incomplete review needs an owned repair/dependency issue')
        for failure in payload['failures']:
            if not all(failure.get(k) for k in ('issue_id', 'owner', 'required_checks', 'severity', 'evidence')):
                raise ValueError('incomplete stable issue')
            _refs(base, failure['evidence'])
        if verdict == 'pass' and task.get('command'):
            executions = state.get('executions', {}).values()
            if not any(e['task_id'] == task_id and e['command'] == task['command'] and e['status'] == 'completed' and e.get('returncode') == 0 and e['inputs'] == task['inputs'] for e in executions):
                raise ValueError('successful bound command execution receipt required')
        if verdict == 'pass' and task['stage'] == 'delivery':
            from .production_gate import evaluate
            gate = evaluate(record, base, 'delivery', require_version=5)
            if gate['status'] != 'READY':
                raise ValueError('delivery requires independent acceptance: ' + '; '.join(gate.get('reasons', [])))
        state['handoffs'] += 1
        task.update(status='done' if verdict == 'pass' else 'blocked', result=payload)
        if task.get('kind') == 'repair' and verdict in ('pass', 'fail', 'needs-review'):
            issue = state['issues'][task['issue_id']]
            issue['repair_attempts'] += 1
            issue['rounds_without_improvement'] = 0 if improvement is True else issue['rounds_without_improvement'] + 1
        if verdict == 'pass' and not review:
            _review(state, task, payload['outputs'])
        elif verdict == 'pass' and task.get('issue_id'):
            issue = state['issues'][task['issue_id']]
            issue.update(status='closed', resolution=dict(issue_id=issue['issue_id'], verdict='verified',
                producer=task['producer'], reviewer=agent_id, asset_fingerprints=task['inputs'],
                checks_covered=payload['checks'], evidence=payload['evidence']))
            # Unblock failed review only through verified repair, preserving history.
            failed = state['tasks'][issue['failed_task']]
            repaired = state['tasks'][task['subject']]
            superseded_inputs = set(repaired['inputs'])
            failed.setdefault('failed_history', []).append(deepcopy(failed.get('result', {})))
            for old_path in superseded_inputs:
                failed['inputs'].pop(old_path, None)
            failed['inputs'].update(task['inputs'])
            all_closed = all(i['status'] == 'closed' for i in state['issues'].values() if i.get('failed_task') == failed['id'])
            failed.update(status='done' if all_closed else 'blocked', result=deepcopy(payload), resolved_by=task['id'])
            for downstream in state['tasks'].values():
                if failed['id'] in downstream['deps']:
                    for old_path in superseded_inputs:
                        downstream['inputs'].pop(old_path, None)
                    downstream['inputs'].update(task['inputs'])
        for failure in payload['failures']:
            key = failure['issue_id']
            issue = state['issues'].get(key)
            if issue is None:
                issue = deepcopy(failure)
                issue.update(status='open', repair_attempts=0, rounds_without_improvement=0, failed_task=task_id)
                state['issues'][key] = issue
            else:
                if issue.get('owner', failure['owner']) != failure['owner'] or set(issue.get('required_checks', failure['required_checks'])) != set(failure['required_checks']):
                    raise ValueError('stable issue owner/checks cannot be reset')
                issue['status'] = 'open'
                issue.setdefault('failed_task', task_id)
                issue.setdefault('owner', failure['owner'])
                issue.setdefault('required_checks', failure['required_checks'])
            repair_id = key + ':repair:' + str(issue['repair_attempts'] + 1)
            if repair_id not in state['tasks']:
                subject = state['tasks'].get(task.get('subject'), task)
                repair_outputs = failure.get('repair_outputs', subject['outputs'])
                reserved = [_path(base, p) for t in state['tasks'].values() for p in t.get('outputs', [])]
                if any(_overlap(_path(base,p), q) for p in repair_outputs for q in reserved):
                    raise ValueError('repair output conflicts with an existing exclusive output')
                if any(_path(base, p) in {_path(base, q) for t in state['tasks'].values() for q in t.get('inputs', {})} for p in repair_outputs):
                    raise ValueError('repair must use new version outputs; preserve existing evidence')
                state['tasks'][repair_id] = dict(id=repair_id, stage=subject['stage'], kind='repair',
                    issue_id=key, owner=issue['owner'], deps=[], inputs=deepcopy(failure.get('repair_inputs', payload['outputs'] or task['inputs'])),
                    outputs=list(repair_outputs), required_checks=list(issue['required_checks']),
                    capabilities=list(failure.get('repair_capabilities', subject['capabilities'])),
                    review_capabilities=list(subject.get('review_capabilities', subject['capabilities'])), status='pending')
                # Superseded completed output owner is historical, never running concurrently.
        result = dict(task_id=task_id, status=task['status'], verdict=verdict)
        state['completions'][completion_id] = {'digest': digest, 'result': result}
        return deepcopy(result)


def resume(path):
    """Inspect persisted state; never reset or resubmit uncertain tool executions."""
    result = next(path)
    result['uncertain_running'] = [t['id'] for t in result['running']]
    result['automatic_redispatch'] = False
    return result


def validate_execution(record, base, stage):
    """Fail-closed v5 integration helper; does not claim perceptual authentication."""
    state = record.get('repair_controller')
    if not isinstance(state, dict) or state.get('schema_version') != 1:
        return ['missing repair_controller v1']
    errors = []
    mapped = {'narration': 'measured-narration-timeline', 'full-render': 'render', 'delivery': 'delivery'}.get(stage)
    active = [t for t in state['tasks'].values() if t['stage'] == mapped and t['status'] == 'running' and t.get('agent_id') and t.get('dispatch_receipt')]
    if len(active) != 1:
        errors.append('exactly one claimed real execution task required')
    else:
        errors.extend(_blockers(state, active[0], base))
    required = {'narration': CHAIN[:3], 'full-render': CHAIN[:5], 'delivery': CHAIN[:-1]}.get(stage)
    if required is None:
        return ['unknown execution stage']
    if record.get('hold') or record.get('editorial_hold'):
        errors.append('active hold')
    for name in required:
        candidates = [t for t in state['tasks'].values() if t['stage'] == name and t.get('kind') != 'repair' and not t.get('subject')]
        if not candidates or any(t['status'] != 'done' for t in candidates):
            errors.append('controller stage incomplete: ' + name)
    for task in state['tasks'].values():
        if task['stage'] not in required:
            continue
        if task['status'] != 'done':
            errors.append('controller task unresolved: ' + task['id'])
        if task['status'] == 'done':
            if (not task.get('agent_id') or not task.get('dispatch_receipt') or not task.get('result')
                    or not any(e.get('event') == 'claim' and e.get('task_id') == task['id']
                               and e.get('agent_id') == task['agent_id'] for e in state.get('events', []))):
                errors.append('completed task lacks actual execution record: ' + task['id'])
            try:
                _refs(base, task['inputs'])
                _refs(base, task.get('result', {}).get('outputs', {}))
                _refs(base, task.get('result', {}).get('evidence', {}))
            except (OSError, ValueError, TypeError) as exc:
                errors.append(str(exc))
    for issue in state['issues'].values():
        if issue['status'] != 'closed':
            errors.append('unresolved issue: ' + issue['issue_id'])
    return errors


def command_guard(record, base, stage, command):
    errors = validate_execution(record, base, stage)
    tasks = record.get('repair_controller', {}).get('tasks', {}).values()
    mapped = {'narration': 'measured-narration-timeline', 'full-render': 'render', 'delivery': 'delivery'}.get(stage)
    if not command or not any(t['stage'] == mapped and t['status'] == 'running' and t.get('command') == command for t in tasks):
        errors.append('command not bound to running controller task')
    return errors


def capability(path, name, benchmark):
    """Register an actually exercised adapter; declarations alone cannot enable it."""
    if name not in ('continuous_av', 'audio'):
        raise ValueError('unsupported review capability')
    with _transaction(path) as (record, base):
        state = record['repair_controller']
        candidate = deepcopy(state)
        if name not in candidate['capabilities']:
            candidate['capabilities'].append(name)
        candidate['capability_benchmarks'][name] = deepcopy(benchmark)
        errors = _capability_errors(candidate, [name], base)
        if errors:
            raise ValueError('; '.join(errors))
        state['events'].append(dict(event='capability', name=name,
            prior=deepcopy(state['capability_benchmarks'].get(name)), benchmark=deepcopy(benchmark)))
        state['capabilities'] = candidate['capabilities']
        state['capability_benchmarks'] = candidate['capability_benchmarks']
        return deepcopy(benchmark)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', required=True, type=Path)
    parser.add_argument('action', choices=('initialize', 'next', 'claim', 'complete', 'resume', 'capability'))
    parser.add_argument('--payload', type=Path, help='JSON object with API keyword arguments')
    args = parser.parse_args(argv)
    payload = json.loads(args.payload.read_text()) if args.payload else {}
    try:
        result = globals()[args.action](args.record, **payload)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0




def start_execution(path, stage, command):
    """Persist launch intent before subprocess; uncertain launches never replay."""
    import uuid
    with _transaction(path) as (record, base):
        errors = command_guard(record, base, stage, command)
        if errors:
            raise ValueError('; '.join(errors))
        state = record['repair_controller']
        mapped = {'narration': 'measured-narration-timeline', 'full-render': 'render', 'delivery': 'delivery'}[stage]
        task = __import__('builtins').next(t for t in state['tasks'].values() if t['stage'] == mapped and t['status'] == 'running' and t.get('command') == command)
        launches = state.setdefault('executions', {})
        if any(e['task_id'] == task['id'] for e in launches.values()):
            raise ValueError('execution already completed or uncertain; never automatically replay')
        token = uuid.uuid4().hex
        launches[token] = dict(task_id=task['id'], stage=stage, command=list(command),
                               inputs=deepcopy(task['inputs']), status='uncertain', agent_id=task['agent_id'])
        return token


def finish_execution(path, token, returncode):
    with _transaction(path) as (record, base):
        execution = record['repair_controller']['executions'][token]
        if execution['status'] == 'completed':
            if execution['returncode'] != returncode:
                raise ValueError('execution completion conflict')
            return deepcopy(execution)
        _refs(base, execution['inputs'])
        execution.update(status='completed', returncode=returncode)
        return deepcopy(execution)

if __name__ == '__main__':
    raise SystemExit(main())
