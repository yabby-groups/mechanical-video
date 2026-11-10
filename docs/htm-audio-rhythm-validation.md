# Measured isolated rhythm comparison — 2026-11-10

**The dedicated rhythm branch runs, but no rhythm capability qualified.**
Neither the pace nor pause result demonstrates HTM gain over both matched controls.
No production listening capability, repair dispatch or generation was enabled.

Implementation: `3e342b5`. [Usage, model and gate definitions](htm-audio-rhythm.md).

## Frozen design and partitions

One fixed candidate used official SP/TM and Classifier, two-second windows with a
0.5-second hop, three epochs and seed 42. Rules and a no-TM classifier used the
same measured inputs. Thresholds came only from new calibration data. The
driver recorded development probabilities without model selection. No model,
threshold or eligibility change followed blind-test results.

| Partition | Independent recordings | Variants | Speakers |
|---|---:|---:|---|
| Train | 24 | 288 | S0002/S0003 |
| Development | 16 | 192 | S0004, formerly inspected calibration |
| Calibration | 24 | 288 | S0009, new |
| Test | 60 | 720 | S0010/S0011, new |

All 1,488 waveforms received actual frozen local CTC inference, with no failed
cases discarded. Original recordings, speakers and normalized texts were checked
for partition leakage. Previously inspected S0007/S0008 test recordings were
excluded, and historical transcripts were excluded before new selection. The
predeclared vocabulary filter is a coverage limit, never a pronunciation label.
The licensed source remains AISHELL-1 Apache-2.0 at the existing pinned revision.

## Held-out result

Hits require interval IoU >=0.5 and complete measured coverage for the case.
All positive variants of a recording must pass; any normal-copy alarm counts
against that recording. Each subtype has 60 independent positive groups, not
720 independent examples. Normal and known cross-defect counts are also 60 groups.

| Dimension | Rules hits | No-TM hits | HTM hits | HTM normal alarms | HTM cross-defect alarms | Result |
|---|---:|---:|---:|---:|---:|---|
| pace | 0/60 | 0/60 | 0/60 | 1/60 | 0/60 | UNQUALIFIED |
| pace/global_fast | 0/60 | 0/60 | 0/60 | 1/60 | 0/60 | UNQUALIFIED |
| pace/local_fast | 0/60 | 0/60 | 0/60 | 1/60 | 0/60 | UNQUALIFIED |
| pace/slow | 0/60 | 0/60 | 0/60 | 1/60 | 0/60 | UNQUALIFIED |
| pause | 38/60 | 37/60 | 32/60 | 0/60 | 0/60 | UNQUALIFIED |

For pace, rules had no normal or cross-defect alarms; the no-TM control had
1/60 in each category. All pause methods had zero normal and cross-defect alarms.
No method met the recall gate. These results use new recordings, extra slow/local
controls and a stricter localization criterion; do not treat comparison with the
previous 1/60 pace result as a paired improvement or regression estimate.

| HTM comparison | Recall-minus-FPR gain | Paired 95% interval |
|---|---:|---|
| pace vs rules | -0.0167 | [-0.0500, 0.0000] |
| pace vs no_tm | 0.0000 | [0.0000, 0.0000] |
| pause vs rules | -0.1000 | [-0.1837, -0.0167] |
| pause vs no_tm | -0.0833 | [-0.1833, 0.0000] |

HTM pause recall is 53.33% (Wilson 95% interval 40.89%–65.37%). Zero of 60
false alarms still has a Wilson upper bound of 6.02%; zero pace hits has a
recall upper bound of 6.02%. The benchmark includes full per-method intervals,
onset/offset errors and excess predicted duration. HTM pause onset/offset MAE
were 0.399/0.537 seconds among cases with predictions; missing detections
remain misses and are not assigned an invented localization error.

## Coverage and interpretation

Under the frozen confidence policy, 49/720 test waveforms had incomplete
usable timing coverage. They remained in the benchmark and prevented
qualification; they were not silently dropped or counted as sound defects.

| Transformation | Incomplete coverage |
|---|---:|
| clipping | 3 |
| local_fast | 2 |
| masking | 3 |
| noise | 10 |
| normal_short_pause | 2 |
| pace | 2 |
| pause | 21 |
| slow | 4 |
| splice | 2 |

The frozen rule pace threshold is 5.000000000000001 (an explicit no-alarm
candidate), while no-TM/HTM probability thresholds are 0.994301/0.997381.
Calibration optimizes the conjunction of all pace variants within a recording;
a subtype that cannot be separated can therefore suppress otherwise useful
alarms. This is a limitation of this declared objective, not a reason to change
the frozen threshold after seeing test results. The current experiment does
not establish that HTM is generally incapable of rhythm assessment.
Any follow-up architecture or objective change needs a new version and new
unseen acceptance groups; the present failures remain evidence.

Transformation labels establish controlled speed/pause changes only. They do
not establish contextual pace appropriateness, genuine normal emphasis,
naturalness or expression. No eligible independently rated Chinese quality
training corpus was acquired in this round. ASR spelling differences remain
nonactionable when pronunciation is correct or uncorroborated.

## Verification and remaining gate

- Full project discovery: **287 tests, OK, 4 native skips**. After adding one
  additional positive-gate regression, the complete dedicated native suite
  passed **35 tests**; final rhythm-focused suite passed **14 tests**.
- Actual CPU HTM training, 1,488 MPS alignments, completed alignment resume,
  and exact replay of calibration plus every held-out inference passed.
- Completed experiment resume reused the benchmark without repeated blind
  inference. Cache corruption, missing receipts, state reset, checkpoint
  changes, coverage and paired-gain behavior have targeted regressions.
- Actual normal/local-fast CLI evaluations stayed UNQUALIFIED/nonactionable.
  The refreshed installed console matched module inference exactly.
- Original acoustic adapter bytes are unchanged. Actual frozen normal,
  clipping, noise, splice and masking examples each reproduced 295 frame
  probabilities exactly. This is compatibility evidence, not a new listening review.
- No new independent Agent listening review is claimed. Conditional ratchet
  and lead-screw controller tasks remain NOT_STARTED, owned by Director:
  rhythm recall, HTM gain and coverage failed the prerequisite gate.
  No test identity is represented as real dispatch; no media was rebuilt.

Runtime evidence: `reports/htm-audio-rhythm-evidence-v1/evidence.json`.
Frozen run: `reports/htm-audio-rhythm-run-v1/`. Corpora, models, logs, caches
and generated media are ignored and not committed. Existing staged validation
bytes were preserved.

| Artifact | SHA-256 |
|---|---|
| benchmark | `38218f9dbf3554c8a68561b3940baca5822c4ce104f6f72ffe62dc2d1b3c55ef` |
| model | `7bf8b8c86e5ba6f24a81f173b1074795e19da06b3c7d0d7f6b9cfe99f81a430d` |
| calibration | `4ba7f1b97d87d01223ff64da5ea798f7f0c05ed6edcf35f5f1ca7cdca7319b00` |
| experiment | `b50f50203a144c332e260945ba765900a07bd7f70de4daeb83d8c0e9c159a1b9` |
| test_lock | `22188fb13a6151809985b4d30782fcfea9b13b288b8e7f5e8dac9a0e0edfea59` |
| dataset | `0c337bff8694f25e05395c52f1d5f3035ba475ce99a281ecde2a9465534d9a75` |
| alignment_job | `aafceee5fa60fbc805e175100f8b9e838c75e82e0c2d7ad9845a64a526fb11d5` |
| source | `67678efa5c7a8b88eb1335a4fb871ad5db3d821fa6c280af92088a68a2658d0b` |
