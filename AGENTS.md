# mechanical-video

## 无人工质检的制作目标（2026-11-09 用户纠正，优先于历史待审交付规则）

本次优化的对象是自动制作、主动修复与合格交付，不是继续替卷尺增加版本。用户不承担逐版看样、发现缺陷、批准修补或替团队关闭问题的职责。授权范围内，Director 和独立 QA 必须自行完成检查、局部修复及复验，不得用“请你看看”“等你确认”作为常规制作的出口。

新制作使用 v5 正式独立验收出口；`REVIEW_DELIVERY`、`NEEDS_REVIEW` 和制作命令退出成功均只是内部状态，不能标记工作流完成。完整连续视听能力必须在媒体制作前实测可用；缺能力归 Director 解决依赖，不以人工作为默认替代，也不先制作大量候选再让用户选。未解决的能力缺口意味着工作流尚未实现目标，不能靠阻断、测试数量或文档数量宣布自动化完成。

每集沿用唯一 controller record，真实派工、失败和修复次数持续保存。原题与最小动作小样合并到一次独立检查，实测时间线由独立 preflight 接收，成片由独立后审接收；最终交付只指向已经验收的文件，不在交付步骤重新生成媒体。版本改名、复制台账或换人不得绕过旧问题。待评审项必须带稳定 issue、唯一内部负责人、证据及复验要求，不能留下无人接手的“待用户确认”。既有资产保护、未知生成结果不重复提交、不新增付费生成和不自动发布的边界保留。

## Core constraints

Use `.venv/bin/python` or `uv run`. Project Skills live only in `.agents/skills/`; never install/update global Skills or modify other projects. Keep secrets in environment variables and out of logs. Preserve assets, providers, keys, source inputs, manifests, scenes, frames, queue records and rollback evidence.

Reusable printer templates live in `production-vault/printer-series-template/`, independently of episode directories and names. Treat this vault as permanent production infrastructure: exclude it from temporary-task, completed-episode and final-videos-only cleanup. Keep verified source CAD, occurrence caches, clean native scenes, common helpers, style references and versioned SHA-256 manifests there; keep episode-specific content in its episode workspace. Preserve candidate versus accepted status. Verified immutable snapshots must not be overwritten or have their protection cleared by cleanup. See [template storage and protection](docs/production-vault.md).

One consumer owns `worker.lock`. Hold `render.lock` for rendering or acceptance, release while idle; never parallelize heavy reconstruction. Default Eevee; optional Cycles uses Metal. Preserve the sandbox, existing concurrency configuration and root-session model; use the approved per-task agent model policy below. Restore only the same fingerprinted task's own incomplete render; source changes require a new archived task. Never edit archived renderer/audit/narration scripts or mix frames across renderer versions; reuse unchanged CAD caches.

On this macOS host, native Blender capture defaults to the executor-approved host GPU path. Use `.venv/bin/python -m mechanical_video.native_capture` for standalone inventories; it preflights Metal, holds render.lock, preserves inputs and never retries a crash. A restricted executor returning `GPU_ACCESS_REQUIRED` must route that same authorized task through scoped host-GPU execution before launching Blender, not first attempt a sandbox Blender run. Keep Codex/macOS security configuration unchanged; never turn unavailable capture into PASS. In-renderer capture still runs in the existing authorized GPU render process. See [native capture](docs/scene-fidelity.md#默认原生采集入口).

`python -m mechanical_video.cli demo` builds cached STEP/STL solids and renders two 720p/30fps five-second demo videos; `batch` queues ten themes, `worker --watch` consumes. The implemented generic CAD family is planetary reducers: reject unsupported products, never substitute a demo. Hidden image geometry/dimensions remain inferred. Vision defaults to `gpt-6-luna` (`VISION_MODEL` overrides), requires a configured endpoint; optional TripoSR is not a baseline dependency. Do not claim simulation, manufacturing accuracy, provider acceptance or media verification without evidence.

## Editorial and approval boundaries

The [six-episode printer plan](docs/printer-series-plan.md) is authoritative: preserve EP01/EP02, then XY transmission, four-corner Z lift, hotend/two cooling paths, bed support/first-layer gap. Do not revive old twelve-episode/eight-shot templates or resume held historical `remake plan/render/worker` jobs as new episodes. Preserve editorial holds.

Director checks current episode state, assets/hashes, dependencies and approval scope, and reads the relevant [approved style](docs/approved-video-style.md) and [production lessons](docs/production-lessons.md) before production. Children receive these relevant constraints in their task packet and load additional sections only when needed. Planning, local approval and production completion are distinct from formal acceptance.

### Reuse the established production baseline first

For all future episodes, Director must inspect the actual user-recognized episode scene and production sources before dispatching construction. The printer-series baseline is EP03's continuous-motion teaching scene and its subtitle/audio/editor workflow, with approval and unresolved QA scopes kept separate. Reuse the scene, CAD caches, stage, lights, materials, camera language, native output settings, motion helpers, subtitle placement and audio/encoding tools wherever applicable; adapt only the new mechanism, necessary teaching geometry, narration and timing. Do not rebuild a full-machine scene merely because full source CAD exists. EP04's concrete [reuse review](series/3d-printer-v2/episodes-current/EP04/ep03-reuse-review.md) is the starting example, not approval of its working animation.

Before Visual/Audio/Editor implementation, record the selected baseline paths/hashes, what is reused, the smallest episode-specific changes and any evidenced reason an existing component cannot serve. Pass that concrete reuse plan to the owners. Creative opening comparisons stay within the established visual language; they do not authorize a new production stack. Open existing assets first, create a new version for changes and preserve originals/archives. New mechanism facts and new media still require their own verification; reuse does not copy another episode's narration, approval or QA verdict.

Director and independent QA must compare early actual frames/clips with the baseline for appearance, framing, motion continuity, captions, sound and native resolution. Correct unintended drift within the authorized task before full rendering, without waiting for the user to identify it. Use the simplest clear, explicitly labeled teaching representation supported by source facts; do not expand into mesh reconstruction, visibility experiments or a replacement pipeline without first establishing why the mature approach cannot meet this episode's goal. Preserve existing issue IDs and repair counts when changing approach.

- Explain one visible mechanical cause through continuous teardown/reassembly, an early recognizable action/question and a retellable ending. Preserve orientation, spatial relationships and motion direction; avoid gratuitous cuts, text overload, visibility tricks or impact sounds. New episodes require Creative Director's comparison of at least three truthful, appealing, feasible openings, sequence purposes and causal payoffs before Script/Visual.
- Shape/connection anomalies require source STEP, occurrence mapping, transforms and independent exports before camera changes; never hide incorrect geometry. Keep inferred mechanics explicit.
- Compare actual affected local A/B clips before full rendering. Record approved hashes and scope. Approval plus an instruction to continue authorizes completing that episode without asking again; it does not authorize another episode, uploads, platform drafts, publish intent or publication.
- Lock approved assets, including narration. Voice/model precedence: episode approval, project default, skill default. Printer series uses `qwen3-tts-flash / Kai`, including future episodes; preserve approved EP01/EP02 audio. Other unconfigured tasks explicitly use `qwen3-tts-flash / Ethan`, overriding historical/skill defaults.
- Timing changes require foley, subtitles, labels, neighboring continuity and preparatory motion checks. Synthetic foley must be labeled as synthetic, never passed off as recordings. Follow the approved continuous style, not an artificial 90-second single take.

The accepted 15-second visual/sound reference is `series/3d-printer-v2/experiments/mechanical-hook-6e21ea58c8729117/mechanical-hook.mp4`, with hashes/scope in `series/3d-printer-v2/approved-style.json`. Preserve both and their archived sources. Its approval covers continuity and sound rhythm only, not full episodes, a season restart or Moon narration; it has no narration. Detailed style remains in the linked style document.

## Dispatch and efficient context

协作视觉证据默认采用缩略图与关键帧：每个回合最多 1 张联系图加 4 张关键帧；联系图最长边 1280、关键帧最长边 1024、单张默认不超过 300 KB。子代理只回传选定证据、时间码和结论，同一组图片不得在 follow-up 中重复发送；细节不足时才升级原图。

多 Agent 调度是硬预算：每个 session 默认只允许一个 Director，最多 4 次 `spawn_agent`，每个子代理最多 1 次 `followup_task`，总消息交接最多 20 次。达到任一上限后必须停止派工，主线程合并已有结果并继续可完成工作；不得通过换名字、重复 spawn 或循环等待绕过预算。等待必须绑定明确的完成事件，不能用轮询代替进展。图片超过本段限额时必须先压缩、拼图或改为文件路径/时间码，禁止继续传原图。

For video production, act as Director and use only necessary real available agents. Ordinary analysis/documentation stays with the main agent. Do not describe sequential role prompts as real delegation. Follow the [handoff workflow](.codex/agent-workflow.md) for role boundaries, dispatch, dependencies, version-impact review, issues and recovery; it is the detailed source of truth, not a requirement for every child to read every section.

Use one main-thread Director (recommended model Sol/low; do not change the active root-session model automatically). Visual and complex Editor work default to Sol/low; Terra handles creative expression and audience judgment. Research defaults to Luna for bounded fact extraction; route complex mechanical/source questions directly to explicit Sol/low without requiring a failed Luna attempt. Deterministic checks use scripts. Reuse the same ready production agents for related work; do not add a Director relay or instantiate all roles by default. See the workflow model table and stage gates. Never automatically raise Sol above the user-selected low effort; independent QA and acceptance thresholds remain unchanged.

Director supplies goal, approval scope, necessary inputs/hashes, exclusive output ownership, acceptance and stop conditions, relevant safety/evidence rules and exact reading pointers. Use independent context (`fork_turns="none"`) and the approved role/task model policy in [the handoff workflow](.codex/agent-workflow.md#模型分配与升级) for self-contained child work; reuse the original agent for related follow-ups. No concurrent writers or reverting others' work. Only launch ready tasks; parallelize independent preparation/fixed-input Visual and Audio, serialize heavy rendering. If agents are unavailable, report it and use the resumable pipeline without claiming independent QA.

Keep ordinary handoff summaries within 500 Chinese characters or equivalent concise prose, with full details in referenced files; never truncate critical defect evidence. Load current records and relevant sections first; do not default to reading whole growing historical logs. Wait on existing process/agent completion mechanisms instead of short sleep/status loops. Report stage changes, substantive evidence and exceptions, not unchanged waits. Check capabilities before work: if listening/playback/alignment is unavailable, collect useful new evidence once and hand off the exact unresolved question; do not repeatedly recreate reports or assets without new evidence.

## Production and acceptance

Use the [production preflight](docs/production-preflight.md) in the existing director-record for actual baseline comparison, capability/ready-input checks, early combined subtitle-label proofs and read-only storage budgeting before full render/resume. This adds execution evidence, not approval requests or a replacement acceptance system.

### Authorized continuation

Before first narration synthesis, validate the core action/pointing phrases against actual source facts and minimal visual evidence. Resolve unsupported actions in the draft before freezing audio; do not use layout fixes to mask a script/visual contradiction. Record whether each lock comes from explicit user approval, project constraints, a Director decision or an internal candidate; an internally authored timeline is not automatically user-approved. See the workflow section on pre-synthesis feasibility and lock provenance.

Director owns routine decisions within the existing authorization, including implementation details and evidence-based local A/B selection. Children report missing inputs to Director first. Consult existing approval records before asking the user; do not request the same authorization after a handoff. Preserve user-reserved preview approvals, locked assets, editorial holds and repair limits. See [continuation and question boundaries](.codex/agent-workflow.md#授权内推进与询问边界).

Missing perceptual evidence blocks the affected acceptance branch, not every reversible production step. With no known blocking defect or explicit hold, finish assembly/encoding and deliver a clearly marked review version with exact unresolved questions. Known P0/P1 and critical mechanical uncertainty still block dependent production. User acceptance of a delivered hash completes that user-delivery scope without fabricating independent QA scores or triggering repeated acceptance requests.

Narrated work requires Audio Director → Audio Production → independent Audio QA and Audio Appeal QA → Editor → both final-mix reviews → Video QA → independent Audience QA → Director. First Script supplies synthesizable text and estimated timing; measured audio then informs final subtitle/semantic timing. Visual-only changes retain approved narration and review affected final-mix evidence without resynthesis. Producers cannot perform their own independent acceptance.

- Narration subtitles: single line, at most 20 characters including all Chinese/English/digits/punctuation, one caption at a time; split long text into successive short captions. Time shots/captions from measured speech, natural pace and useful pauses, never slowed speech or looped shots to pad length. For new work, duration follows the complete mechanical explanation; there is no universal 90-second minimum. User instruction (2026-11-09): “视频不能为了凑时长，而把最关键的漏掉”. Preserve the title payoff, key contact/state transition and a complete action cycle before allocating time to teardown/reassembly. Missing or unreadable core causality blocks content acceptance regardless of length; do not pad with slowed speech, repeated motion or empty views. Necessary explanatory slow motion is allowed when it reveals new evidence. Preserve existing approved media and historical report results.
- Follow [video QA](docs/video-qa.md), [audio QA](docs/audio-qa.md) and [audience QA](docs/audience-qa.md) for applicable dimensions. Inspect actual media and record method/coverage; sampled frames, ordered static frames, real-time playback, listening and full decode are different evidence. Decode/ASR/PCM/TTS logs/local approval cannot replace perceptual acceptance. ASR discrepancies require corroboration; never resubmit uncertain provider requests automatically. Verified speech repairs regenerate only affected sentences into new versions, then remeasure, update captions/shots and recheck speech/mix.
- Keep generation status, user approval and QA separate. Missing perceptual, alignment or shot-correspondence evidence leaves relevant scores null. Known failures remain REWORK/FAIL; missing evidence may be NEEDS_REVIEW. Handoffs identify file/hash, shot/timecode (or unavailable), evidence and exact review question.
- Formal acceptance requires overall and technical ≥90, audience ≥85, audio technical ≥90, audio appeal ≥85, all established gates passed, no unresolved P0/P1 or critical mechanical/audiovisual uncertainty. Audio technical contributes once to the existing video audio dimension; audio appeal stays separate. Never invent scores or lower thresholds.
- Director routes evidenced issues to the unique owner; technical failures first, then creative weaknesses with Creative Director. Rebuild affected assets, review neighbors/global timing as impacted. New final files require same-version QA associations; independent QA must validate any reused evidence, never rewrite an old report's hash.
- Preserve issue IDs, versions, attempts, evidence and rollback. At most three automatic repair rounds per issue; stop a strategy after two rounds without measurable improvement. New names/owners do not reset counts. Missing capabilities stop the affected branch, not unrelated authorized work.

For data-driven work use [audience growth](docs/audience-growth.md): record primary audience goal, new visible information, causal payoff, locked assets and smallest testable change. Separate retention, likes, sharing/saving, discussion and follow intent with timecoded evidence; predictions are not measured growth. Platform observations require post ID/type, publication/observation times, window and version. Retention locates inspection windows; inspect the matching actual film before attributing causes. Account totals, post totals and different media types are not interchangeable. Packaging changes do not authorize publication.

## Tools and validation

Prefer available `codegraph_*` tools for structural questions (context then explore; symbol search/callers/callees/impact/files). Trust AST results rather than repeating grep. Use native search for literal text or if tools are unavailable. If the server reports uninitialized, ask before `codegraph init -i`.

For ego-browser use `/Users/lmj/.local/bin/ego-browser`, JavaScript via `nodejs -e`; no heredocs/herestrings or shell wrappers. Preserve sandbox and existing allow rules.

Run applicable unittest discovery for code changes. Production CAD/video changes additionally need actual CAD generation, independently exported valid positive-volume solids, render, ffprobe and full FFmpeg decode. Record native versus encoded resolution/frame rate separately; technical completion is not perceptual acceptance. Documentation/configuration and read-only audit-tool changes need their applicable tests, links/scope/TOML checks and `git diff --check`, not unrelated renders or provider calls. Append current validation to [validation.md](docs/validation.md), preserving historical records.

Read-only usage audit: `.venv/bin/python scripts/audit_token_usage.py <session.jsonl-or-directory> --format json|markdown`. See [audit usage and baseline](docs/token-usage-audit.md). Report cached/noncached inputs, outputs and coordination separately; do not equate cumulative tokens with cost or promise savings before comparable real-task measurement.


### 2026-11-09 返工预防执行修复

新制作遵循 [返工预防](docs/production-rework-prevention.md)：Director 冻结原题与必答机制，先独立审查可解码局部小样的输入—接触/传动—输出及脚本对应，未解决 P0/P1 不扩为整片。新记录 v4；自定义配音/全片渲染/交付命令走 `python -m mechanical_video.production_run --record ... --stage ... -- command`，完整 argv 绑定 execution、源文件绑定 assets。不可用归档脚本直接运行绕过；旧版本问题和计数保留。文件/几何 PASS 与局部认可均不替代题意、因果或感官验收；不要求用户来发现制作前可定位的缺陷。


### 渲染前检查实际姿态（2026-11-09）

新渲染器必须在第一次出图前，用正式制作同一个 pose 回调逐帧运行 [场景预检](docs/pre-render-scene-checks.md)，检测关键部件出框/过小、指定表面遮挡、连接锚点脱开和缺失运动。静态保存场景不能代替自定义 pose 求值。v4 full-render/delivery 额外要求绑定同版 source/renderer/policy、完整 requirement 和逐帧覆盖的 `assets.scene_preflight`。缺失或失败先阻断，不等用户发现；不把几何 PASS 宣称为完整视觉/因果理解。保留在制与归档脚本，接入独占新版本；当前真实 Blender 回归状态见 validation.md。


### 动作声明与逐帧状态核对（2026-11-09）

本次卷尺V7复核已确认开头/结尾动作与字幕相反或错位；执行[动作声明核对](docs/caption-action-alignment.md)，v4 full-render/delivery 必须绑定 action_alignment、action_alignment_policy、motion、timeline 及原题requirement。门禁会重算，不信单独PASS；“回收”却拉出、“解除”却加锁不能交给用户发现。场景预检目标必须包含穿壳连片及关键接触件，不能只测整个机构/可见按钮。新增检查不能倒填为旧V7已经通过；原片与旧批准记录保留。


### 主动修复闭环（2026-11-09）

执行[多Agent主动发现、修复与复验](docs/agent-repair-loop.md)。Director在每次已授权制作内主动安排前检、小样和后审，不等待用户指出缺陷；根据实际失败证据交唯一所有者修复，回传后重跑失败检查并交独立评审复验。v4的P0/P1关闭状态必须有稳定issue_id、非空required_checks及同版resolution（对应issue_id、verified、不同producer/reviewer、完整asset_fingerprints、覆盖全部必查项的checks_covered和有效evidence），否则BLOCKED。制作完成不等于修复关闭；上一版本问题同样保留。真实感官能力不足不填分，不重复派同能力代理。当前没有无人值守内容修复调度器，不能将交接检查或渲染worker称为自动内容闭环。


### 持久化修复调度 v5（2026-11-09）

新制作入口采用 [repair-controller](docs/repair-controller.md)，通过 next → 真实会话派工 → claim → complete → 独立复验推进；resume 不重复未知命令。配音、全片、交付要求 v5 执行记录；历史 v4 的原判定保留。统一事件时间线必须来自实测语音并绑定字幕、motion、foley。当前仅完成简化代理的跨题材技术闭环，原片与连续视听验收仍未完成，不能标记系统整体完成。
