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

For retention-driven production, use [the audience-growth worksheet](audience-growth.md).
Review the actual local A/B outputs with matching time ranges. Report separately:
new visible information after the hook, time to the first understandable causal
payoff, retellable knowledge, share/save value, a natural answerable discussion
point, and the reason to follow the series. Cite actual times and coverage;
mark ending or global pacing unavailable when only a local excerpt exists.
A moving camera alone is not new information. Do not assign a growth score or
infer engagement effects from static images, platform labels or one post.
Preserve the distinction between a production improvement visible in the
reviewed asset and an untested platform-performance hypothesis.

Actual observations also support `retention_5s`, `retention_9s`,
`retention_18s`, `retention_27s`, `skip_2s_rate`, `like_rate`, `comment_rate`,
`share_rate`, `save_rate`, `follow_rate`, and integer `attributed_followers`.
Rates are fractions (51.72% is `0.5172`), not percentage-point numbers.
Preserve the platform-reported value and denominator uncertainty instead of
reconstructing rounded rates. Do not merge values from different observation
times or scopes into one snapshot.

Supply `actual.media_type` as `video` or `image_post` when known. Comparisons
require matching media metadata; a known video cannot use an image post or a
legacy record with unknown media type as a peer. Legacy records remain valid;
comparisons between two unknown types explicitly report that media
comparability is unverified. The existing window/platform/duration filters
remain descriptive; they do not establish matching topics, random assignment,
independent viewers or growth causality. For image posts, do not invent a video
duration to force them into this duration-based comparison tool; retain their
native image-count metrics in the source evidence instead.


## 连续视听评审入口｜2026-11-09

完整审片必须执行[连续视听评审与证据导入](perceptual-review.md)，扫描工具的NEEDS_REVIEW不能称为通过。使用原片播放包记录实际覆盖与理解时间码，独立评审后导入新报告；缺感官能力则保留明确缺口。delivery_gate重新校验连续视听证据和原始评分，不信任单独PASS标签。
