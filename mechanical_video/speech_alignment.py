"""Local CTC forced alignment of existing narration; never synthesizes speech.

The transcript must describe all speech in the input. Results measure timing,
not perceptual quality or mechanical correctness. Dependencies are optional.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import unicodedata


def normalize(text):
    return ''.join(c.lower() for c in text if unicodedata.category(c)[0] in 'LN')


def ctc_path(log_probs, tokens, blank):
    """Viterbi alignment with CTC repeat/blank constraints, including final blank."""
    import numpy as np
    p = np.asarray(log_probs)
    if p.ndim != 2 or not np.isfinite(p).all() or not tokens or blank in tokens:
        raise ValueError('invalid CTC emissions or transcript')
    if min(tokens + [blank]) < 0 or max(tokens + [blank]) >= p.shape[1]:
        raise ValueError('token outside vocabulary')
    states = np.full(2 * len(tokens) + 1, blank, dtype=int)
    states[1::2] = tokens
    previous = np.full(len(states), -np.inf)
    previous[0] = p[0, blank]
    previous[1] = p[0, tokens[0]]
    parents = np.zeros((len(p), len(states)), dtype=np.int8)
    skip = (states != blank) & (states != np.roll(states, 2))
    skip[:2] = False
    for t in range(1, len(p)):
        advance = np.r_[-np.inf, previous[:-1]]
        jump = np.r_[-np.inf, -np.inf, previous[:-2]]
        jump[~skip] = -np.inf
        choices = np.stack([previous, advance, jump])
        parents[t] = choices.argmax(axis=0)
        previous = choices.max(axis=0) + p[t, states]
    state = len(states) - 2 + int(previous[-1] > previous[-2])
    if not np.isfinite(previous[state]):
        raise ValueError('speech too short to align transcript')
    path = np.empty(len(p), dtype=int)
    for t in range(len(p)-1, -1, -1):
        path[t] = state
        state -= int(parents[t, state])
    spans = []
    for i, token in enumerate(tokens):
        frames = np.flatnonzero(path == 2*i+1)
        if not len(frames):
            raise ValueError('uncovered transcript token')
        spans.append((int(frames[0]), int(frames[-1])+1,
                      float(np.exp(p[frames, token]).mean())))
    return spans


def recognized_units(ids, probabilities, tokenizer, step, offset, duration):
    """Collapse actual CTC runs; retain repeated tokens separated by a blank."""
    import numpy as np
    ids=np.asarray(ids);probabilities=np.asarray(probabilities)
    if (ids.ndim!=1 or not len(ids) or probabilities.ndim!=2 or len(ids)!=len(probabilities)
            or not np.isfinite(probabilities).all() or ids.min()<0 or ids.max()>=probabilities.shape[1]
            or not all(math.isfinite(v) for v in (step,offset,duration)) or step<=0 or duration<=0):
        raise ValueError('invalid actual CTC token timing input')
    recognized=[];run_start=0;special=set(tokenizer.all_special_ids)
    for end in range(1,len(ids)+1):
        if end<len(ids) and ids[end]==ids[run_start]:continue
        token=int(ids[run_start])
        text_unit=normalize(tokenizer.decode([token],group_tokens=False))
        if token not in special and text_unit:
            start,stop=run_start*step+offset,min(end*step+offset,duration)
            if not 0<=start<stop<=duration:raise ValueError('CTC unit outside actual audio')
            recognized.append(dict(text=text_unit,start=start,end=stop,
                confidence=float(np.exp(probabilities[run_start:end,token]).mean()),
                frame_start=run_start,frame_end=end))
        run_start=end
    return recognized


class CTCAligner:
    """Reuse one frozen ASR network; every call decodes the actual audio anew."""

    def __init__(self, model, revision=None, device='cpu'):
        import torch
        from transformers import AutoProcessor, AutoModelForCTC
        if device not in ('cpu', 'mps'):
            raise ValueError('unsupported alignment device')
        if device == 'mps' and not torch.backends.mps.is_available():
            raise ValueError('requested MPS alignment is unavailable')
        self.model, self.revision, self.device = str(model), revision, device
        self.processor = AutoProcessor.from_pretrained(model, revision=revision)
        self.network = AutoModelForCTC.from_pretrained(model, revision=revision).eval().to(device)

    def align(self, audio, text):
        import numpy as np
        import torch
        audio = Path(audio).resolve()
        source_hash = hashlib.sha256(audio.read_bytes()).hexdigest()
        pcm = subprocess.run(['ffmpeg','-v','error','-i',str(audio),'-f','f32le',
                              '-ar','16000','-ac','1','-'], check=True, capture_output=True).stdout
        samples = np.frombuffer(pcm, dtype='<f4').copy()
        if not len(samples) or not np.isfinite(samples).all():
            raise ValueError('empty or invalid audio')
        processor, network = self.processor, self.network
        transcript = normalize(text)
        vocab = processor.tokenizer.get_vocab()
        if not transcript or any(c not in vocab for c in transcript):
            raise ValueError('transcript contains unsupported characters')
        tokens = [vocab[c] for c in transcript]
        inputs = processor(samples, sampling_rate=16000, return_tensors='pt').to(self.device)
        with torch.inference_mode():
            logits = network(**inputs).logits[0]
            probabilities = logits.log_softmax(-1).cpu().numpy()
        greedy_ids = logits.argmax(-1).cpu().numpy()
        greedy = processor.batch_decode(torch.tensor(greedy_ids).unsqueeze(0))[0]
        frames = ctc_path(probabilities, tokens, network.config.pad_token_id)
        # Use the convolution stride, not proportional paragraph durations.
        step = int(np.prod(network.config.conv_stride)) / 16000
        duration = len(samples) / 16000
        receptive, stride = 1, 1
        for kernel, hop in zip(network.config.conv_kernel, network.config.conv_stride):
            receptive += (kernel - 1) * stride
            stride *= hop
        offset = (receptive - stride) / (2 * 16000)
        recognized = recognized_units(greedy_ids,probabilities,processor.tokenizer,step,offset,duration)
        if hashlib.sha256(audio.read_bytes()).hexdigest() != source_hash:
            raise ValueError('audio changed during alignment')
        return dict(schema_version=1, method='forced_alignment',
                    audio=dict(path=str(audio), sha256=source_hash), duration=duration,
                    model=self.model, revision=getattr(network.config, '_commit_hash', None) or self.revision,
                    transcript=text, normalized_transcript=transcript, greedy_transcript=greedy,
                    frame_seconds=step, frame_offset_seconds=offset, boundary_quantization_seconds=step/2,
                    recognition_units=recognized,
                    recognition_scope='greedy CTC token timings measured independently of expected-text path; not listening acceptance',
                    characters=[dict(text=c,start=a*step+offset,end=min(b*step+offset,duration),confidence=q)
                                for c,(a,b,q) in zip(transcript, frames)],
                    scope='CTC timing candidate; independent review required before acceptance')

def align(audio, text, model, revision=None):
    return CTCAligner(model, revision).align(audio, text)


def measurement_from_alignment(events, alignment_path, minimum_similarity=0.7):
    """Bind explicit phrases to measured characters, rejecting untrusted candidates.

    Greedy agreement is a sanity check, not independent listening acceptance.
    Repeated phrases are consumed in order; missing/overlapping phrases fail.
    """
    from difflib import SequenceMatcher
    from .scene_fidelity import file_ref
    if not 0.7 <= minimum_similarity <= 1:
        raise ValueError('alignment sanity threshold cannot be weakened')
    report = json.loads(Path(alignment_path).read_text())
    if report.get('method') != 'forced_alignment' or file_ref(report['audio']['path']) != report['audio']:
        raise ValueError('stale or unsupported speech alignment')
    text = normalize(report['transcript'])
    chars = report['characters']
    if text != ''.join(c['text'] for c in chars) or text != report['normalized_transcript']:
        raise ValueError('alignment transcript differs from measured characters')
    similarity = SequenceMatcher(None, text, normalize(report['greedy_transcript']), autojunk=False).ratio()
    if similarity < minimum_similarity:
        raise ValueError('recognized speech disagrees with supplied transcript')
    duration=report['duration']
    numeric=lambda v: type(v) in (int,float) and math.isfinite(v)
    if not numeric(duration) or duration <= 0:
        raise ValueError('invalid alignment duration')
    previous=0
    for c in chars:
        if (not all(numeric(c.get(k)) for k in ('start','end','confidence'))
                or not 0 <= previous <= c['start'] < c['end'] <= duration
                or not 0 <= c['confidence'] <= 1):
            raise ValueError('invalid measured character interval or confidence')
        previous=c['end']
    greedy=normalize(report['greedy_transcript'])
    spans=[]; cursor=0; greedy_cursor=0
    for event in events:
        phrase=normalize(event['phrase'])
        start=text.find(phrase,cursor)
        if not phrase or start < 0:
            raise ValueError('event phrase absent or out of order')
        greedy_start=greedy.find(phrase,greedy_cursor)
        if greedy_start < 0:
            raise ValueError('event phrase not independently supported by greedy recognition')
        greedy_cursor=greedy_start+len(phrase)
        selected=chars[start:start+len(phrase)]
        if any(not 0 <= c['confidence'] <= 1 for c in selected) or sum(c['confidence'] for c in selected)/len(selected) < .05:
            raise ValueError('event has insufficient acoustic support')
        spans.append(dict(event_id=event['id'],text=event['phrase'],start=selected[0]['start'],end=selected[-1]['end']))
        cursor=start+len(phrase)
    return dict(method='forced_alignment',audio=report['audio'],evidence=file_ref(alignment_path),
                duration=report['duration'],spans=spans)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', required=True)
    parser.add_argument('--transcript', required=True, help='UTF-8 file containing all spoken words')
    parser.add_argument('--model', required=True)
    parser.add_argument('--revision')
    parser.add_argument('--output', required=True)
    parser.add_argument('--events', help='JSON action events to bind to measured speech')
    parser.add_argument('--timeline', help='New event timeline path; requires --events')
    args=parser.parse_args()
    if bool(args.events) != bool(args.timeline):
        parser.error('--events and --timeline must be supplied together')
    if args.timeline and Path(args.timeline).exists():
        parser.error('timeline exists; choose a new version')
    if Path(args.output).exists():
        parser.error('output exists; choose a new version')
    result=align(args.audio, Path(args.transcript).read_text(), args.model, args.revision)
    with open(args.output, 'x') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
        stream.write('\n')
    if args.events:
        from .event_timeline import build
        events=json.loads(Path(args.events).read_text())
        measurement=measurement_from_alignment(events,args.output)
        timeline=build(events,measurement,args.audio,args.output)
        with open(args.timeline,'x') as stream:
            json.dump(timeline,stream,ensure_ascii=False,indent=2)
            stream.write('\n')

if __name__ == '__main__':
    main()
