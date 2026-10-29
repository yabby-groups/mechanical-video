---
name: mechanical-video
description: Build reusable build123d mechanical assemblies and render disassembly videos, manage image analysis, ten video themes, resumable batch queues and M3 resource limits in this project.
---

# Mechanical video

Run from the mechanical-video project root with `.venv/bin/python -m mechanical_video.cli`.

- The user-authorized visual-first full-series remake uses `remake plan`,
  `remake render --episode 1 --preview-only`, `remake worker`, and `remake status`.
  Its independent queue/output live under `series/3d-printer-v2`; preserve the
  original series. The user selected a new male voice workflow; the remake is
  pinned to `qwen3-tts-flash / Andre`, overriding the project Ethan default for
  this edition. The supplied voice catalog provenance is in voice-selection.json.
  All twelve episodes are authored in remake_content.py. Use the same master
  CAD hash, eight distinct action shots, measured speech, >=90 seconds, 1080x1920,
  30fps and full decode. Review EP01 previews before launching the sequential
  worker. A definite HTTP 429/503 rejection may retry with archived markers;
  uncertain speech requests must block. See docs/series-remake.md.

- `series init --name 3d-printer`, `series plan --season 1`, `series render --episode 1`, `series render --episodes 1-3`, `series continue --count 3`, and `series status` manage the pinned official Voron 2.4r2 documentary series. See `docs/series-production.md`. Only authored episodes may render; never fabricate remaining editorial content or completion. Keep source CAD, license, per-occurrence transforms and material uncertainty. Share the master hash between episodes. Narration uses audiogen with explicit Ethan, measured short clips and single-line subtitles of at most 20 characters. Production format is 1080×1920, 30fps, H.264/AAC, at least 90 seconds. A completed output is immutable. Archived renderer fingerprints prohibit frame mixing. Preview before production, preserve frames, and serialize Blender with the existing render lock.

- `model` exports reusable independent STEP/STL solids and assembly manifest.
- `demo` renders shell and full explosion videos at 1280×720, 30fps, five seconds.
- `batch` queues ten themes; `worker` processes pending/failed jobs sequentially; `worker --watch` continuously polls. `status` reports failures, `retry` explicitly resets exhausted retry counts.
- Add `--portrait` for 720×1280 or `--production` for 1080p; model files are shared across all render variants.
- `image PATH` defaults to `gpt-6-luna`; requires `VISION_ENDPOINT` and optional `VISION_API_KEY`. `VISION_MODEL` can override the project default. Parametric families: planetary reducers and a photo-guided cordless-drill concept. Drill dimensions, hidden internals and battery configuration are hypothetical. Use `model --family cordless_drill` for its cache; supported drill themes are overview, shell, internals, explode, transparent, assembly and explanation. gears, working and closeup remain reducer-specific. Unsupported families must stop after saving analysis.
- `.venv/bin/python -m mechanical_video.web` serves the loopback image uploader.

All Skills stay in this project's `.agents/skills/`. Never write global Skills. Use the installed cad Skill when extending STEP/build123d models. Preserve independently validated positive-volume part solids and part-local placements; never substitute a single whole-object mesh for an assembly.

Inspect artifacts/models/*/assembly.json, per-video job.json, scene.blend, blender.log, video.verification.json and queue.sqlite before reporting completion. A job is complete only after ffprobe checks H.264, size, fps, duration, and FFmpeg decodes every frame. Keep frames for interrupted render resume. Reuse cached models; bump model VERSION when geometry implementation changes.

Only one renderer may hold artifacts/render.lock. Eevee is default. Optional Cycles uses Metal. Blender may require approved GPU access outside the Codex sandbox on macOS; keep the existing sandbox configuration. Do not install or run TripoSR until its ARM64 dependencies have passed an isolated compatibility check. Baseline generation never depends on reconstruction weights.

All hidden structures and image-derived dimensions remain explicitly inferred. The demo is an educational kinematic visualization, not a certified manufactured design or dynamic simulation. Never claim arbitrary image-to-CAD or provider acceptance without an actual successful run. See README.md and docs/validation.md for verified scope.

A persistent watcher owns `worker.lock`; `render.lock` is held only during a render or independent acceptance. `.venv/bin/python -m mechanical_video.acceptance --wait` may run while the watcher remains alive. New jobs archive `blender_scene.py`, `audit_scene.py` and `narration.py` under `renderer/`; fingerprints participate in task IDs. Never modify archives. Re-enqueue after editing source to create a new render version and reuse the CAD cache. Cycles writes selected Metal GPU evidence to `hardware.json`; new workers record timing in `metrics.json`.

The workbench supports theme, portrait/landscape, 720p/1080p, duration and renderer selection, plus cached example generation without a configured vision provider. Latest actual acceptance includes 1080p playback and Cycles on the Apple M3 GPU; consult docs/validation.md rather than assuming all provider or resolution combinations have been tested.
