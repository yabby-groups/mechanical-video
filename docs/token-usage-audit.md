# Read-only token usage audit

Run from the project root, using existing session files or directories:

```sh
.venv/bin/python scripts/audit_token_usage.py /path/to/session.jsonl --format markdown
.venv/bin/python scripts/audit_token_usage.py /path/to/sessions --format json
```

Multiple inputs are accepted; directories are searched recursively for JSONL files.
The script reads inputs and writes only to stdout. It does not call providers,
change logs, create sessions, or export message/argument/tool-output bodies.
Errors omit input paths and raw log contents. Redirect stdout explicitly to save a report.
Empty inputs or unreadable paths exit 2; malformed lines are counted as warnings,
so inspect warnings and coverage rather than treating exit 0 as proof of complete data.

## Accounting boundaries

- Use the latest cumulative `event_msg/token_count` snapshot per session, never
  sum cumulative snapshots or add the parallel `token_usage_record` stream.
  Counter decreases are flagged; the latest epoch is reported, not a fabricated
  all-epoch total. Missing counts stay unknown.
- Noncached input is input minus cached input only when both are valid.
  Reasoning is a reported subset of output, not an extra term in total tokens.
- Count both function and custom tool calls/outputs. Output length is characters,
  not tokens. Namespaced tool names are retained; coordination counts normalize
  their final component. Calls hidden inside an orchestration tool body are not
  parsed, inferred, or separately counted.
- Deduplicate supplied paths and copies by session identity. Conflicting copies
  are flagged and the copy with more usage snapshots is selected (ties use the
  first resolved path); totals are not added. Missing identity uses a content hash.
- Team sums require parent metadata linking supplied logs. Spawn-result IDs help
  identify missing children, but do not themselves prove parentage. Missing logs,
  unresolved spawn calls, orphaned parents, or record warnings leave coverage
  incomplete. Cyclic parent relationships remain unassigned.
- `linked_logs_complete` means coverage of observed linked logs only. Forked
  history can overlap and unobserved activity may be absent: reported session sums
  are not verified account usage or bills. No prices or monetary savings are calculated.
- Phase deltas require explicit structured `event_msg` metadata with
  `type: phase_start` and a `phase` of research, creative, script, visual, audio,
  editing, or qa. No production emitter is added or required. Existing logs without
  markers stay unattributed; prose is never classified into phases. First snapshots
  are unattributed because their earlier history is unknown. Gaps/resets mark phase
  deltas incomplete; unknown fields stay null.

## Frozen historical baseline

[Machine-readable baseline](token-usage-baseline.json) contains source SHA-256,
session identities, counts and coverage, without raw content. It covers two root
session files sampled on 2026-10-31, not their complete agent trees.

| Session | Input | Cached input | Noncached input | Output | Spawn / message / follow-up | Wait / sleep |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `01a18b7f-9b1c-70f1-af2a-c83fc25f8182` | 71,022,053 | 70,583,168 | 438,885 | 93,579 | 12 / 81 / 33 | 26 / 199 |
| `01a18d14-1e66-7b93-8ce0-8cf6d4bf4a5e` | 18,172,400 | 17,937,280 | 235,120 | 72,784 | 7 / 13 / 5 | 8 / 0 |

Both sessions have no observed counter reset. Including custom outputs gives
2,215,640 and 1,881,221 tool-output characters respectively; the earlier manual
sample counted function outputs only and therefore understated this diagnostic.
There are no explicit phase markers; all usage remains unattributed.

For the next already-authorized comparable task, record task scope, actual
deliverables, QA completeness and the same token/coordination metrics. Compare
noncached input and output separately from cached traffic. Document differences
in scope and available evidence before interpreting savings. The instruction
rewrite is static optimization, not proof of measured production savings.

## Workflow walkthrough (static, not production acceptance)

| Scenario | Required route | Avoided repetition / retained gate |
| --- | --- | --- |
| New episode | Director checks source, authorization and capabilities; Creative Director compares three openings, then required production roles | Only ready tasks start; natural measured narration, independent QA and full final-file evidence remain required |
| Visual-only local revision | Lock baseline/audio; Visual tests affected A/B; Editor handles changed timing; affected independent QA associates new final hash | No Audio synthesis chain or new-episode opening exercise; unchanged evidence needs corresponding QA verification |
| Approved continuation | Check approval scope/current state; assign remaining work with self-contained inputs | No repeated approval request or broad historical reread; new final artifact still needs its own QA associations |
| Render recovery | Verify fingerprint, lock ownership, old writer stopped and existing output; resume only matching unfinished task | No new render version mixed into old frames, no busy status loop, no automatic Metal/crash retry |
| Missing listening capability | Collect available useful evidence, report file/hash, interval or unavailable, precise question and next reviewer | Stop repeated QA/report generation; audio-related dimensions stay null, known defects remain FAIL/REWORK |

Detailed ownership and version-impact rules remain in the
[handoff workflow](../.codex/agent-workflow.md). Core constraints and acceptance
thresholds remain in [AGENTS.md](../AGENTS.md). No model, concurrency, publication,
provider, media asset or production scheduler is changed by this optimization.
