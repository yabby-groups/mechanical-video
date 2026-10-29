"""Continuous camera/action envelopes, without shot boundaries or visibility cuts."""
def ease(t,start,end):
    x=max(0,min(1,(t-start)/(end-start)))
    return x*x*x*(x*(x*6-15)+10)

def envelopes(t):
    opening=ease(t,.25,4)*(1-ease(t,12.8,15))
    close=ease(t,3,6.5)
    down=ease(t,8,11.8)
    back=ease(t,12,15)
    scale=(.28*(1-close)+.075*close)*(1-down)+.13*down
    scale=scale*(1-back)+.28*back
    return opening,close,down,back,scale
