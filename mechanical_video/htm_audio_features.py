"""Complete PCM decode and bounded, versioned acoustic features (no loudness gain).

The first stream is decoded at its native sample rate, retaining every channel
for amplitude checks. Pitch is a simple autocorrelation estimate, not phonetics.
"""
import hashlib
from functools import lru_cache
import json
import re
from pathlib import Path
import subprocess

import numpy as np

VERSION = 2
HOP_SECONDS = .02
FEATURES = ('rms_db', 'peak', 'clipped_fraction', 'centroid', 'flatness',
            'zcr', 'pitch_hz', 'voicing', 'silence', 'energy_delta',
            'spectral_flux', 'speech_rate', 'gap_seconds')
FEATURES += ('paired_tracks', 'mix_voice_correlation', 'mix_level_delta')
BOUNDS = ((-100, 0), (0, 1.5), (0, .2), (0, 1), (0, 1), (0, 1),
          (0, 500), (0, 1), (0, 1), (-40, 40), (0, 2), (0, 20), (0, 3))
BOUNDS += ((0, 1), (-1, 1), (-40, 40))


def _version(path):
    stat = Path(path).stat()
    return stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns


@lru_cache(maxsize=16384)
def _version_sha(path, version):
    with Path(path).open('rb') as stream:
        result = hashlib.file_digest(stream, 'sha256').hexdigest()
    if _version(path) != version:
        raise ValueError('file changed during fingerprinting: '+path)
    return result


def sha(path):
    path = str(Path(path).resolve())
    # ctime catches same-size edits even if a caller restores mtime. Every
    # immutable file version is fully hashed once per process; no disk cache.
    return _version_sha(path, _version(path))


def ref(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha(path)}


def verify(reference):
    if ref(reference['path']) != reference:
        raise ValueError('stale evidence: ' + reference['path'])


def decode(path):
    before = ref(path)
    info = json.loads(subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_streams',
         '-of', 'json', str(path)], check=True, capture_output=True).stdout)['streams'][0]
    rate, channels = int(info['sample_rate']), int(info['channels'])
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0',
                          '-f', 'f32le', '-'], check=True, capture_output=True).stdout
    pcm = np.frombuffer(raw, dtype='<f4').reshape(-1, channels)
    if not len(pcm) or not np.isfinite(pcm).all():
        raise ValueError('empty or invalid decoded PCM')
    verify(before)
    return pcm, rate, before


def extract(audio, alignment=None, narration_track=None, mix_track=None):
    pcm, rate, source = decode(audio)
    duration = len(pcm) / rate
    paired = None
    paired_times = None
    tracks = {}
    if bool(narration_track) != bool(mix_track):
        raise ValueError('paired-track features require narration and actual mix together')
    if narration_track:
        voice, voice_rate, voice_ref = decode(narration_track)
        if ref(mix_track) != source:
            raise ValueError('mix track must be the actual evaluated audio')
        if abs(len(voice)/voice_rate-duration) > .02:
            raise ValueError('paired tracks must share the same measured clock and duration')
        paired = voice.mean(axis=1)
        paired_times = np.arange(len(paired))/voice_rate
        tracks = {'narration': voice_ref, 'mix': source}
    chars = []
    alignment_ref = None
    if alignment is not None:
        from .speech_alignment import normalize
        alignment_ref = ref(alignment)
        data = json.loads(Path(alignment).read_text())
        if data.get('method') != 'forced_alignment' or data['audio'] != source:
            raise ValueError('alignment must bind the actual audio')
        if abs(data['duration'] - duration) > .05:
            raise ValueError('alignment duration mismatch')
        chars = data['characters']
        if ''.join(c['text'] for c in chars) != normalize(data['transcript']):
            raise ValueError('incomplete alignment characters')
        previous = 0
        for c in chars:
            if (not all(np.isfinite(c[k]) for k in ('start', 'end', 'confidence'))
                    or not 0 <= previous <= c['start'] < c['end'] <= duration
                    or not 0 <= c['confidence'] <= 1):
                raise ValueError('invalid measured character span')
            previous = c['end']
        verify(alignment_ref)
    # Select strongest channel for pitch; retain all channels for raw amplitude.
    mono = pcm[:, int(np.argmax(np.mean(pcm.astype(float)**2, axis=0)))]
    hop = max(1, round(rate * HOP_SECONDS))
    window = max(hop, round(rate * .04))
    rows, intervals = [], []
    previous_db, previous_spectrum, silence_start = None, None, None
    for offset in range(0, len(pcm), hop):
        raw = pcm[offset:min(offset + hop, len(pcm))].astype(float)
        signal = mono[offset:min(offset + window, len(pcm))].astype(float)
        rms_db = float(20*np.log10(max(1e-5, np.sqrt(np.mean(raw**2)))))
        spectrum = np.abs(np.fft.rfft(signal * np.hanning(len(signal)))) + 1e-12
        spectrum /= spectrum.sum()
        frequencies = np.fft.rfftfreq(len(signal), 1/rate)
        centered = signal - signal.mean()
        # FFT autocorrelation bounds computation even for high-rate source audio.
        nfft = 1 << (2*len(signal)-1).bit_length()
        ac = np.fft.irfft(np.abs(np.fft.rfft(centered, nfft))**2, nfft)[:len(signal)]
        lo, hi = max(1, rate//500), min(len(ac), rate//50+1)
        lag = lo + int(np.argmax(ac[lo:hi])) if hi > lo else 0
        voicing = max(0., float(ac[lag]/max(ac[0], 1e-12))) if lag else 0.
        pitch = rate/lag if lag and voicing >= .35 and rms_db > -50 else 0.
        start, end = offset/rate, min(offset+hop, len(pcm))/rate
        nearby = [c for c in chars if c['end'] > start-.5 and c['start'] < end+.5]
        rate_chars = len(nearby) / (end-start+1) if nearby else 0.
        past = [c['end'] for c in chars if c['end'] <= start]
        if rms_db < -50:
            if silence_start is None:
                silence_start = start
        else:
            silence_start = None
        gap = start-max(past) if past else (start-silence_start if silence_start is not None else 0.)
        correlation, delta = 0., 0.
        if paired is not None:
            # Both tracks use absolute sample time. No cross-correlation shift is
            # applied: a time-shifted stem must not conceal a synchronization defect.
            indexes = np.arange(offset, min(offset+hop, len(pcm)))
            voice_segment = np.interp(indexes/rate, paired_times, paired)
            mix_segment = pcm[indexes].mean(axis=1)
            if np.std(voice_segment)>1e-6 and np.std(mix_segment)>1e-6:
                correlation = float(np.corrcoef(voice_segment, mix_segment)[0, 1])
            voice_db = 20*np.log10(max(1e-5, np.sqrt(np.mean(voice_segment**2))))
            delta = float(rms_db-voice_db)
        flux = (float(np.abs(spectrum-previous_spectrum).sum())
                if previous_spectrum is not None and len(spectrum) == len(previous_spectrum) else 0.)
        rows.append([rms_db, float(np.abs(raw).max()), float(np.mean(np.abs(raw)>=.999)),
                     float(np.dot(spectrum, frequencies)/(rate/2)),
                     float(np.exp(np.log(spectrum).mean())/spectrum.mean()),
                     float(np.mean(np.diff(np.signbit(signal)))) if len(signal)>1 else 0.,
                     pitch, voicing, float(rms_db < -50),
                     0. if previous_db is None else rms_db-previous_db, flux, rate_chars, gap,
                     float(paired is not None), correlation, delta])
        intervals.append([start, end])
        previous_db, previous_spectrum = rms_db, spectrum
    features, times = np.asarray(rows), np.asarray(intervals)
    sequences = {}
    if chars:
        groups = {'aligned_units': [[c['start'], c['end']] for c in chars]}
        # Use measured character boundaries. Chinese characters are NOT assumed
        # to be verified syllables; phoneme/syllable coverage remains unqualified.
        cursor, sentences = 0, []
        from .speech_alignment import normalize
        for sentence in re.split(r'[。！？.!?\n]+', data['transcript']):
            count = len(normalize(sentence))
            if count:
                sentences.append([chars[cursor]['start'], chars[cursor+count-1]['end']])
                cursor += count
        groups['sentences'] = sentences
        for name, boundaries in groups.items():
            summary = []
            for start, end in boundaries:
                selected = features[(times[:, 0] < end) & (times[:, 1] > start)]
                if not len(selected):
                    raise ValueError('alignment unit has no decoded audio coverage')
                vector = selected.mean(axis=0)
                vector[1] = selected[:, 1].max()  # never average away amplitude peaks
                summary.append(vector)
            sequences[name] = {'features': np.asarray(summary), 'intervals': np.asarray(boundaries)}
    return {'features': features, 'intervals': times, 'sequences': sequences, 'tracks': tracks,
            'audio': source, 'alignment': alignment_ref, 'duration': duration,
            'coverage': {'source_samples': len(pcm), 'samples_consumed': len(pcm),
                         'sample_rate': rate, 'channels': pcm.shape[1],
                         'start': 0., 'end': duration},
            'raw_amplitude': {'peak': float(np.abs(pcm).max()),
                              'clipped_fraction': float(np.mean(np.abs(pcm)>=.999)),
                              'rms_db': float(20*np.log10(max(1e-5, np.sqrt(np.mean(pcm.astype(float)**2)))))}}


def encode(values):
    """Overlapping scalar windows: 64 bits per feature, 5 active bits each."""
    active = []
    for i, (value, (low, high)) in enumerate(zip(values, BOUNDS)):
        bucket = int(round(np.clip((value-low)/(high-low), 0, 1)*59))
        active.extend(range(i*64+bucket, i*64+bucket+5))
    return np.asarray(active, dtype=np.uint32)
