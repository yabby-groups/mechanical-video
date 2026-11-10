"""Measure every corpus audio with one frozen local CTC model; resume by receipts.

No synthesized timing, scaled timestamp copies, or silent failed-case removal.
ASR spelling differences remain evidence, not repair instructions.
"""
import argparse
import copy
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import shutil

from .htm_audio_features import ref, verify
from .htm_audio_model import load_dataset
from .htm_audio_review import write_new
from .speech_alignment import CTCAligner, normalize


def validate_measured(value, case, job):
    if (value.get('method') != 'forced_alignment' or value.get('audio') != case['audio']
            or value.get('source_script') != case['script'] or value.get('alignment_job') != job
            or normalize(value.get('transcript', '')) != normalize(Path(case['script']['path']).read_text())):
        raise ValueError('alignment receipt does not bind the frozen inputs/job')
    chars = value.get('characters', [])
    duration = value.get('duration')
    if (not isinstance(duration, (int,float)) or not math.isfinite(duration) or duration <= 0
            or not chars or ''.join(c['text'] for c in chars) != normalize(value['transcript'])):
        raise ValueError('alignment has incomplete measured characters')
    previous = 0.
    for char in chars:
        if (not all(isinstance(char[k], (int,float)) and math.isfinite(char[k]) for k in ('start','end','confidence'))
                or not 0 <= previous <= char['start'] < char['end'] <= duration
                or not 0 <= char['confidence'] <= 1):
            raise ValueError('alignment has invalid measured character bounds')
        previous = char['end']


def align_corpus(dataset, output, model, revision, device='cpu', resume=False):
    dataset, output, model = Path(dataset).resolve(), Path(output).resolve(), Path(model).resolve()
    source = ref(dataset)
    data = load_dataset(dataset)
    verify(source)
    if not model.is_dir() or not revision:
        raise ValueError('a local frozen ASR snapshot and exact revision are required')
    from . import speech_alignment
    job = dict(schema_version=1, dataset=source, revision=revision, device=device,
               model_files=[ref(p) for p in sorted(model.iterdir()) if p.is_file()],
               implementation=[ref(__file__), ref(speech_alignment.__file__)],
               packages={name: importlib.metadata.version(name) for name in ('torch','transformers','numpy')},
               ffmpeg=ref(shutil.which('ffmpeg')),
               cases=[c['id'] for c in data['cases']],
               scope='Actual CTC measurements on each waveform; no phonetic or perceptual acceptance.')
    if not job['model_files']:
        raise ValueError('empty local ASR snapshot')
    job_path = output/'job.json'
    if output.exists():
        if not resume or not job_path.is_file() or json.loads(job_path.read_text()) != job:
            raise ValueError('existing alignment job differs; use a new output or matching --resume')
    else:
        output.mkdir(parents=True)
        (output/'alignments').mkdir()
        write_new(job_path, job)
    job_ref = ref(job_path)
    aligned = copy.deepcopy(data)
    engine = None
    for index, case in enumerate(aligned['cases']):
        path = output/'alignments'/(hashlib.sha256(case['id'].encode()).hexdigest()+'.json')
        receipt = path.with_suffix('.receipt.json')
        for key in ('audio','script'):
            verify(case[key])
        if path.exists():
            if not receipt.is_file():
                raise ValueError('alignment lacks a completed receipt; preserve it and use a new output')
            saved=json.loads(receipt.read_text())
            if saved != ref(path):
                raise ValueError('alignment receipt fingerprint differs from its output')
            verify(saved)
            value = json.loads(path.read_text())
        else:
            if engine is None:
                engine = CTCAligner(model, revision, device=device)
            # Failures stop the job. Every frozen case remains required; callers
            # may explicitly resume completed receipts after resolving a cause.
            value = engine.align(case['audio']['path'], Path(case['script']['path']).read_text())
            value.update(source_script=case['script'], alignment_job=job_ref)
            for key in ('audio','script'):
                verify(case[key])
            validate_measured(value, case, job_ref)
            write_new(path, value)
            write_new(receipt, ref(path))
        validate_measured(value, case, job_ref)
        case['alignment'] = ref(path)
        if (index+1) % 25 == 0 or index+1 == len(aligned['cases']):
            print(f"aligned {index+1}/{len(aligned['cases'])}", flush=True)
    verify(source)
    for item in job['model_files'] + job['implementation'] + [job['ffmpeg']]:
        verify(item)
    aligned['alignment_job'] = job_ref
    target = output/'dataset.json'
    if target.exists():
        if json.loads(target.read_text()) != aligned:
            raise ValueError('completed aligned dataset differs from frozen receipts')
    else:
        write_new(target, aligned)
    load_dataset(target)
    print(target, flush=True)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--device', choices=('cpu','mps'), default='cpu')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    align_corpus(args.dataset, args.output, args.model, args.revision, args.device, args.resume)


if __name__ == '__main__':
    main()
