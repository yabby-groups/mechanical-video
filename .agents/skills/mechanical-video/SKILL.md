---
name: mechanical-video
description: Build reusable build123d mechanical assemblies and render disassembly videos, manage image analysis, ten video themes, resumable batch queues and M3 resource limits in this project.
---

# Mechanical video

Run from the mechanical-video project root with `.venv/bin/python -m mechanical_video.cli`.

- For the printer series, read [the current six-episode plan](../../../docs/printer-series-plan.md),
  approved style and current approval/QA records before production. Preserve
  EP01 and EP02 assets; EP02's generated optimized film remains NEEDS_REVIEW.
  Printer narration is explicitly `qwen3-tts-flash / Kai`, overriding both
  historical Andre and the generic Ethan default. Never regenerate locked audio
  merely because plans changed. New episodes cover XY, four-corner Z lift,
  hotend/two cooling paths, and bed support/first-layer gap. Use one causal
  mechanism per episode, continuous spatial relationships, measured speech,
  >=90 seconds, 1080x1920 encoding, 30fps and full decode; do not impose eight shots.
  Recheck selected source hashes and corrected occurrence exports rather than
  blindly reusing the historical master hash. Next is EP03 belt-route and
  input/motion verification, then three opening proposals and local preview.
  Generic carriage travel is not proof of correct CoreXY transmission.

- `remake status` inspects the historical queue under `series/3d-printer-v2`.
  `remake plan/render/worker` still use the old twelve-episode implementation
  in remake_content.py; they do not consume the current six-episode plan.
  Keep editorial hold, historical plans and original assets. Do not launch the
  old worker or regenerate old plans to implement the new direction. New and
  historical episode numbers are not interchangeable resumable tasks. See
  docs/series-remake.md for historical implementation, not current voice or
  editorial authority. A definite HTTP 429/503 rejection may retry with archived
  markers; uncertain speech requests must block.

- Historical `series init/plan/render/continue/status` commands manage the original official Voron 2.4r2 series described in `docs/series-production.md`; they are not the current six-episode production entry. Historical Ethan audio is preserved, not a voice choice for new printer films. Only authored, in-scope episodes may render. Keep source CAD, license, per-occurrence transforms and material uncertainty. Use verified source versions, measured speech and single-line subtitles of at most 20 characters. Production format is 1080×1920, 30fps, H.264/AAC, at least 90 seconds. Completed outputs are immutable. Archived renderer fingerprints prohibit frame mixing. Preview before production, preserve frames, and serialize Blender with the existing render lock.

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
