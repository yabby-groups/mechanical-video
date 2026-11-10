# Isolated HTM rhythm experiment

This opt-in branch tests controlled pace and interior-pause changes. It is not
contextual pace appropriateness, naturalness, expression or pronunciation QA.
ASR spelling differences never trigger repair or resynthesis. Existing acoustic
models and historical experiment directories are preserved.

## Interface and representation

Use the dedicated native runtime, with the existing command family:

```sh
reports/htm-audio-runtime/venv/bin/python -m mechanical_video.htm_audio_entry --engine rhythm train --help
reports/htm-audio-runtime/venv/bin/python -m mechanical_video.htm_audio_entry --engine rhythm calibrate --help
reports/htm-audio-runtime/venv/bin/python -m mechanical_video.htm_audio_entry --engine rhythm benchmark --help
reports/htm-audio-runtime/venv/bin/python -m mechanical_video.htm_audio_entry --engine rhythm evaluate --help
```

The installed `htm_audio_review --engine rhythm` command dispatches through this
version-neutral entrypoint, preserving the original acoustic adapter fingerprint.
The alternate module entrypoint is `mechanical_video.htm_audio_rhythm`. Outputs
use `rhythm-window-v1`; they are not interchangeable with existing acoustic QA
receipts. Evaluate returns experimental candidates and `UNQUALIFIED`, never an
automatically actionable production review. Benchmark PASS is controlled and
subtype-scoped; it does not register a controller capability. A successful
benchmark must undergo separate bridge/replay and isolated controller acceptance
before enabling any automatic dispatch.

Two-second windows advance by 0.5 seconds. A final window closes the tail; midpoint
boundaries partition the complete audio into nonoverlapping decision intervals.
These intervals, rather than unions of overlapping context windows, localize
predictions. Features include measured character/extent rate, acoustic speech
fraction, inter-character gaps, CTC support duration, local rate change, pitch
mean/variation, energy/change and voiced fraction. Sentence summaries explain
measured rate but are not a second training sequence. CTC character supports are
not phoneme boundaries or independent pronunciation evidence. Raw amplitude is
retained separately and never normalized into a passing loudness result.

Mean character confidence below 0.5, or window evidence below 0.35, leaves missing
coverage. Interior empty windows may use measured neighboring characters. No
alignment yields no feature rows, not synthetic zero-rate evidence. Invalid
windows reset temporal state and cannot train; incomplete coverage blocks the
relevant qualification. Low confidence is not relabeled as a sound defect.

Official SpatialPooler/TemporalMemory form a dedicated rhythm engine. SP/TM learn
only normal training sequences; per-dimension official Classifier instances then
learn window labels with SP/TM frozen. A window with partial positive overlap
below 50% is unknown, not negative. Fixed seed 42, three epochs, deterministic
interleaved recording order and no positive replay are the single declared
candidate. This run does not select a model using calibration or test results.

Every audio reloads the same fingerprinted checkpoint, resets TM and disables
learning. SP inference counters may change in memory; checkpoint files do not.
The C++ AnomalyLikelihood is not used. Raw anomaly remains separate from quality.

## Matched comparisons and gates

All methods use exactly the same measurements, eligibility and decision intervals:

- Rules: departure from training-normal 5th/95th character-rate percentiles, with
  an acoustic speech-fraction guard; measured maximum interior gap for pauses.
- No TM: official Classifier on the scalar input SDR alone.
- HTM: official Classifier on input SDR, TM active cells and raw anomaly SDR.

Independent calibration chooses each method/dimension threshold by grouped
localized recall minus normal and cross-defect false-alarm rates. The grid has
101 empirical quantiles plus an explicit no-alarm threshold; ties prefer fewer
normal alarms, then the higher threshold. This makes an uninformative classifier
visible rather than disguising a saturated score as a pass.

Qualification requires at least 50 independent positive, normal and known
cross-defect recording groups, localized recall >=95%, normal and cross-defect
FPR <=5%, and complete measured coverage. Positive variants within one recording
must all pass; any negative-variant alarm counts against that recording. A match
requires interval IoU >=0.5. Onset/offset errors and excess predicted duration
are reported. Global-fast, local-fast and slow subtypes are reported separately;
aggregate pace cannot conceal a failed subtype.

HTM must improve recall-minus-normal-FPR over **both** controls, with the 95%
paired original-recording bootstrap lower bound strictly above zero (2,000
resamples, seed 42). A perfect tied baseline supplies no HTM gain. Wilson intervals
accompany recall/FPR; the acceptance thresholds remain point-estimate gates,
not confidence-bound guarantees. Development reports never qualify.

## Reproducible isolated run

The pinned AISHELL source is Apache-2.0. `scripts/prepare_htm_rhythm.py` retains
prior S0002/S0003 training; prior S0004 calibration becomes explicit development.
Previously inspected S0007/S0008 test recordings are excluded. The new
[cohort](htm-audio-rhythm-cohort.json) reserves S0009 calibration and S0010/S0011
test, with unique text across partitions and exclusion of historical transcripts.
The fixed ASR vocabulary filter applies before selection; it does not imply
unsupported characters are mispronounced.

Twelve variants per original cover normal speech, short pauses, global/local
normal tempo controls, clipping, noise, long pauses, splice, masking, global
fast (1.65–1.9x), local fast (middle 60%, 1.65–1.9x) and slow (0.65–0.8x).
These are transformation labels, not independently rated acceptable/unacceptable
expression. Slow changes do not receive invented negative pause labels. Every
waveform is actually re-aligned; failed cases remain required.

```sh
PYTHONPATH=. reports/htm-audio-runtime/venv/bin/python scripts/run_htm_rhythm_experiment.py \
  --dataset reports/htm-audio-rhythm-aligned-v1/dataset.json \
  --build reports/htm-audio-runtime/build-manifest.json \
  --output reports/htm-audio-rhythm-run-v1
```

The driver freezes inputs/code/configuration, trains one candidate, records
unthresholded development diagnostics, calibrates and locks the test inputs
before test inference. `--resume` verifies completed receipts and reuses a
completed benchmark without new test inference. `--resume --replay` explicitly
recomputes and compares the entire frozen test result. Partial files without
valid receipts are not deleted or silently overwritten. All corpora, checkpoints,
feature caches, logs and generated media stay under ignored `reports/`.

If gain or coverage fails, retain `UNQUALIFIED` and the frozen failures. Do not
retune against these test results, lower the gain gate, or begin controller
repair/generation. The two new mechanical controller acceptance tasks are
conditional on eligible listening evidence; tests cannot impersonate real agent
dispatch. No subjective-rating corpus has yet met the required license and
independent Chinese quality-label conditions.
