# Read-only token usage audit

Run from the project root, using existing session files or directories:

```sh
.venv/bin/python scripts/audit_token_usage.py /path/to/session.jsonl --format markdown
.venv/bin/python scripts/audit_token_usage.py /path/to/sessions --format json
.venv/bin/python scripts/audit_token_usage.py /path/to/sessions --root-session REAL_THREAD_ID \
  --production-record /path/to/director-record.json --format json
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
  editing, or qa. The optional `--production-record` also reads explicitly recorded
  `workflow_events` with timezone-qualified timestamp, thread_id, type and phase;
  see [ready handoff and phase recording](production-handoff.md). Existing logs without
  markers stay unattributed; prose is never classified into phases. First snapshots
  are unattributed because their earlier history is unknown. Gaps/resets mark phase
  deltas incomplete; unknown fields stay null.

Schema v3 retains existing totals and adds per-thread `copy_diagnostics` (selected
SHA256, snapshot count and warnings for each supplied copy), plus team-local
duplicate/conflicting-thread/missing-snapshot diagnostics. Top-level duplicate
counts still cover the whole input directory, so use team diagnostics for a
selected root. Conflicts leave phase completeness false even for the selected copy.
`tool_output_sizes` separates structured image payload characters, text characters,
image count and unclassified/serialization characters; none are token estimates.
Image URLs/data and message bodies are never exported.

External phase markers never rewrite session logs. Same-thread overlapping or
unpaired end markers are input errors; unclosed/out-of-log markers or unmatched
threads restrict coverage. Snapshot intervals crossing a recorded boundary stay
unattributed rather than being assigned to either phase. Known missing snapshots
also leave their subsequent delta unattributed. Record stage events and outcome
metrics in the existing director record; this is not an automatic scheduler.

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

## 团队选择、比较与本次基线

```sh
.venv/bin/python scripts/audit_token_usage.py /explicit/log/directory \
  --root-session REAL_THREAD_ID --format json
.venv/bin/python scripts/audit_token_usage.py --compare before.json after.json
```

根选择仅使用明确提供的日志，按 `thread_id`、`session_meta.id` 及父线程元数据选子树；共享 `session_id` 不合并不同线程。guardian 默认独立列出，不计入制作团队；指定根时只列该团队的 guardian。去重按真实线程，缺子日志、冲突副本、计数重置仍限制覆盖，不用 spawn 结果替代父子关联。

增加声明角色/最后观察到的模型汇总（不是逐轮模型用量归因）、协调对象计数和有成对时间戳的实际等待时长分布；缺时间戳不猜测。只解析协调 target/recipient 标识、spawn 结果 ID、元数据和用量白名单，不输出消息正文、加密字段、图片、参数或工具输出正文。模型和 target 只接受有限标识格式。

比较分别报告缓存输入、非缓存输入、输出及协调的原值和差值；团队覆盖不全明确提示。只有两份报告均有完整已链接日志覆盖，且显式 `comparison_context: {scope, quality}` 非空且相同，才计算变化率。该元数据须来自可比实际任务与 QA，不由工具推断；不由累计 token 推算费用。

[本次分析的脱敏冻结基线](token-usage-analysis-baseline-20261102.json)来自已结束的分析根线程 `01a19bce-951e-7670-bcc3-6d3257b6f612`，不是正在执行的实现会话，也不是完整 EP06 制作团队统计。记录了三个历史全片版本及其哈希、被拒的床板/工具头相交 P1、最终感官 QA 缺口；只读现有记录，未重查或渲染影片。旧的 10 月基线保留。

下一次已授权实际制作在既有 director-record 同时记录首次交付耗时、重大返工、全片重渲次数、用户发现的缺陷、验收完整度及任务范围，再保存同口径审计。当前只能证明工具行为与测试通过，实际制作节省量尚未测量。
