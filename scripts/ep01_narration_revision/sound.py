"""Continuous synthetic foley, action envelopes and measured speech ducking."""
import array, math, random, wave

def generate(path,events):
    rate=48000; rng=random.Random(19); data=array.array('h')
    for i in range(rate*100):
        t=i/rate; ramp=min(1,t/.1,(100-t)/.2)
        duck=min([1]+[.28+.72*min(1,max(0,e['start']-t,t-e['end'])/.25) for e in events])
        sliding=max(0,1-abs(t-3.6)/3.6)+max(0,1-abs(t-95)/5)
        travel=max(0,1-abs(t-62)/10)+max(0,1-abs(t-80)/8)
        motor=.014*math.sin(2*math.pi*(125*t+2*math.sin(t*.7)))+.004*math.sin(2*math.pi*251*t)
        ticks=.007*math.exp(-(t%(1/10.74))*180)*math.sin(2*math.pi*1850*t)
        value=(motor+ticks+travel*.006*math.sin(2*math.pi*187*t)+(.001+sliding*.005)*(rng.random()*2-1))*duck*ramp
        data.append(round(value*32767))
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate); f.writeframes(data.tobytes())
