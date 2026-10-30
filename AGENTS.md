# mechanical-video

All Skills belong in this project's `.agents/skills/`. Never install/update user or global Skills. Use `.venv/bin/python` or `uv run`. Do not modify other projects.

## Pipeline

`python -m mechanical_video.cli demo` builds cached STEP/STL solids and renders two verified 720p 30fps five-second videos. `batch` enqueues all ten themes; `worker --watch` processes continuously. Only one consumer may own worker.lock. Hold render.lock during rendering or acceptance and release it while idle so acceptance can run alongside a watcher. Never run parallel heavy reconstruction models. Default Eevee; optional Cycles must use Metal. Preserve models, source inputs, manifests, scenes, frames, and queue records for reuse and resume.

Hidden geometry and dimensions from images must remain explicitly inferred. The implemented CAD family is planetary reducers; reject unsupported products rather than substituting the demo. Vision defaults to gpt-6-luna (VISION_MODEL can override it) and requires a configured provider endpoint. TripoSR is optional and must not become a baseline dependency. Do not claim simulation, manufacturing accuracy, live provider acceptance, or video verification without evidence.

## Production direction and approval

Before production, read [approved visual style](docs/approved-video-style.md) and [production lessons](docs/production-lessons.md), then inspect the episode state, accepted assets, approval scope, editorial holds and dependencies.

- Aim for audience understanding and interest: reveal a recognizable action and question early, develop mechanical causes through the middle, and end with one insight viewers can retell. Advance through continuous action, not frequent cuts, text overload or impact sounds. For a new episode, Creative Director compares at least three truthful, visually appealing, feasible openings before Script and Visual; record the selected opening and each sequence's purpose.
- If a part's shape or connection looks wrong, inspect source CAD, occurrence mappings and independent exports before adjusting the camera. Never conceal incorrect geometry with framing. Keep inferred mechanics explicit.
- Validate locally before a full render: compare a few opening candidates and actual affected A/B clips. Record approved asset hashes and exact scope. Once the user approves local work and instructs continuation, complete that episode without asking again; approval does not extend to other episodes or publication. Preserve editorial holds. Uploads, platform drafts and publication require explicit authorization.
- Lock approved assets. Voice/model precedence is episode-specific user approval, then project default, then skill default. EP02 retains its approved Kai narration; visual-only changes do not regenerate speech.
- When action or camera timing changes, check foley, subtitles, labels and neighboring continuity. Retain necessary preparatory motion across excerpt boundaries. Integrate local changes into one frozen renderer; never mix frames across renderer versions. The same fingerprinted task may resume its own incomplete render.
- Record generation status, user approval scope and QA status separately. A complete film may be supplied clearly labeled NEEDS_REVIEW with exact unresolved gates; only all-gates-passed work may be called formally accepted. Local approval is not a QA score. Missing listening or real-time viewing evidence leaves the relevant scores null.

## Multi-Agent Dispatch

For video production, the main agent acts as Director. Use real available Codex sub-agents only for necessary roles; never describe sequential role prompts as spawned agents. If unavailable, report the limitation and use the resumable pipeline. Give each child explicit inputs, outputs, acceptance criteria and exclusive file ownership; record identity, task, result and evidence. No concurrent writers to the same file. Parallelize independent preparation and fixed-input Visual/Audio work; serialize heavy rendering under render.lock. Editor waits for required assets and QA for actual output. Preserve assets, skills, providers and keys.

Roles: Research owns references and uncertainty; Creative Director owns narrative direction; Script owns narration and shot plans; Visual owns CAD, animation and renders; Audio owns existing audiogen production; Editor owns assembly, captions and timing. Growth Analyst prepares truthful platform packaging and distinguishes predictions from actual metrics. Independent QA reviews actual output and reference evidence. Report stage changes, substantive progress and exceptions; do not repeat unchanged render-wait updates.

For narrated production, use distinct Audio Production and Audio QA agents. Audio Director first prepares per-segment intent, key terms, emphasis and synchronization from approved script/timing, with natural documentary delivery. Audio Production uses the approved voice/model and only supported controls. Order: Audio Director → Audio Production → independent Audio QA and Audio Appeal QA → Editor → both final-mix audio reviews → Video QA → independent Audience QA → Director. For visual-only revisions, retain approved narration and review the affected final mix without resynthesis.

Audio QA records actual speech, ASR, timing and sound evidence rather than TTS logs. Missing forced alignment, listening/audio understanding or shot correspondence stays unverified; critical omissions, misreadings or severe audiovisual mismatch block formal acceptance. ASR mismatches are candidates requiring corroboration, not proof of mispronunciation. Do not automatically resubmit uncertain TTS/ASR requests. For verified fixable speech issues, regenerate only affected sentences in a new version, retain originals, remeasure, update captions/shots and recheck speech and final mix.

## Quality gates and repair

Follow [video QA](docs/video-qa.md); `python -m mechanical_video.video_qa` provides project QA tooling, not automatic perceptual acceptance. Inspect actual video, audio, captions and timeline. Record coverage and method: sampled frames, ordered static frames and real-time playback are different evidence; sampled frames never establish frame-by-frame review.

- Formal acceptance requires overall and technical scores ≥90, audience ≥85, audio technical ≥90 and audio appeal ≥85, every established gate passed, and no unresolved P0/P1 or critical mechanical/audiovisual uncertainty. Never invent missing scores or lower thresholds. Audio QA contributes once to the existing video audio dimension; keep audio appeal separate.
- Independent Audience QA assesses opening, pacing, memorable visuals, knowledge, discussion value and ending with timecoded evidence. Missing perceptual evidence stays unverified; technical decode and user local approval cannot substitute for it or measured platform engagement.
- Director routes evidenced issues to Research, Script, Visual, Audio or Editor as appropriate. Fix technical failures first, then creative weaknesses with Creative Director and the relevant owner. Rebuild only affected shots and downstream assets; rerun applicable QA on the actual new version, neighbors and global timeline where impacted.
- Preserve versions, evidence, scores and rollback paths. Track attempts per issue: at most three automatic repair rounds; stop a strategy after two rounds without measurable improvement. If tooling cannot repair or verify the issue, mark NEEDS_REVIEW and identify the missing capability; never imply an automated loop ran.
- Human-review handoffs identify shot ID, timecode, evidence and exact unresolved question; explicitly say when shot/timecode is unavailable. Director requires verified results before formal acceptance and preserves prior approval scope and holds.

## CodeGraph

Prefer configured `codegraph_*` tools for structural queries: context then explore; search for symbols, callers/callees for edges, impact for change scope, files for inventory. Trust AST results rather than repeating grep. Use native searches for literal text. If the server reports not initialized, ask before `codegraph init -i`. No CodeGraph tools were exposed during initial implementation; native reads are the fallback.

## ego-browser

Use `/Users/lmj/.local/bin/ego-browser`, JavaScript via `nodejs -e`, never heredocs/herestrings or shell wrappers. Preserve sandbox configuration and existing allow rules.

New tasks archive the renderer, audit and narration scripts under their video directory. Their content fingerprints determine the task ID. Never edit archived scripts or mix frames across renderer versions. Re-enqueue after source changes; reuse the unchanged CAD cache.

## Validation

For code/CAD/video production changes, run applicable unittest discovery, actual CAD generation, render, ffprobe and full FFmpeg decode. Documentation-only changes require link/scope checks and `git diff --check`, not new renders or provider calls. Record current results in docs/validation.md. CAD must contain independently exported positive-volume valid solids. Technical video completion requires H.264, expected dimensions, duration and full decode; record native render resolution/frame rate separately from encoded resolution/frame rate. This does not establish perceptual acceptance. Keep secrets in environment variables and out of logs.

## 配音与字幕规范

- 项目内视频 QA 可用 `python -m mechanical_video.video_qa`；遵守 `docs/video-qa.md` 中的证据限制，未验证维度不可视为通过。

- 音色：优先使用本集用户批准的音色与模型（EP02 为 Kai）；无本集批准配置时，项目默认 `qwen3-tts-flash / Ethan`，显式指定 Ethan，覆盖技能中的 Roy 默认值。
- 字幕：旁白字幕始终单行，每条最多 20 个字符，中文、英文、数字及标点均计数；超长内容拆成连续短句，不换行显示，同一时刻只显示一条。
- 时长：正式配音拆解视频实际时长不得少于 90 秒。用户明确要求的短片、测试或预览除外。
- 文案：默认面向普通观众讲清机械原理，以问题和因果关系串联拆解；避免流水账式报零件名、空泛宣传及反复免责声明。推测结构集中说明，画面持续保留提示。
- 节奏与同步：按短句使用本集批准配置（无配置时 Ethan）生成配音，用实测音频时长安排字幕和镜头。优先自然语速与合理展示停顿，不通过明显放慢语音或循环镜头凑时长。
- 验收：交付前检查音色配置、全部字幕的单行与字符限制、音画对应关系，以及实际时长 ≥90 秒；完成音视频全片解码并记录结果。

## 已确认的拆解视觉风格（2026-10-28）

- 用户认可的是连续版：`series/3d-printer-v2/experiments/mechanical-hook-6e21ea58c8729117/mechanical-hook.mp4`，原话“就是这种感觉”。后续制作先读 `docs/approved-video-style.md`。
- 连续动作优先：保持同一机构的空间关系、朝向和运动方向；外壳逐渐打开，镜头连续靠近传动，再沿线材移向热端。不要为制造刺激而频繁跳切、突然换景别、隐藏零件或重置装配状态。
- 机械爽感来自看得清的动作与因果关系；近景揭示结构，让观众有时间辨认。长片可有必要的镜头转换，但要维持空间和动作衔接，不机械扩写成90秒的一镜到底。
- 声音连续跟随机械动作，使用克制的转动、滑动与接合拟音；取消每次换画面都加冲击音。合成拟音不得冒充实录。
- 此次确认只涵盖15秒测试的视觉连贯性与声音节奏，不代表批准完整EP01、整季成片或Moon旁白。该测试无旁白；后续配音不能重新压过画面或退回逐句拼接加长停顿的节奏。
- 保存参考成片、帧、场景、源文件归档及哈希；`series/3d-printer-v2/approved-style.json` 是本次确认的机器可读记录。不得覆盖参考视频或修改其归档脚本。
