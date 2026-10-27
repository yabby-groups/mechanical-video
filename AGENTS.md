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
