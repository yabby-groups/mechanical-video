"""Restrained synthetic motor and sliding sounds for the sample."""
import array
import math
import random
import wave


def generate(path):
    rate=48000
    rng=random.Random(19)
    samples=array.array('h')
    phase=0.0
    for i in range(rate*16):
        t=i/rate
        fade=max(0,min(1,t/.35,(16-t)/.8))
        active=max(0,min(1,(t-.8)/1.2,(14.0-t)/1.2))
        phase+=2*math.pi*(96+active*(31+9*math.sin(t*2.5)))/rate
        motor=.035*math.sin(phase)+.011*math.sin(phase*2)
        movement=active*.009*math.sin(2*math.pi*(215*t+1.8*math.sin(t*2)))
        air=(.004+active*.003)*(rng.random()*2-1)
        samples.append(round((motor+movement+air)*fade*32767))
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate); f.writeframes(samples.tobytes())
