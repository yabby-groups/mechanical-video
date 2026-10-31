# Narration subtitle placement

Follow the existing [approved video style](approved-video-style.md); this document adds typography placement evidence without changing that approval.

For native 1080×1920 printer-series video, use the accepted EP02 actual white-glyph position as the placement reference: Y1489–1531, approximately389px below the last white-ink row (measurement conventions can differ by1px). This is actual encoded ink, not ASS anchor or font box. EP02 reference SHA2565c5feeb0e876dfdcddeef1782d6193fb757aa483c2868a7d06ecdcd6d335d295; independent evidence: `series/3d-printer-v2/episodes-current/EP03/benchmark-production/subtitle-position-review-v1/independent/report.md`.

EP03 initial controlled candidate retains the current font, size, outline and an8 alignment; change Subtitle pos(540,1635) to pos(540,1484). This is a candidate anchor, not proof of exact ink placement. At another native resolution scale coordinates proportionally and remeasure actual output; do not confuse encoded upscaling with native typography.

Reserve a clear subtitle band around Y1480–1540. The existing trajectory Note atY1500 must not coexist in that band: move it toY1410 for this candidate and inspect the actual mechanism/background. Preserve other approved labels unless there is evidenced overlap. Avoid overlaying narration with schematic labels, pointers or platform controls.

Every narration caption remains one line, ≤20characters including punctuation/Latin/digits, with no overlapping caption times. Verify short and longest strings and mechanism closeups in actual encoded samples. Measure white glyph ink (RGB>220, channel spread<22, discard rows≤8eligible pixels), record the chosen crop band and full source/output hashes; allow antialiasing and compression variation. Inspect outlines and actual readability separately. A count or successful decode does not establish perception, word alignment or platform UI safety. Platform-safe claims require actual platform UI evidence.

New audio can change timing: use actual measured sources and approved Script timeline; never silently stretch voice or copy obsolete cue times. Every new encode needs new hashes and applicable final audio/video/audience reviews. Preserve previous films and archived scripts.
