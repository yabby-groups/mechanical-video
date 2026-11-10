"""Prepare an isolated, grouped Chinese acoustic-defect corpus from AISHELL-1.

Requires a hash-verified source-manifest.json and the upstream license page.
Original source recordings stay immutable. No subjective ratings are invented.
"""
import argparse
import hashlib
import io
import json
import re
from pathlib import Path
import subprocess
import tarfile
import wave

import numpy as np

from mechanical_video.htm_audio_features import ref,verify,sha
from mechanical_video.htm_audio_model import load_dataset
from mechanical_video.htm_audio_review import write_new
from mechanical_video.speech_alignment import normalize

REVISION='bbe295d530192a4cd41644b711c9aecd087df653'
PLAN={'S0002':('train',12),'S0003':('train',12),'S0004':('calibration',16),
      'S0005':('test',30),'S0006':('test',30)}


# A synthetic mechanism is not proof that all other dimensions are absent.
# Exclude physically coupled mechanisms from negative labels.
NEGATIVES = {
    'clipping': ['pause', 'pace', 'masking'],
    'noise': ['pause', 'pace', 'splice'],
    'pause': ['clipping', 'noise', 'splice', 'pace', 'masking'],
    'splice': ['pause', 'pace', 'masking'],
    'pace': ['clipping', 'noise', 'pause', 'masking'],
    'masking': ['pause', 'pace', 'splice'],
}
ACOUSTIC = ['clipping', 'noise', 'pause', 'splice', 'pace', 'masking']

def negative_kinds(case):
    kind = case['provenance']['transformation']
    return list(ACOUSTIC if kind.startswith('normal') else NEGATIVES[kind])

def annotate(data):
    for case in data['cases']:
        case['negative_kinds'] = negative_kinds(case)
    data['negative_label_policy'] = {
        'version': 1, 'matrix': NEGATIVES,
        'scope': 'Known injected acoustic mechanisms only; coupled or subjective dimensions omitted.'}
    return data

def read(data):
    with wave.open(io.BytesIO(data),'rb') as stream:
        if stream.getsampwidth()!=2 or stream.getnchannels()!=1:
            raise ValueError('expected 16-bit mono source')
        return np.frombuffer(stream.readframes(stream.getnframes()),'<i2').astype(float)/32768,stream.getframerate()


def save(path,x,rate):
    with wave.open(str(path),'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(rate)
        stream.writeframes((np.clip(x,-1,1)*32767).astype('<i2').tobytes())


def prepare(source,output,plan=None,exclude_datasets=(),vocabulary=None):
    source,output=Path(source).resolve(),Path(output).resolve()
    plan = PLAN if plan is None else plan
    if (not plan or any(not re.fullmatch(r'S[0-9]{4}', speaker) or len(item)!=2
        or item[0] not in ('train','calibration','development','test')
        or type(item[1]) is not int or item[1]<1 for speaker,item in plan.items())):
        raise ValueError('invalid predeclared speaker plan')
    supported = set(json.loads(Path(vocabulary).read_text())) if vocabulary else None
    excluded_texts=set()
    for path in exclude_datasets:
        old=load_dataset(path)
        excluded_texts.update(normalize(Path(c['script']['path']).read_text()) for c in old['cases'])
    manifest=json.loads((source/'source-manifest.json').read_text())
    if manifest['revision']!=REVISION or manifest['license']!='Apache-2.0':
        raise ValueError('unexpected source revision or license')
    for item in manifest['files']:
        verify({'path':item['path'],'sha256':item['sha256']})
    license_path=source/'upstream-license.html'
    if b'Apache License v.2.0' not in license_path.read_bytes():
        raise ValueError('missing original license evidence')
    transcript={}
    for line in (source/'aishell_transcript_v0.8.txt').read_text().splitlines():
        parts=line.split()
        if len(parts)>1:transcript[parts[0]]=''.join(parts[1:])
    output.mkdir(parents=True,exist_ok=False)
    originals=output/'originals';originals.mkdir()
    derived=output/'derived';derived.mkdir()
    cases=[];selection=[];seen_text=set(excluded_texts)
    kinds=('normal','normal_short_pause','normal_tempo','clipping','noise','pause','splice','pace','masking')
    for speaker,(split,count) in plan.items():
        selected=0
        with tarfile.open(source/(speaker+'.tar.gz')) as archive:
            members=[m for m in archive.getmembers() if m.isfile() and m.name.endswith('.wav')]
            members.sort(key=lambda m:hashlib.sha256(('htm-independent-v1:'+m.name).encode()).hexdigest())
            for member in members:
                utterance=Path(member.name).stem
                text=transcript.get(utterance,'')
                if not text or normalize(text) in seen_text:continue
                if supported is not None and any(c not in supported for c in normalize(text)):continue
                raw=archive.extractfile(member).read();x,rate=read(raw);duration=len(x)/rate
                if not 2.5<=duration<=8:continue
                seen_text.add(normalize(text));selected+=1
                original=originals/(utterance+'.wav');original.write_bytes(raw)
                script=originals/(utterance+'.txt');script.write_text(text+'\n')
                selection.append(dict(id=utterance,speaker=speaker,split=split,audio=ref(original),script=ref(script)))
                rng=np.random.default_rng(int(hashlib.sha256(utterance.encode()).hexdigest()[:8],16))
                # Choose a small-amplitude interior boundary to avoid adding an
                # unrelated click when inserting a known synthetic pause.
                left,right=round(duration*.3*rate),round(duration*.6*rate)
                anchor=left+int(np.argmin(np.abs(x[left:right])))
                stop=min(len(x),anchor+round(.8*rate));start=anchor/rate
                for kind in kinds:
                    y=x.copy();stem=original;labels=[]
                    if kind=='normal':
                        audio=original
                    else:
                        audio=derived/(utterance+'-'+kind+'.wav')
                        end=stop/rate
                        if kind in ('normal_short_pause','pause'):
                            length=(float(rng.uniform(.18,.55)) if kind=='normal_short_pause' else float(rng.uniform(1.8,2.8)))
                            extra=np.zeros(round(length*rate));y=np.r_[x[:anchor],extra,x[anchor:]]
                            end=start+len(extra)/rate
                        elif kind in ('normal_tempo','pace'):
                            speed=float(rng.uniform(.92,1.1)) if kind=='normal_tempo' else float(rng.uniform(1.65,1.9))
                            subprocess.run(['ffmpeg','-v','error','-i',str(original),'-af','atempo='+str(speed),str(audio)],check=True)
                            y,_=read(audio.read_bytes());start=0.;end=len(y)/rate
                        elif kind=='clipping':
                            ceiling=float(rng.choice([.55,1.]))
                            segment=x[anchor:stop];gain=max(8.,ceiling/max(np.quantile(np.abs(segment),.65),1e-4))
                            y[anchor:stop]=np.clip(segment*gain,-ceiling,ceiling)
                        elif kind=='noise':
                            segment=x[anchor:stop];rms=max(1e-4,float(np.sqrt(np.mean(segment**2))))
                            noise=rng.normal(0,rms*10**(-float(rng.uniform(-2,8))/20),len(segment))
                            y[anchor:stop]+=noise
                        elif kind=='splice':
                            n=min(stop-anchor,round(.2*rate));y[anchor:anchor+n]=x[anchor:anchor+n][::-1]
                            y[anchor:anchor+n]+=float(rng.choice([-.2,.2]));end=(anchor+n)/rate
                        elif kind=='masking':
                            rms=max(1e-4,float(np.sqrt(np.mean(x[anchor:stop]**2))))
                            y[anchor:stop]+=rms*3*np.sin(2*np.pi*float(rng.uniform(160,600))*np.arange(stop-anchor)/rate)
                        if kind not in ('normal_tempo','pace'):save(audio,y,rate)
                        if kind in ('normal_short_pause','normal_tempo','pause','pace'):stem=audio
                        if not kind.startswith('normal'):labels=[dict(kind=kind,start=start,end=end)]
                    cases.append(dict(id=utterance+'-'+kind,split=split,recording_id=utterance,speaker_id=speaker,
                        audio=ref(audio),script=ref(script),narration_track=ref(stem),mix_track=ref(audio),
                        labels=labels,license='Apache-2.0',license_evidence=ref(license_path),
                        provenance=dict(source=ref(source/'source-manifest.json'),original=ref(original),
                                        transformation=kind,seed='SHA256(recording id)'),
                        producer='deterministic-acoustic-transform',labeler='known-waveform-transform',
                        label_source='synthetic_injection_on_real_speech',topic='Mandarin read speech'))
                    start=anchor/rate
                if selected==count:break
        if selected!=count:raise ValueError('not enough distinct utterances for '+speaker)
    dataset=output/'dataset.json'
    write_new(dataset,annotate(dict(schema_version=2,source=ref(source/'source-manifest.json'),cases=cases,
        scope='Acoustic perturbations of licensed real speech; no subjective quality labels or lexical qualification.',
        selection=selection,selection_plan=plan,alignment_vocabulary=ref(vocabulary) if vocabulary else None,excluded_datasets=[ref(p) for p in exclude_datasets],selection_policy='Predeclared speakers; SHA256 order; unique normalized text; duration 2.5..8 s')))
    load_dataset(dataset)
    print(dataset)
    return dataset


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--plan',help='JSON speaker -> [split, count], frozen before preparation')
    parser.add_argument('--exclude-dataset',action='append',default=[],help='Exclude every previously observed normalized transcript')
    parser.add_argument('--vocabulary',help='Optional fixed CTC vocabulary JSON; predeclared transcript eligibility only')
    args=parser.parse_args()
    prepare(args.source,args.output,json.loads(Path(args.plan).read_text()) if args.plan else None,args.exclude_dataset,args.vocabulary)
