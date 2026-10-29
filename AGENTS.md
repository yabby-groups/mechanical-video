# mechanical-video

All Skills belong in this project's `.agents/skills/`. Never install/update user or global Skills. Use `.venv/bin/python` or `uv run`. Do not modify other projects.

## Pipeline

`python -m mechanical_video.cli demo` builds cached STEP/STL solids and renders two verified 720p 30fps five-second videos. `batch` enqueues all ten themes; `worker --watch` processes continuously. Only one consumer may own worker.lock. Hold render.lock during rendering or acceptance and release it while idle so acceptance can run alongside a watcher. Never run parallel heavy reconstruction models. Default Eevee; optional Cycles must use Metal. Preserve models, source inputs, manifests, scenes, frames, and queue records for reuse and resume.

Hidden geometry and dimensions from images must remain explicitly inferred. The implemented CAD family is planetary reducers; reject unsupported products rather than substituting the demo. Vision defaults to gpt-6-luna (VISION_MODEL can override it) and requires a configured provider endpoint. TripoSR is optional and must not become a baseline dependency. Do not claim simulation, manufacturing accuracy, live provider acceptance, or video verification without evidence.

## CodeGraph

Prefer configured `codegraph_*` tools for structural queries: context then explore; search for symbols, callers/callees for edges, impact for change scope, files for inventory. Trust AST results rather than repeating grep. Use native searches for literal text. If the server reports not initialized, ask before `codegraph init -i`. No CodeGraph tools were exposed during initial implementation; native reads are the fallback.

## ego-browser

Use `/Users/lmj/.local/bin/ego-browser`, JavaScript via `nodejs -e`, never heredocs/herestrings or shell wrappers. Preserve sandbox configuration and existing allow rules.

New tasks archive the renderer, audit and narration scripts under their video directory. Their content fingerprints determine the task ID. Never edit archived scripts or mix frames across renderer versions. Re-enqueue after source changes; reuse the unchanged CAD cache.

## Validation

Run unittest discovery, actual CAD generation, render, ffprobe and full FFmpeg decode. Record current results in docs/validation.md. CAD must contain independently exported positive-volume valid solids. Video completion requires H.264, expected dimensions, duration and full decode. Keep secrets in environment variables and out of logs.

## 配音与字幕规范

- 音色：本项目默认使用 `qwen3-tts-flash / Ethan`；调用时显式指定 Ethan，覆盖技能中的 Roy 默认值。
- 字幕：旁白字幕始终单行，每条最多 20 个字符，中文、英文、数字及标点均计数；超长内容拆成连续短句，不换行显示，同一时刻只显示一条。
- 时长：正式配音拆解视频实际时长不得少于 90 秒。用户明确要求的短片、测试或预览除外。
- 文案：默认面向普通观众讲清机械原理，以问题和因果关系串联拆解；避免流水账式报零件名、空泛宣传及反复免责声明。推测结构集中说明，画面持续保留提示。
- 节奏与同步：按短句生成 Ethan 配音，用实测音频时长安排字幕和镜头。优先自然语速与合理展示停顿，不通过明显放慢语音或循环镜头凑时长。
- 验收：交付前检查音色配置、全部字幕的单行与字符限制、音画对应关系，以及实际时长 ≥90 秒；完成音视频全片解码并记录结果。

## 已确认的拆解视觉风格（2026-10-28）

- 用户认可的是连续版：`series/3d-printer-v2/experiments/mechanical-hook-6e21ea58c8729117/mechanical-hook.mp4`，原话“就是这种感觉”。后续制作先读 `docs/approved-video-style.md`。
- 连续动作优先：保持同一机构的空间关系、朝向和运动方向；外壳逐渐打开，镜头连续靠近传动，再沿线材移向热端。不要为制造刺激而频繁跳切、突然换景别、隐藏零件或重置装配状态。
- 机械爽感来自看得清的动作与因果关系；近景揭示结构，让观众有时间辨认。长片可有必要的镜头转换，但要维持空间和动作衔接，不机械扩写成90秒的一镜到底。
- 声音连续跟随机械动作，使用克制的转动、滑动与接合拟音；取消每次换画面都加冲击音。合成拟音不得冒充实录。
- 此次确认只涵盖15秒测试的视觉连贯性与声音节奏，不代表批准完整EP01、整季成片或Moon旁白。该测试无旁白；后续配音不能重新压过画面或退回逐句拼接加长停顿的节奏。
- 保存参考成片、帧、场景、源文件归档及哈希；`series/3d-printer-v2/approved-style.json` 是本次确认的机器可读记录。不得覆盖参考视频或修改其归档脚本。
