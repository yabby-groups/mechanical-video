"""Reproducible isolated local speech controls; NEVER a qualification corpus.

No provider calls, old production assets, or human-quality labels. Original
test sentences are CC0. eSpeak is used locally; generated speech is test media.
Run with the dedicated HTM Python from the production repository root.
"""
import argparse
import json
from pathlib import Path
import subprocess
import wave

import numpy as np

from mechanical_video.htm_audio_features import ref, sha
from mechanical_video.htm_audio_review import train, calibrate, evaluate, benchmark, write_new


def read_wav(path):
    with wave.open(str(path), 'rb') as stream:
        return np.frombuffer(stream.readframes(stream.getnframes()), '<i2').astype(float)/32768, stream.getframerate()


def save_wav(path, x, rate):
    with wave.open(str(path),'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(rate)
        stream.writeframes((np.clip(x,-1,1)*32767).astype('<i2').tobytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True); p.add_argument('--build-manifest',required=True)
    a=p.parse_args(); root=Path(a.output).resolve(); root.mkdir(parents=True,exist_ok=False)
    rng=np.random.default_rng(42)
    cases=[]
    kinds=('normal','omission','repetition','mispronunciation','clipping','noise','pause','splice','pace','masking')
    topics=('tape-measure','click-pen')
    scripts={
        'train': ('A spring pulls the tape into the case.', 'The pen button moves a small cam.'),
        'calibration': ('The tape reel turns as the spring relaxes.', 'A cam holds the refill against its spring.'),
        'test': ('The tape lock presses against the moving strip.', 'Pressing the pen releases the rotating cam.'),
    }
    voices={'train':'en-us','calibration':'en-sc','test':'en'}
    for split in scripts:
        for topic_index,topic in enumerate(topics):
            for kind in kinds:
                name=f'{split}-{topic}-{kind}'
                script=root/(name+'.txt'); audio=root/(name+'.wav')
                text=scripts[split][topic_index]+' This is a separate '+kind+' control.'
                script.write_text(text+'\n')
                spoken=text
                if kind=='omission': spoken=text.split('.')[0]+'.'
                if kind=='repetition': spoken=text+' '+text.split('.')[0]+'.'
                if kind=='mispronunciation': spoken=text.replace('spring','string').replace('cam','cat').replace('lock','rock')
                subprocess.run(['espeak','-v',voices[split],'-s','165','-w',str(audio),spoken],check=True)
                x,rate=read_wav(audio); stem=x.copy(); start,end=.4,min(1.4,len(x)/rate)
                lo,hi=round(start*rate),round(end*rate)
                if kind=='clipping': x[lo:hi]=np.clip(x[lo:hi]*30,-1,1)
                elif kind=='noise': x[lo:hi]+=rng.normal(0,.3,hi-lo)
                elif kind=='pause':
                    x=np.r_[x[:lo],np.zeros(2*rate),x[lo:]]; stem=x.copy(); end=start+2
                elif kind=='splice': x[lo:hi]+=np.tile([.7,-.7],(hi-lo+1)//2)[:hi-lo]
                elif kind=='pace': x=np.interp(np.arange(0,len(x),1.8),np.arange(len(x)),x); stem=x.copy(); start=0.; end=len(x)/rate
                elif kind=='masking': x[lo:hi]+=.6*np.sin(2*np.pi*250*np.arange(hi-lo)/rate)
                if kind in ('omission','repetition','mispronunciation'): start=0.; end=len(x)/rate
                save_wav(audio,x,rate)
                stem_path=root/(name+'-stem.wav'); save_wav(stem_path,stem,rate)
                cases.append(dict(id=name,split=split,recording_id=name,speaker_id=voices[split],
                    audio=ref(audio),script=ref(script),labels=[] if kind=='normal' else [dict(kind=kind,start=start,end=end)],
                    narration_track=ref(stem_path),mix_track=ref(audio),
                    license='CC0 original synthetic test speech; not a human quality corpus',
                    provenance='local eSpeak; procedural known transformation, no production media',
                    label_source='synthetic_injection',labeler='deterministic-transform',producer='espeak-smoke',
                    topic=topic))
    dataset=root/'dataset.json'; write_new(dataset,{'schema_version':1,'cases':cases})
    model=root/'model'; cal=root/'calibration.json'; bench=root/'benchmark.json'
    train(dataset,model,a.build_manifest,epochs=3)
    calibrate(dataset,model,cal)
    report=benchmark(dataset,model,cal,bench)
    for topic in topics:
        c=next(c for c in cases if c['split']=='test' and c['topic']==topic and c['id'].endswith('clipping'))
        kwargs=dict(qualified=bench,subject_id=str(root/(topic+'-controller.json')),
                    narration_track=c['narration_track']['path'],mix_track=c['mix_track']['path'])
        first=evaluate(c['audio']['path'],c['script']['path'],model,cal,**kwargs)
        second=evaluate(c['audio']['path'],c['script']['path'],model,cal,**kwargs)
        if first != second: raise AssertionError('frozen inference changed on replay')
        write_new(root/(topic+'-review.json'),first)
    write_new(root/'smoke-summary.json',{'status':report['status'],'benchmark':ref(bench),
        'cases':len(cases),'dimensions':report['dimensions'],'frozen_replay':True,
        'scope':'actual HTM execution on local synthetic controls, not qualification or listening acceptance'})
    print(root/'smoke-summary.json')


if __name__=='__main__': main()
