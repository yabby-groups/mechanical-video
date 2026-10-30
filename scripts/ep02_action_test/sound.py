"""Synthetic mechanical foley synchronized to the illustrative animation."""
import wave

import numpy as np


def generate(path, events, seconds):
    rate = 48000
    t = np.arange(round(seconds * rate), dtype=np.float64) / rate

    def motion(start, end):
        u = np.clip((t - start) / (end - start), 0, 1)
        return 4 * u * (1 - u)

    cycles = max(1, round(seconds / 6.3))
    omega = 2 * np.pi * cycles / seconds
    travel = .25 + .75 * np.abs(np.cos(omega * t))
    panel_intervals = [
        (events[14]['start'], events[14]['end'] + 2),
        (events[40]['start'], events[46]['end']),
        (events[47]['start'], seconds - .1 if seconds > 36 else events[48]['end'])]
    panel = np.maximum.reduce([motion(a, b) for a, b in panel_intervals])
    frame = motion(events[21]['start'] + 3, events[34]['end'] - 2)
    rng = np.random.default_rng(20261030)
    noise = np.convolve(rng.uniform(-1, 1, t.size), np.ones(9) / 9, mode='same')
    noise *= np.minimum(1, np.minimum(t / .03, (seconds - t) / .03))
    # Integer carrier cycles and periodic modulation preserve phase at the loop.
    phase = 2 * np.pi * (120 * t + 12 * np.sin(2 * omega * t) / (2 * omega))
    motor = travel * (.045 * np.sin(phase) + .014 * np.sin(2 * phase))
    rail = travel * (.033 * noise + .009 * np.sin(phase * 6.4))
    sliding = panel * (.048 * noise + .021 * np.sin(2 * np.pi * 145 * t))
    vibration = frame * (.018 * np.sin(2 * np.pi * 92 * t) + .027 * noise)
    clicks = np.zeros_like(t)
    turning_times = [(i + .5) * seconds / (2 * cycles) for i in range(2 * cycles)]
    for when in turning_times + [events[14]['end'] + 2]:
        start = max(0, int(when * rate)); stop = min(len(t), start + int(.2 * rate))
        dt = t[start:stop] - when
        clicks[start:stop] += .035 * np.exp(-np.maximum(dt, 0) * 38) * (dt >= 0) * np.sin(2 * np.pi * 520 * dt)
    duck = np.ones_like(t)
    for event in events:
        a = max(0, int((event['start'] - .12) * rate))
        b = min(len(t), int((event['end'] + .12) * rate))
        if b > a:
            duck[a:b] = np.minimum(duck[a:b], .55 + .45 * np.clip(
                np.maximum(event['start'] - t[a:b], t[a:b] - event['end']) / .12, 0, 1))
    samples = np.clip(2 * (motor + rail + sliding + vibration + clicks) * duck, -.98, .98)
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes((samples * 32767).astype('<i2').tobytes())
