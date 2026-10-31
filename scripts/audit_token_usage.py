"""Read-only Codex JSONL usage audit; stdout contains metadata, never message bodies."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
PHASES = {"research", "creative", "script", "visual", "audio", "editing", "qa", "unattributed"}
COORDINATION = ("spawn_agent", "send_message", "followup_task", "wait_agent", "sleep")


def object_value(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            pass
    return {}


def token_value(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def normalize_usage(raw):
    values = {key: token_value(raw.get(key)) for key in FIELDS}
    inp, cached, out = (values[k] for k in FIELDS[:3])
    values["noncached_input_tokens"] = inp - cached if inp is not None and cached is not None and cached <= inp else None
    # Reasoning is a subset of output in these logs, not an extra charge to add.
    values["total_tokens"] = inp + out if inp is not None and out is not None else None
    return values


def audit_file(path):
    warnings = Counter()
    calls = Counter()
    usage = None
    previous = None
    phase = "unattributed"
    phases = {}
    snapshots = resets = output_chars = outputs = 0
    session_id = parent_id = None
    call_names = {}
    spawned_ids = set()
    seen_events = set()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for line in stream:
            digest.update(line)
            try:
                event = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                warnings["malformed_lines"] += 1
                continue
            if not isinstance(event, dict):
                warnings["nonobject_lines"] += 1
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            kind = event.get("type")
            subtype = payload.get("type")
            if kind == "session_meta":
                candidate = payload.get("id") or payload.get("session_id")
                if isinstance(candidate, str):
                    if session_id and session_id != candidate:
                        warnings["conflicting_session_ids"] += 1
                    session_id = candidate
                source = object_value(payload.get("source"))
                spawn = object_value(object_value(source.get("subagent")).get("thread_spawn"))
                parent = spawn.get("parent_thread_id") or payload.get("parent_thread_id")
                if isinstance(parent, str):
                    parent_id = parent
            if kind == "event_msg" and subtype == "phase_start":
                # Only explicit structured labels; never infer a stage from user/agent prose.
                label = payload.get("phase")
                phase = label if isinstance(label, str) and label in PHASES else "unattributed"
            if kind == "event_msg" and subtype == "token_count":
                info = object_value(payload.get("info"))
                raw = info.get("total_token_usage")
                if not isinstance(raw, dict):
                    warnings["missing_usage_snapshots"] += 1
                    continue
                current = normalize_usage(raw)
                snapshots += 1
                if current["noncached_input_tokens"] is None:
                    warnings["missing_or_invalid_cache_counts"] += 1
                if current["input_tokens"] is None or current["output_tokens"] is None:
                    warnings["missing_core_usage_counts"] += 1
                reset = previous is not None and any(
                    current[k] is not None and previous[k] is not None and current[k] < previous[k]
                    for k in FIELDS
                )
                if reset:
                    resets += 1
                    warnings["counter_resets_latest_epoch_only"] += 1
                # Deltas, not sums of cumulative snapshots. A reset/gap cannot be stage-attributed.
                bucket = phase if previous is not None and not reset else "unattributed"
                entry = phases.setdefault(bucket, {k: 0 for k in current})
                for key in current:
                    now = current[key]
                    before = previous[key] if previous else 0
                    if now is None or before is None or reset:
                        warnings["unattributed_usage_gaps"] += 1
                        entry[key] = None
                        continue
                    if entry[key] is not None:
                        entry[key] += now - before
                previous = current
                usage = current
            if kind != "response_item":
                continue
            if subtype in ("function_call", "custom_tool_call", "function_call_output", "custom_tool_call_output"):
                event_id = payload.get("call_id") or payload.get("id")
                identity = (subtype, event_id)
                if event_id and identity in seen_events:
                    continue
                if event_id:
                    seen_events.add(identity)
            if subtype in ("function_call", "custom_tool_call"):
                name = payload.get("name")
                if not isinstance(name, str):
                    warnings["unnamed_tool_calls"] += 1
                    continue
                calls[name] += 1
                call_names[payload.get("call_id") or payload.get("id")] = name
            elif subtype in ("function_call_output", "custom_tool_call_output"):
                output = payload.get("output", "")
                output_chars += len(output) if isinstance(output, str) else len(json.dumps(output, ensure_ascii=False))
                outputs += 1
                name = call_names.get(payload.get("call_id"), "").split("__")[-1].split(".")[-1]
                if name == "spawn_agent":
                    child = object_value(output).get("agent_id")
                    if isinstance(child, str):
                        spawned_ids.add(child)
    if usage is None:
        warnings["no_usage"] += 1
    if not session_id:
        warnings["missing_session_id"] += 1
        session_id = "sha256:" + digest.hexdigest()
    coordination = {name: sum(n for tool, n in calls.items() if tool.split("__")[-1].split(".")[-1] == name)
                    for name in COORDINATION}
    return {
        "session_id": session_id, "parent_session_id": parent_id,
        "sha256": digest.hexdigest(), "usage_latest": usage,
        "usage_snapshots": snapshots, "counter_resets": resets,
        "phases": phases, "tool_calls": dict(sorted(calls.items())),
        "phase_deltas_complete": snapshots > 0 and not resets and not any(warnings.values()),
        "coordination": coordination, "tool_output_chars": output_chars,
        "tool_output_events": outputs, "spawned_session_ids": sorted(spawned_ids),
        "warnings": {key: value for key, value in warnings.items() if value},
    }


def audit_paths(inputs):
    paths = set()
    for value in inputs:
        path = Path(value)
        if not path.exists():
            raise ValueError("Input path does not exist")
        if path.is_dir():
            paths.update(p.resolve() for p in path.rglob("*.jsonl") if p.is_file())
        else:
            paths.add(path.resolve())
    if not paths:
        raise ValueError("No JSONL files found")
    sessions = {}
    duplicates = conflicts = 0
    for path in sorted(paths):
        record = audit_file(path)
        key = record["session_id"]
        if key in sessions:
            duplicates += 1
            old = sessions[key]
            if old["sha256"] != record["sha256"]:
                conflicts += 1
                # Prefer the copy with more snapshots; still flag the ambiguity, never add copies.
                if record["usage_snapshots"] > old["usage_snapshots"]:
                    sessions[key] = record
                sessions[key]["warnings"]["conflicting_session_copies"] = 1
        else:
            sessions[key] = record
    teams = []
    for root_id, root in sorted(sessions.items()):
        if root["parent_session_id"] in sessions:
            continue
        members = {root_id}
        while True:
            children = {sid for sid, rec in sessions.items() if rec["parent_session_id"] in members}
            expanded = members | children
            if expanded == members:
                break
            members = expanded
        missing = set()
        unknown_spawns = 0
        for sid in members:
            rec = sessions[sid]
            missing.update(child for child in rec["spawned_session_ids"]
                           if child not in members or sessions[child]["parent_session_id"] != sid)
            known = {child for child in members if sessions[child]["parent_session_id"] == sid}
            unknown_spawns += max(0, rec["coordination"]["spawn_agent"] - len(known))
        valid = len(members) > 1 and all(not sessions[s]["warnings"] for s in members)
        complete = valid and not missing and not unknown_spawns and root["parent_session_id"] is None
        totals = None
        if len(members) > 1:
            totals = {}
            for field in (*FIELDS, "noncached_input_tokens", "total_tokens"):
                values = [sessions[s]["usage_latest"].get(field) if sessions[s]["usage_latest"] else None for s in members]
                totals[field] = sum(values) if all(v is not None for v in values) else None
        teams.append({"root_session_id": root_id, "members": sorted(members),
                      "coverage": "linked_logs_complete" if complete else "incomplete",
                      "missing_or_unverified_children": sorted(missing),
                      "unresolved_spawn_calls": unknown_spawns, "reported_session_sum": totals})
    assigned = {sid for team in teams for sid in team["members"]}
    return {"schema_version": 1, "sessions": list(sessions.values()), "teams": teams,
            "unassigned_session_ids": sorted(set(sessions) - assigned),
            "duplicate_session_copies": duplicates, "conflicting_session_copies": conflicts,
            "notes": ["Cumulative snapshots are not added; latest epoch only after a reset.",
                      "Reasoning is reported separately and is not added to output.",
                      "Team sums include only metadata-linked supplied sessions; fork history may overlap.",
                      "Cyclic parent links remain unassigned and are never aggregated.",
                      "Complete means supplied linked-log coverage, not complete billing coverage.",
                      "Tool output lengths count both tool formats; tool-call bodies are not interpreted.",
                      "No prices, message bodies, arguments, or tool output bodies are exported."]}


def markdown(report):
    lines = ["# Token usage audit", "", "| Session | Input | Cached | Noncached | Output | Reasoning subset | Resets |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    def cell(value):
        return "unknown" if value is None else str(value)
    for rec in report["sessions"]:
        usage = rec["usage_latest"] or {}
        values = [usage.get(k) for k in ("input_tokens", "cached_input_tokens", "noncached_input_tokens", "output_tokens", "reasoning_output_tokens")]
        lines.append("| " + " | ".join([rec["session_id"], *map(cell, values), str(rec["counter_resets"])]) + " |")
        lines.extend(["", "Coordination: " + json.dumps(rec["coordination"], sort_keys=True),
                      f"Tool output: {rec['tool_output_chars']} characters / {rec['tool_output_events']} events.",
                      "Warnings: " + json.dumps(rec["warnings"], sort_keys=True),
                      "Phases: " + json.dumps(rec["phases"], sort_keys=True),
                      f"Phase deltas complete: {rec['phase_deltas_complete']}.", ""])
    lines += ["## Linked sessions", "", "```json", json.dumps(report["teams"], indent=2), "```", ""]
    lines += [f"Duplicate session copies: {report['duplicate_session_copies']}; conflicting copies: {report['conflicting_session_copies']}.",
              "Unassigned sessions: " + json.dumps(report["unassigned_session_ids"]), ""]
    lines.extend("- " + note for note in report["notes"])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="JSONL session file(s) or directories (recursive)")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    try:
        report = audit_paths(args.inputs)
    except (OSError, ValueError):
        # Do not echo paths, exception text, or malformed log contents.
        print("Unable to read audit inputs; check paths and permissions.", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else markdown(report), end="\n" if args.format == "json" else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
