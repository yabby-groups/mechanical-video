# Visual-first full series remake

## Current entry — 2026-10-30

Use the [current six-episode plan](printer-series-plan.md). Preserve the
user-approved EP01 Kai film and existing EP02 assets; the optimized EP02 full
film remains NEEDS_REVIEW. New episodes cover XY, four-corner Z lift,
hotend/two cooling paths, and bed support/first-layer gap. The printer series
uses `qwen3-tts-flash / Kai`; the Andre/twelve-episode/eight-shot template below
is historical, not current editorial guidance.

Existing `remake plan/render/worker` still execute that historical content.
This documentation update does not migrate the queue or implement a renderer.
Keep editorial hold and immutable archives; do not launch the old batch.
Next is EP03 belt/source-motion verification and local preview preparation.

## Historical implementation

Current editorial state: EP01 was rejected by the user despite technical media
acceptance. EP01/EP02 outputs are preserved; EP03 interrupted frames and
EP04-EP12 plans remain on editorial hold. `editorial-hold.json` prevents the
old worker from restarting. The chosen new direction is macro mechanical
action, source cutaways, visible transmission and synchronized sound. The
15-second mechanical-hook experiment and Moon continuous-speech audition are
tests, not accepted replacements for the full episode or the series voice.

The later **continuous** task `mechanical-hook-6e21ea58c8729117` was explicitly
approved by the user for its feel on 2026-10-28. It supersedes the eight-cut
hook as the visual/sound reference. Read [approved-video-style.md](approved-video-style.md)
before further production. This approval does not accept a full episode or
Moon narration, and saving it does not restart the held batch.

The user requested a new EP01-EP12 edition after approving the close-up CW2
visual study. Original accepted films, source CAD and interrupted frames stay
under `series/3d-printer`. The old worker is superseded, not resumed.

The active second edition lives under `series/3d-printer-v2`. It shares the same
official Voron 2.4r2 display master, commit and model hash. It selects the
Octopus display option instead of displaying multiple alternative control
boards as simultaneous installed hardware. Original source options remain on
disk. CAD materials remain unspecified; display colors are editorial choices.

The user explicitly requested a new male voice and supplied the read-only
catalog from ecom-details-image. Andre was selected from its male voice list
for the described natural, steady delivery. Voice model is qwen3-tts-flash.
The catalog location, hash and selected entry are retained in
`voice-selection.json`; a real decoded opening audition is retained under
`voice-audition/`. This edition overrides the normal Ethan project default.

```sh
.venv/bin/python -m mechanical_video.cli remake plan
.venv/bin/python -m mechanical_video.cli remake render --episode 1 --preview-only
.venv/bin/python -m mechanical_video.cli remake worker
.venv/bin/python -m mechanical_video.cli remake status
```

`remake_content.py` contains twelve authored episodes, each with eight distinct
shots: physical source-part actions, changed viewing regions, and brief
utterances tied to the visible action. Each plan allocates at least 96 seconds
of visual action. Measured speech can extend a shot; voice is never stretched.
Titles, source disclaimers and parts-list narration do not precede the action.
There is no music in this edition. Every subtitle is one line, <=20 characters,
and confined to its own measured speech interval. Scenes, scripts, captions,
audio clips, frames, source fingerprints and audit reports remain retained.

The SQLite queue is sequential and a separate `worker.lock` owns the edition.
All Blender work uses the project's shared `artifacts/render.lock`; other
workers cannot render in parallel. Sixteen native preview images (two per
shot) precede each production render. EP01 is visually inspected before the
worker launch; subsequent previews receive automatic bounds/source checks.
Automatic preview acceptance is not a claim of subjective viewing approval.

Per-episode render task IDs include model, measured timeline, selected voice
and archived source fingerprints. The archived sources never change. A new
source revision creates a new render directory. Existing completed output
requires its verified hash and is immutable. Existing JPEG frames are reused
only within the same task. Changed/uncertain completed output blocks replacement.

Speech uses the bundled local audiogen runner. Completed clips are decoded
before reuse. An uncertain request leaves a `.submitted` marker and stops the
worker. Only an explicit provider HTTP 429/503 rejection permits up to three
bounded attempts, with the prior marker and request log archived before retry.
No credentials are written to logs. Request environment and provider acceptance
are only established by actual successful clips, not by voice-catalog support.

Source-part placement is restored from the pinned manifest. Display explosions,
gear motion, filament, feed speed and deposited paths are explicitly schematic,
not meshing/contact physics, thermal analysis, certified control or sliced
G-code. The display's source approximation limitations remain on screen. No new
manufacturing CAD is claimed. Camera fitting checks each sampled shot, and
the production audit records source positions and bounds.

Completion requires native shot/source checks, multiple independently moving
source-part shots, >=90 seconds, 1080x1920, 30fps H.264/AAC, measured Andre
speech, single-line captions and a full FFmpeg decode. See each output's
`validation.json` and current `docs/validation.md`; queue/planning is not
completion. Worker logs are under `series/3d-printer-v2/production.log`.
