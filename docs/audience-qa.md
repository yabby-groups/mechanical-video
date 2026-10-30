# Audience QA

Run `.venv/bin/python -m mechanical_video.audience_qa VIDEO --output NEW_DIR --visual --technical-report TECHNICAL_REPORT`.
Use a timeline only if it belongs to that exact video revision; otherwise shot
IDs remain unknown. The tool samples frames from the actual video, retains the
configured model's response and evidence-linked candidate findings, and binds
the two reports to the same video hash. The technical and audience thresholds
remain independent: 90 and 85 respectively. Unverified dimensions do not pass.

Sampled stills cannot establish the quality of motion, audio, subtitle timing,
or the full audience experience. The current implementation leaves all audience
scores unverified and cannot certify a film or perform creative repairs.
Do not infer viewing, retention or engagement statistics from a model assessment.

`python -m mechanical_video.episode_performance --db PATH import RECORD.json`
stores subjective predictions separately from actual imported observations.
`... --db PATH compare SNAPSHOT_ID METRIC` compares recorded observations from
the same platform and measurement window, within 10% of the video duration.
The result is descriptive, not a causal or statistically validated estimate.
Required record fields are `episode_id`, `video_version`, `platform`,
`duration_seconds`, `title`, and `cover_version`. Subjective predictions require
`audience_score` and `basis`; real observations require `source`, `observed_at`,
`measurement_window`, and a `metrics` object. Retention and completion rates
are fractions from 0 to 1. Do not import guesses as actual data.
