"""Original synchronized foley synthesis. No external samples or claimed recording."""
import array
import math
import random
import wave

def generate(path):
    rate=48000; rng=random.Random(19)
    samples=array.array('h')
    for i in range(rate*15):
        t=i/rate
        # Restrained motor bed, gear ticks and tactile transition transients.
        ramp=min(1,t/.07,(15-t)/.12)
        proximity=1+.3*math.sin(math.pi*t/15)**2
        whirr=proximity*.018*math.sin(2*math.pi*(125*t+2*math.sin(t*.7)))
        whirr+=.006*math.sin(2*math.pi*251*t)
        tick_age=(t%(1/10.74))
        ticks=.012*math.exp(-tick_age*180)*math.sin(2*math.pi*1850*t)
        slide=max(0,1-abs(t-2)/1.8)+max(0,1-abs(t-14)/1)
        value=whirr+ticks+(.002+.007*slide)*(rng.random()*2-1)
        samples.append(round(max(-.8,min(.8,value*ramp))*32767))
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate); f.writeframes(samples.tobytes())
