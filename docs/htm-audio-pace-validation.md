# Measured HTM pace validation — 2026-11-10

**The missing timing input is fixed; pace is still UNQUALIFIED.** Four controlled
acoustic dimensions pass again. No production listening capability was enabled.
ASR spelling differences remain nonactionable and never authorize resynthesis.

## What changed and what was measured

The previous corpus supplied no alignment, so the speech-rate feature was always
zero. The new local `CTCAligner` reuses one frozen network on CPU or MPS and
measures each actual waveform. Derived audio receives its own inference; no
source timestamps are copied or scaled. Completed receipts bind the source
corpus, audio, scripts, model files, implementation, packages and FFmpeg. Recovery
checks completed outputs and skips inference; a failure cannot remove a case
from the frozen evaluation. The default CPU wrapper exactly reproduced the
previous stored CPU JSON on an isolated training recording.

The real MPS pilot used train/calibration recordings only. Acceleration changed
median measured character rate from 2.94 to 5.88 and 5.88 to 8.82 characters/s.
Warm MPS calls took roughly 0.19–0.44 s for these short clips; the first call
included warm-up. Character timing is CTC emission timing, not verified full
phoneme boundaries. No pronunciation quality was inferred from spelling.

The frozen corpus contains 100 originals and 900 variants: S0002/S0003 supply
24 training originals, S0004 supplies 16 calibration originals, and previously
unused S0007/S0008 supply 60 test originals. All normalized transcripts from the
previous 100-recording corpus were excluded before selection. Recording, speaker,
text and audio-hash partition checks passed. The reproducible speaker plan is
[htm-audio-pace-cohort.json](htm-audio-pace-cohort.json). Test variants retain the original
recording group; 540 test files do not count as 540 independent recordings.
The source remains pinned AISHELL-1, Apache-2.0, with upstream archive/transcript
hash verification. Old source corpora, models, reports and media remain intact.

The initial new cohort contained characters absent from the fixed ASR vocabulary
(including 秒, 链 and 腕). That cohort was preserved and never trained/evaluated.
A new corpus explicitly applied the fixed-vocabulary eligibility rule before
training and test evaluation. This is a scope limitation, not evidence that
unsupported words are spoken incorrectly. All 900 selected waveforms were
actually aligned; none failed or was silently dropped. Actual `--resume` reused
all completed receipts. Pace evaluation/qualification now requires alignment;
missing timing cannot yield an automatically passing zero-rate result.

## Frozen held-out outcome

The implementation, model, calibration and aligned inputs were locked before
HTM test inference. No threshold/model changes followed test results. Full
qualification replay reproduced calibration and all held-out inference, then
normal and accelerated example reports were validated against actual inference.
Other required listening dimensions remain unqualified; example report validation
does not establish complete listening acceptance. No controller repair or generation
was started from these reports.

| Dimension | Localized hits / defect groups | Normal alarms / groups | Cross-defect alarms / groups | HTM gain over current baseline | Status |
|---|---:|---:|---:|---:|---|
| omission | 0/0 | 0/0 | 0/0 | 0.000 | UNQUALIFIED |
| repetition | 0/0 | 0/0 | 0/0 | 0.000 | UNQUALIFIED |
| mispronunciation | 0/0 | 0/0 | 0/0 | 0.000 | UNQUALIFIED |
| clipping | 60/60 | 0/60 | 0/60 | 0.467 | PASS (controlled) |
| noise | 60/60 | 0/60 | 0/60 | 1.000 | PASS (controlled) |
| pause | 60/60 | 9/60 | 0/60 | -0.117 | UNQUALIFIED |
| splice | 60/60 | 0/60 | 0/60 | 1.000 | PASS (controlled) |
| pace | 1/60 | 0/60 | 0/60 | 0.017 | UNQUALIFIED |
| masking | 60/60 | 0/60 | 0/60 | 1.000 | PASS (controlled) |
| naturalness | 0/0 | 0/0 | 0/0 | 0.000 | UNQUALIFIED |
| expression | 0/0 | 0/0 | 0/0 | 0.000 | UNQUALIFIED |

Pace detects only 1/60 (1.67%). Pause still detects 60/60 but raises normal alarms
in 9/60 groups (15%); it is not enabled. The four passing rows concern known
clipping, additive noise, reversal/offset splices and interfering tones, with
known narration/mix stems. They do not validate genuine production edit quality,
real mix intelligibility, slow speech or context-appropriate pacing. The new
cohort differs from the previous cohort; their counts are not pooled or treated
as a paired improvement experiment.

The gates use point estimates: 60/60 recall has a Wilson 95% lower bound of
93.98%, and zero alarms in 60 groups has an upper bound of 6.02%. Full intervals,
onset error and frame predictions are in the benchmark. Baseline rules cover
clipping/pause plus available recognition candidates. Noise/splice/masking/pace
have no equivalent strong conventional classifier in that baseline; no claim
of HTM-specific superiority over a matched classifier is established.

## Remaining pace problem

Post-run diagnosis used **only training/calibration** data and did not alter this
model, calibration or held-out report. Training normal extent rates span
2.62–5.61 characters/s and accelerated rates 4.95–9.65: there is overlap. On the
16 calibration groups, measured whole-clip or extent rate admits a simple
sample-level threshold separating accelerated examples with zero group alarms.
These are diagnostic calibration results, not held-out results or adopted
rules. The HTM pace probability threshold selected by the frozen calibration
was 1.0, and the held-out result remains poor.

Timing is now present, so missing ASR input no longer explains the failed
classifier. The next model change must address how sentence-level rhythm and
local timing are represented and supervised, then use new held-out data.
A synthetic speed multiplier is also not an independent judgment of contextual
pace appropriateness. Do not tune on this now-inspected test set, move its failed
cases, or replace the frozen threshold with the diagnostic threshold.

## Independent quality-label sources checked

No additional reviewer model was downloaded. Only source metadata, licenses and
papers were inspected; no message was sent to a dataset author.

| Candidate | Original evidence | Current decision |
|---|---|---|
| [Beyond Naturalness](https://huggingface.co/datasets/ServiceNow-AI/Beyond-Naturalness-TTS-Eval/tree/2bfb1d78132c8c8a88899bd8dcf319c115c0e310) | 860 English samples; three linguists; binary failure labels for ten dimensions, including expressiveness and pace | Evaluation only; training/fine-tuning prohibited. No production naturalness/expression qualification adopted; speaker provenance and domain coverage also need verification |
| [Spanish naturalness](https://huggingface.co/datasets/asosawelford/es-TTS-subjective-naturalness/tree/62da90783a4f00aae19b2f17d8f6eeb49fefd52f) | Human naturalness ratings, 92 raters and 52 voices; original paper says most samples have one rating | HF card, linked author repository and paper did not establish an explicit data license. No training audio downloaded. Transcript/group provenance also needs verification |
| [RAVDESS](https://zenodo.org/records/1188976) | Human validity/intensity/genuineness judgments; 24 actors but only two text statements | CC-BY-NC-SA-4.0 and two texts do not meet the current production-license and three-way text-disjoint split needs |
| [CREMA-D](https://github.com/CheyneyComputerScience/CREMA-D) | Independent emotion-category/intensity votes; ODbL/Database Contents License | Emotion identity/intensity is not an expression-quality score; do not substitute it |
| [ESD](https://github.com/HLTSingapore/Emotional-Speech-Data) | Mandarin/English emotional speech and transcripts; research-only signed license requested | Intended emotional states are not independent naturalness/expression quality ratings; no license request was sent |

The earlier SOMOS/BVCC/NISQA findings remain in
[the prior report](htm-audio-review-continuation.md). None of these checks supplies
an accepted training corpus for Chinese mechanical-narration naturalness or
expression. That remains an internal data dependency, not a request for the user
to label clips. Mispronunciation, omission/repetition and complete listening
replacement likewise remain unqualified.

## Verification and reproducibility

Dedicated HTM/alignment suite: **21 tests passed**. Default project discovery:
**274 tests, OK, 2 native skips covered by the dedicated environment**. Meaningful
new checks cover recovery without repeated inference, changed model/output/case
sets, failure retention and pace with missing alignment. Syntax/TOML, corpus CLI
entry points and diff checks passed. The real CPU compatibility check and 900
MPS inferences supplement fixture tests. This step does not claim a new independent
agent or listening review; earlier independent review receipts remain historical.

Code: `1792c22`. Execution: `reports/htm-audio-pace-run-v1/`.
Alignment job: `reports/htm-audio-pace-aligned-v1/`.
Source metadata: `reports/htm-audio-label-sources-v2/`.
Archived scripts/logs/refs: `reports/htm-audio-pace-evidence-v1/`.

| Artifact | SHA-256 |
|---|---|
| benchmark | `ce75c2556df755b296a4175b6824e26e78e287d50f52cf9076d44a738c8fba8c` |
| model | `e3b58e67862f921a1758a2e3ff86f2b143c2d16a2b4be4d29d5f6b223bc3d33f` |
| calibration | `96a156fd73c28766ecfc0bdb07b841918a474acca6c74b1b77164a061391284a` |
| test_lock | `4efae090ab4cc6f9894d98440871e8eb50c0f22fd01e93226c936dd7db2f3142` |
| qualification_replay | `b43ade916df3374a3d69f14af84fd53dd4d2c022830514d27918f270cf6a747d` |
| report_replay | `3c39da2f4425a9ac1f189db8703bdfc2bbc1aba8c40ad2cff16360407bdd45c2` |
| source | `a49c61f1830cba6f04a76f7a5d271dbb33363fb48f51f9e212826fc96a7b9d4c` |
| raw_corpus | `1dc11c9a1689ab754a7c918cec0d0e9f973138e4a672be62351f3733afc25e71` |
| aligned_corpus | `7be40aac41ff2ac03e31b6e9f633debadc1f8c50e3e280138bed42bb638d50b2` |
| alignment_job | `0bbcfab4258119382e9586d5087355b1a83ed4ad5ecf5123e136e66ada42a5e4` |
| diagnosis | `cb1f1b96316ca9c18bab3feb3d32a64b701d825f8c03a6276abb0dad83ff83e9` |
| cpu_compatibility | `1605f8905c7659a8ec226043a7234b73bf1e72e20cb901723503634d76ec73bc` |
