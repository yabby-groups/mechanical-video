# Independent audio QA

Run `.venv/bin/python -m mechanical_video.audio_qa AUDIO SCRIPT --output NEW_DIRECTORY --asr`.
The optional ASR request uses the existing `scripts/ep02_asr_review.py` and
submits an MP3 derived from the actual input. It creates a submission marker
before the request; inspect an uncertain submission before retrying. Never
resubmit merely because a request timed out. The report records the original
input hash, text comparison, ffprobe, full decode, loudness and silence
candidates. An ASR discrepancy is a candidate, not proof of mispronunciation.
Times are unknown when the recognizer supplies no alignment. FFmpeg silence
and peaks need contextual review.

The six dimension weights are 30/20/15/15/10/10. All scores currently remain
null: forced alignment, calibrated clarity and naturalness, voice consistency,
music masking and visual correspondence are not implemented. The result is
NEEDS_REVIEW, or FAIL on a fatal input/decode error. There is no automated
speech repair, reassembly, final-mix assessment or blind regression benchmark.
Reviewers must identify the affected shot and timecode from evidence; do not
invent them. Explicitly preserve episode-specific voices, including Kai.

To attach an independently completed report for the exact final MP4, use
`mechanical_video.video_qa VIDEO --output NEW_DIRECTORY --audio-report REPORT`.
The input SHA-256 must match. A fully verified passing report contributes once
to the existing 15-point audio dimension. The present checker cannot produce
such a report and cannot authorize delivery.

`python -m mechanical_video.audio_direction TIMELINE --output NEW_JSON` creates
a direction draft from existing measured events, preserving the configured voice
and model. It does not claim emotion controls or visual synchronization.
`python -m mechanical_video.audio_appeal AUDIO --output NEW_DIRECTORY --timeline
TIMELINE --technical-report TECHNICAL_REPORT` measures silence in the actual
asset and records segment placement; its independent 20/25/20/15/15/5 appeal
scores remain null until actual listening, visual, and subtitle evidence exists.
The audio technical and appeal delivery gates require the same input hash and
thresholds 90 and 85 respectively. They do not add to the video score again.
The current code does not automatically replace clips, update subtitle timing,
reassemble a film, or interpret emotion from an audio model.
