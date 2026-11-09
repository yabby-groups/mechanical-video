# HTM audio review

This is an executable, audio-only experimental reviewer, not a qualified
replacement for independent listening or continuous audiovisual acceptance.
The current held-out smoke corpus qualifies **no dimension**. See
[measured validation](htm-audio-review-validation.md).

## Source and environment

The adapter directly calls official `htm.bindings.algorithms.SpatialPooler`,
`TemporalMemory`, `Classifier`, and `htm.bindings.sdr.SDR`. It does not implement
a substitute HTM or use C++ AnomalyLikelihood. The tracked source revision is
`0cab77fa638925e0c84a1b2aa6c7cc1258cb66f1`, exported read-only with `git archive`
from `/Users/lmj/yuntan/apps/simhash/cxx-src/htm.core`. Untracked/modified files
in that checkout are excluded. The upstream source is AGPL-3.0; no upstream
source, binary, corpus, checkpoint, or media is committed here.

Build C++ first, then the Python bindings, in a fresh directory:

```sh
.venv/bin/python scripts/build_htm_audio.py \
  --source /Users/lmj/yuntan/apps/simhash/cxx-src/htm.core \
  --work reports/htm-audio-build-new \
  --thirdparty-lock docs/htm-audio-thirdparty-lock.json
```

The builder records compiler, interpreter, platform, source archive, dependency
source-tree hashes, commands, build log and installed binding hashes. A
dependency mismatch fails before producing an accepted build manifest. The
upstream digestpp URL follows master, so the checked tree lock is required for
repeatable adoption. Toolchain/platform changes require a new build fingerprint
and retraining; a matching source revision alone is insufficient.

The measured local environment is
`reports/htm-audio-runtime/venv/bin/python`; its build manifest and logs are beside
the venv. The project extra `htm-audio` supplies NumPy, **not** an arbitrary PyPI
package named htm. Optional ASR/alignment dependencies remain separate. From the
repository root, `python -m mechanical_video.htm_audio_review` or the installed
`htm_audio_review` command provides the four subcommands below.

## Frozen corpus contract

All file references are absolute `{path, sha256}` objects. The JSON corpus is
frozen before training and contains train/calibration/test partitions. Each case:

```json
{
  "id": "unique-id", "split": "train", "recording_id": "original-recording",
  "speaker_id": "actual-speaker", "audio": {"path": "/absolute/a.wav", "sha256": "..."},
  "script": {"path": "/absolute/frozen.txt", "sha256": "..."},
  "alignment": {"path": "/absolute/alignment.json", "sha256": "..."},
  "narration_track": {"path": "/absolute/stem.wav", "sha256": "..."},
  "mix_track": {"path": "/absolute/a.wav", "sha256": "..."},
  "license": "explicit applicable license and source",
  "provenance": "source recording and transformation provenance",
  "producer": "producer identity", "labeler": "independent label source",
  "label_source": "independent_rating",
  "labels": [{"kind": "noise", "start": 1.2, "end": 1.7}],
  "quality_ratings": {"naturalness": 4.1, "expression": 3.5}
}
```

Alignment and paired tracks are optional; an unpaired track is rejected.
Alignment uses the existing `speech_alignment` measured-character contract and
must bind the actual input and frozen transcript. The mix must be the actual
evaluated audio, with a stem on the same sample clock and duration. Equality of
duration is a sanity check, not proof of correct alignment or mix intelligibility.

No recording ID, speaker, normalized text, or identical audio bytes may cross
partitions. All transformed copies retain the original recording ID. Grouped
test recall requires every defect copy in a group to be found; any normal-copy
false alarm counts against that group. License/provenance and labeler fields
are source attestations: the software cannot authenticate human ratings or
detect dishonestly renamed original recordings. Curate and freeze corpus
provenance independently; do not label a generated fixture as a human rating.

Kinds: omission, repetition, mispronunciation, clipping, noise, pause, splice,
pace, masking, naturalness, expression. Subjective training labels require
`independent_rating` and different producer/labeler identities. Synthetic
injections cannot qualify subjective dimensions. Higher quality ratings mean
better quality, on a consistent independent scale.

## Execution and outputs

```sh
HTM_PY=reports/htm-audio-runtime/venv/bin/python
$HTM_PY -m mechanical_video.htm_audio_review train --dataset corpus.json \
  --build-manifest reports/htm-audio-runtime/build-manifest.json --output reports/model-v1
$HTM_PY -m mechanical_video.htm_audio_review calibrate --dataset corpus.json \
  --model reports/model-v1 --output reports/calibration-v1.json
$HTM_PY -m mechanical_video.htm_audio_review benchmark --dataset corpus.json \
  --model reports/model-v1 --calibration reports/calibration-v1.json --output reports/benchmark-v1.json
$HTM_PY -m mechanical_video.htm_audio_review evaluate --audio actual-mix.wav \
  --script frozen.txt --alignment measured.json --narration-track stem.wav --mix-track actual-mix.wav \
  --model reports/model-v1 --calibration reports/calibration-v1.json \
  --qualified reports/benchmark-v1.json --subject-id /absolute/director-record.json \
  --output reports/review-v1.json
```

Outputs refuse overwrite. Exit codes: 0 successful training/calibration or
qualified PASS, 2 REWORK, 3 UNQUALIFIED. Invalid inputs/cold start raise an error;
they are never low-anomaly PASS. Normal training needs at least two independent
recordings/100 frames; calibration needs two independent normal recordings and
two positive recordings per enabled threshold. These are execution floors,
not production qualification sample sizes.

Full native-rate PCM decode retains all channels for raw amplitude, RMS and
clipping. A strongest channel supplies pitch; this is an autocorrelation
estimate, not phonetic recognition. The frame hop is 20 ms. Features include
energy, spectrum, F0/voicing, silence duration, deltas, measured character rate,
and optional actual stem/mix correlation and level difference. Measured
character and sentence sequences also pass through SP/TM/classifiers, with
separate reset and anomaly summaries. Character boundaries are not verified
syllables; syllable/phoneme acceptance is not implemented. Qualification currently
uses frame classifications, not a claimed multiscale quality gain.

SP/TM learn normal recordings only. Supervised classifiers learn labeled
active-cell patterns with SP/TM frozen. Calibration chooses thresholds using
only calibration cases. Every independent inference reloads the same hashed
checkpoint and resets TM; all learning is off. Runtime/feature/binary drift
rejects the checkpoint. Raw TM anomaly is reported separately and never mapped
to an overall listening score. Probabilities are not calibrated confidence.

ASR disagreement and missing terms are timecoded **candidates**. Homophones
remain uncertain; expected-text forced alignment does not establish actual
wrong-word timing. Text dimensions require alignment and remain UNQUALIFIED
when recognition disagrees. The baseline includes conservative amplitude and
silence rules plus available recognition/alignment candidates. Without actual
recognition in a corpus, it cannot validate text-review performance.

Qualification requires, per dimension, at least 50 original test recording
groups with defects and 50 normal groups, recall >=95%, normal FPR <=5%, and
positive HTM gain over the baseline. Reports include Wilson 95% intervals and
onset localization error. Subjective dimensions additionally require >=50
independent rated groups and Spearman >=0.7. Insufficient, equal-to-baseline,
or worse performance remains UNQUALIFIED. Ground-truth intervals must be
independently sound; any temporal overlap counts as a detection, so inspect
localization error and interval overreach before adopting a dimension.

Calibration thresholds and case IDs are reproduced from the frozen calibration
partition before use; a test-tuned threshold JSON is rejected. Checkpoint
manifests must fingerprint the exact complete set of SP, TM and classifiers.
Capability validation verifies every frozen input/checkpoint, recomputes
metrics and reruns held-out inference, comparing probabilities, alignment,
tracks, coverage, dimensions and the baseline. Cached results are reused only
after checking those immutable inputs again. Caches are process-local; a new CLI
process can repeat full calibration and held-out inference, which may be costly
for a large qualification corpus. Incoming audio QA/controller
reports also rerun the actual audio, so editing a consistent JSON result is
insufficient to enable PASS.

## QA and repairs

`audio_qa --htm-review report.json` attaches verified narrow evidence and can
propagate REWORK. Existing score fields remain independent. The controller can
register `htm_audio:<kind>` with absolute model, calibration and qualification
paths; it does not register this tool as `audio` or `continuous_av`.

`htm_audio_bridge.complete_review(record, task_id, actual_agent_id, completion_id,
report, repair_outputs)` requires an already claimed independent review. The
report subject must be the canonical controller record path. Stable issue IDs
bind that subject and dimension, retaining all affected intervals so removal
of one defect cannot renumber another. Repairs preserve remeasured alignment,
neighbor continuity, final mix and independent recheck requirements. Only HTM
checks can be completed by this adapter; the extra checks need their actual
independent evidence through the existing controller.

Unqualified dimensions create owned Director dependencies. Explicit new output
paths are required. Existing repair limits, independent identities and
idempotent completion IDs remain in force. No synthesis, repair command,
upload, publication or paid operation is launched by this adapter. A qualified
detector does not grant narration-generation authorization. Local replacements
must use available authorized assets, remeasure affected speech/captions and
verify neighboring segments and the actual final mix before closing a defect.

To reproduce the development controls with local eSpeak and original text:

```sh
$HTM_PY scripts/smoke_htm_audio.py --output reports/htm-smoke-new \
  --build-manifest reports/htm-audio-runtime/build-manifest.json
```

This intentionally small synthetic corpus is not a qualification dataset.
