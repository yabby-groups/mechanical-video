# 《拆解一台 3D 打印机》

Run from this repository, using the project interpreter:

```sh
.venv/bin/python -m mechanical_video.cli series init --name 3d-printer
.venv/bin/python -m mechanical_video.cli series plan --season 1
.venv/bin/python -m mechanical_video.cli series render --episode 1
.venv/bin/python -m mechanical_video.cli series render --episodes 1-3
.venv/bin/python -m mechanical_video.cli series continue --count 3
.venv/bin/python -m mechanical_video.cli series status
```

`python -m mechanical_video.series` is the same entry point. Installing this
project also exposes `series`; installing a global Skill is unnecessary.

The twelve-episode plan and all twelve authored scripts are persisted under
`series/3d-printer`. EP01–03 have actually been synthesized, rendered and checked
(see current per-episode `validation.json`). EP04–12 have scripts and specialist
animation code, including explicitly schematic internal principle diagrams;
their provider calls, native scenes and completed videos have not yet been
accepted. A planned episode is never reported as a produced film.

## Source and reuse

Official repository: <https://github.com/VoronDesign/Voron-2>.
Revision: `7b32e405f0719881cca782500c822e01e3b16bf2`, branch `Voron2.4`,
CAD `Voron_2.4r2_Assembly_STEP.zip`. The original archive, extracted STEP,
GPL-3.0 LICENSE, upstream tree/commit records, and 263-page manual are retained.
`asset_manifest.json` records hashes and provenance. `cad_bom.json` is an
occurrence inventory, not a shopping list; the official configurator is the
source for a configuration-specific procurement BOM.

Part geometry is exported in local millimetres; full world occurrence matrices
and assembly paths are preserved. Native STEP remains the master. Colors are
display groups, not verified material specifications. Unknown materials stay
unknown. OpenCascade topology repairs, if required, are recorded per part and
must preserve volume within 1e-5 relative tolerance. Defective vendor solids
that cannot be repaired analytically may use a closed, consistently oriented
faceted BRep derived exclusively from the original CAD triangulation (0.025 mm
linear tolerance, 0.2 rad angular tolerance). This display approximation must
pass positive-volume and geometric validity checks, and converge in volume to
within 1 percent of a finer (0.01 mm, 0.1 rad) source tessellation. An invalid
analytic BRep's own volume integral is retained as a diagnostic, not treated as
a reliable reference. Each approximation records actual convergence and
triangle count and is marked as schematic on screen. Source STEP is unchanged.
Failed in-memory solid validation blocks display-model generation. A separate
full disk STEP round-trip audit is retained; its findings must also be reviewed
before claiming reusable manufacturing CAD validity. No invented internal printer
geometry replaces CAD.

The manual's frame section is pages 12–21, Z drives 34–47, A/B drives 62–80,
gantry 82–122, Z belts 118–121, belt routing 124–142, panels 232–244.
The narrative distinguishes fixed bed/four-motor belt-lifted gantry from
leadscrew-bed machines. Toolhead variants must follow the pinned CAD.

## Resume and acceptance

One production lock and the existing shared render lock serialize work.
Speech is generated in short, separately cached Ethan clips using the bundled
audiogen runner. An uncertain provider submission leaves a marker and cannot
automatically resubmit. A known HTTP rejection can be reviewed and explicitly
archived before retry; preserve that audit trail.

Each episode archives its production Python sources. Different source hashes
require a new task/version instead of mixing old and new frames. Complete JPEG
frames are reused; an interrupted encode can rerun without rendering those
frames. Five 25%-resolution preview frames precede the 1080×1920 sequence.
Blender uses Eevee and four CPU threads. Preview, production scene, logs,
motion samples, narration clips and frames remain available.

The actual clip durations set subtitles and timeline. Each subtitle is a
single line of at most 20 characters, and its interval contains only that
utterance. Gaps are short natural pauses; no time stretching. Music is a quiet
locally synthesized original ambient bed, independent of the voice provider.

Completion requires 90 seconds, 1080×1920, 30fps H.264, AAC, a full FFmpeg
decode, ordered/non-overlapping subtitle timing, and source-model-matched
mechanical keyframes. `validation.json` records the evidence. Explosion
distances and sample toolhead paths are marked as illustrative on screen;
these are not stress simulation, certified motion control, or sliced G-code.

Existing output with acceptance is skipped. Existing output without acceptance
is preserved and blocks replacement. No completion is recorded on failure.
Source, model and media files are deliberately retained for auditing and reuse.

## Additional CAD quality audit

`master_assembly/roundtrip-validation.json` preserves a stricter independent
read-back of all 1,414 STEP files. Three analytic compatibility exports have
invalid topology after STEP serialization (`m00078`, `m00079`, `m00784`), despite
positive volumes and in-memory validity. Some valid threaded parts have about
0.281% mass-integral drift; that is reported rather than hidden. These findings
do not establish manufacturing accuracy. Source-derived approximation and
motion are marked on screen. The original display assembly, all geometry
hashes and finished videos are preserved; experimental STEP files in `canonical_parts/` remain diagnostic. Three native
OpenCascade BRep sidecars have passed positive-volume and solid-validity
readback in `canonical-brep-validation.json`; the two carriage faces use their
original boundary wires, while the Molex component uses its archived closed
source mesh and is explicitly approximate. `cad_assembly.json` preserves every
source ID, hierarchy and matrix and points these three parts to native BRep.
`cad-roundtrip-validation.json` records an independent full pass over this
mixed STEP/BRep mapping. Numerical volume drift stays reported and is not a
manufacturing accuracy certificate. Display STL files and the display manifest
remain unchanged. Failed STEP trials and the original failed audit are retained.

Reproduce the additional CAD validation sequentially:

```sh
.venv/bin/python scripts/canonical_printer_brep.py
.venv/bin/python scripts/validate_printer_parts.py --canonical
```

Only claim full CAD readback acceptance when the latter report has `passed:true`.
Do not substitute a sidecar into an already rendered display assembly.

The source CAD includes Spider and Octopus alternative controller arrangements.
These are source configuration options, not a claim that the printer requires
two simultaneous controller boards. Materials remain unknown where upstream
metadata does not establish them.

The preserved display STL of the right X carriage is not watertight (missing
triangulation on source faces); canonical BRep validity does not retroactively
repair that rendering mesh. This local display limitation is covered by the
on-screen source-approximation label and retained for audit. Do not use display
STLs for fabrication. A future mesh correction must create a new display-model
version and new render tasks, preserving accepted first-season outputs.
