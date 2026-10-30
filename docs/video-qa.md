# Evidence-first video QA

Run `.venv/bin/python -m mechanical_video.video_qa VIDEO --output NEW_DIRECTORY --visual`.
The directory must not already exist. The report records the source hash, sampled
frames, full decode result, candidate intervals and the actual provider response.
Exit codes: 0 PASS, 2 REWORK, 3 NEEDS_REVIEW, 4 FAIL. A formal video needs
90 seconds, 1080p (portrait or landscape), H.264 and AAC. Long black, frozen,
or silent intervals are candidates, not proof of defects. Inspect their context.
The visual request describes five actual sampled frames; it is not motion,
mechanical, audio, subtitle, or shot-level certification. Scores remain null
until those dimensions have reliable evidence. Never treat null as a pass.

This is an initial inspection tool, not an automated production or repair
system. Existing series queues, immutable archives, editorial hold, and render
lock remain authoritative. Do not use this report to approve or release a film.
