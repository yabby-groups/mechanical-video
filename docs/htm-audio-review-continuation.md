# HTM audio continuation validation — 2026-11-10

Historical frozen run-v8 snapshot. For the subsequent actual-timing experiment,
see [pace validation](htm-audio-pace-validation.md). Its hashes and measurements
remain unchanged.

Status at this checkpoint: four dimensions pass configured controlled-injection point thresholds.
General production listening remains unqualified; no production capability was enabled.
This is not complete listening replacement or continuous audiovisual acceptance.
User clarification: actual pronunciation matters; ASR spelling errors are not
repair targets. All string-only candidates are explicitly nonactionable, retain
null defect confidence, and cannot initiate synthesis.

## Implementation and independent review

The official source-built C++ SP/TM/Classifiers now retain encoded acoustics,
columns and supervised anomaly context alongside active TM cells. Train-only
class balancing addresses rare local defects. Calibration searches low
probabilities and empirical quantiles on calibration data only. Explicit
`negative_kinds` prevent unknown dimensions becoming negative examples in
training, calibration and qualification. Only recordings explicitly normal for
all six acoustic mechanisms satisfy warm-start counts or train SP/TM.
Cross-defect false alarms are separately measured and gated. Process-local
fingerprint caching binds device/inode/size/mtime/ctime; calibration cache reuse
still checks calibration dependencies. No online learning occurs in evaluation.

Actual independent agent `/root/htm_continuation_review` found the unknown-negative
calibration/count inconsistency and an incorrect stale-file test expectation;
both were fixed and retested. Its final bounded warm-start observation was also
fixed with explicit-normal regression coverage. This was code QA, not listening.
Independent `/root/htm_benchmark_audit` then verified 1,011 unique referenced
hashes, six nested model references and 13 checkpoint files; it independently
recomputed every grouped dimension and baseline metric with exact agreement.
Its audit supports controlled-injection detection only, with the statistical,
label and baseline limits below. Archived run history records that v5–v7 stopped
before completed test outputs; input hashes alone cannot prove historical
non-consultation. The no-test-tuning statement relies on that execution history.
Earlier independent controller experiments remain in
[original validation](htm-audio-review-validation.md); no fake dispatch or new
production-media acceptance was introduced.

The native source-built environment passed **18 tests**. Final default project
discovery passed **271 tests, 2 native-environment skips**. Coverage includes CTC
blank-separated repeats, actual recognized-token timing, unknown labels,
contradictory negatives, cross-defect qualification, development ineligibility,
same-size timestamp-restored edits and cached calibration-input mutation.

## Frozen Chinese experiment

AISHELL-1 source revision `bbe295d530192a4cd41644b711c9aecd087df653`,
[official Apache-2.0 declaration](https://www.openslr.org/33/). The maintained
fetcher verifies upstream LFS SHA-256, transcript Git blob SHA-1 and byte sizes,
preserving existing manifests. Five original speakers were partitioned before
training: 24 train, 16 calibration and 60 test original recordings. Recording,
speaker, normalized text and audio hash cannot cross partitions. Nine variants
per recording give 900 cases total. Three normal controls include modest
pitch-preserving tempo changes and short pauses; six known acoustic injections
have local labels. Related copies count once per original group, not as
independent samples. Negatives exclude physically coupled mechanisms.

Previous inspected English examples were demoted to development; their pause
regression improved from 0/2 to 2/2, which is not qualification. Blind runs v5–v7
were stopped before test outputs when review exposed contract issues. Their
original bytes remain archived. Final run-v8 froze current implementation,
calibration and inputs before held-out inference. No test-driven tuning or
threshold changes followed these results.

The test comprises 540 variants from 60 independent originals and **two held-out
speakers**. Labels describe deterministic perturbations of human Mandarin read
speech, not independently rated naturalness, expression or production mixing.
Inserted short pauses were chosen at low-amplitude boundaries, without human
naturalness labels; they are controls for the declared long-pause mechanism.
“Normal” and negative labels refer to absence of the declared injected mechanism;
they are not exhaustive perceptual ratings of the source recording.

| Dimension | Localized hits / defect groups | Normal false alarms / groups | Cross-defect false alarms / known-negative groups | HTM gain | Onset MAE (s) | Status |
|---|---:|---:|---:|---:|---:|---|
| omission | 0/0 | 0/0 | 0/0 | 0.000 | — | UNQUALIFIED |
| repetition | 0/0 | 0/0 | 0/0 | 0.000 | — | UNQUALIFIED |
| mispronunciation | 0/0 | 0/0 | 0/0 | 0.000 | — | UNQUALIFIED |
| clipping | 60/60 | 0/60 | 0/60 | 0.550 | 0.010 | PASS (controlled) |
| noise | 60/60 | 0/60 | 0/60 | 1.000 | 0.025 | PASS (controlled) |
| pause | 60/60 | 0/60 | 0/60 | 0.000 | 0.535 | UNQUALIFIED |
| splice | 60/60 | 0/60 | 0/60 | 1.000 | 0.010 | PASS (controlled) |
| pace | 0/60 | 0/60 | 0/60 | 0.000 | — | UNQUALIFIED |
| masking | 60/60 | 0/60 | 0/60 | 1.000 | 0.008 | PASS (controlled) |
| naturalness | 0/0 | 0/0 | 0/0 | 0.000 | — | UNQUALIFIED |
| expression | 0/0 | 0/0 | 0/0 | 0.000 | — | UNQUALIFIED |

Measured CPU-run times: training 94.6 s; calibration 88.7 s; held-out benchmark including calibration replay 646.8 s.

Recall requires overlap with every labeled defect copy in the original group;
any normal or known-negative copy false alarm counts against that group. Gain
is `(HTM recall - normal FPR) - (baseline recall - normal FPR)`; cross-defect FPR
is an additional mandatory gate. The baseline has amplitude/silence rules; this
corpus supplies no recognition alignments and cannot measure text accuracy.
The configured gates use point estimates. At 60/60 hits the Wilson 95% recall
interval is 93.98–100%; at 0/60 alarms its upper bound is 6.02%, so these results
do not establish 95% recall / 5% FPR as confidence-bound guarantees. Full intervals
and baseline statistics are in the frozen benchmark. Noise/splice/masking gains
are against always-negative baseline outputs; this does not show superiority to
a matched conventional acoustic classifier.
These results measure the combined HTM adapter; no separate SP/TM ablation was
performed. Localization overlap alone is insufficient evidence of exact repair
boundaries or perceptual acceptance.

## Actual recognition and remaining labels

Existing local Chinese wav2vec2 CTC weights at revision
`99ccb2737be22b8bb50dcfcc39ad4d567fb90cfd` were executed on one train and one
calibration original. Greedy token timing is independent of the expected-text
forced path. CTC emission intervals can be only one frame wide; they are not
complete phoneme durations or sufficient local-repair bounds. Observed “阿里 / 阿黎” and other disagreements were localized, with
no claim that the actual recording is mispronounced. New reports explicitly
mark these candidates nonactionable. Original alignment, model-file fingerprints,
runtime package versions and updated candidate evidence are archived.

Independent quality labels remain unresolved:

| Source | Original evidence | Decision |
|---|---|---|
| [SOMOS](https://zenodo.org/records/7378801) | 374,955 human naturalness ratings; single synthesized speaker; CC-BY-NC-SA-4.0, noncommercial research only | Not a speaker-disjoint production qualification corpus; no audio downloaded |
| [VoiceMOS 2022 / BVCC](https://zenodo.org/records/10691660) | Unified human MOS; mixed source terms; Blizzard audio omitted with separate download scripts and redistribution restrictions | Rights and speaker/text grouping require source-level review; no corpus adopted |
| [NISQA corpus](https://github.com/gabrielmittag/NISQA/wiki/NISQA-Corpus) | Human signal-quality dimensions; source-specific licenses | Signal quality is not an expression-quality label; no model substituted for HTM |

Original metadata and license pages are archived in
`reports/htm-audio-label-sources-v1/`. No model predictions or synthetic injection
labels were relabeled as independent subjective scores. Chinese mechanical-term
pronunciation, omission/repetition, naturalness/expression, real masking and
production-domain listening remain unqualified until their own sufficient,
licensed, independently labeled held-out evaluation passes. Existing formal
quality thresholds and `continuous_av` stay unchanged. Models, source audio,
media and build caches remain ignored and outside commits.

## Immutable local evidence

Primary run: `reports/htm-audio-aishell-v1/run-v8/`.
Corpus: `reports/htm-audio-aishell-v1/dataset-dimensions-v2.json`.
Execution/archive: `reports/htm-audio-continuation-v1/`.

| Artifact | SHA-256 |
|---|---|
| benchmark | `fdf2eb880340f8f4dde05d74686a31f9b2540f776db25111a9731d3e33033053` |
| model | `912fcbcac4bd91d9adebde4045b783fd56e1f7a261307cb4becb47c486af18c1` |
| calibration | `56024b2bf0655dc59ab7f4a77f7d3f0e0693a9c7efbbf5964018b8c1872d0b55` |
| dataset | `6eb14c3105baf805af29dd1f3d0efca61f9e3b4212a1e8ebcc1f7527bee186e3` |
| source | `8edf63b7e3f55191dde8e6602bb282b402d22549943418d2974b42c252e30253` |
| frozen_test | `769c34957fc3d7898ab1cdc1381fad421e1c0e27c4c5e389936cf8f990632496` |

Final qualification validation reran calibration and every held-out inference,
accepting exactly clipping/noise/splice/masking for controlled injections in 655.9 s.
No production capability was registered. Proof: `run-v8/qualification-replay.json`,
SHA-256 `323c4f1abec93cf48d59c193f6cc550dec93c8ec6792b3a3b4685075b8c6b610`. The actual independent audit receipt is
`reports/htm-audio-continuation-v1/independent-audit-receipt.json`; it records
the real collaboration response and is explicitly not a cryptographic identity receipt.
