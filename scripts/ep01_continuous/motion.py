"""100s continuous EP01 choreography, all quantities illustrative."""
def ease(t,a,b):
    x=max(0.,min(1.,(t-a)/(b-a)))
    return x*x*x*(10+x*(-15+6*x))
def state(t):
    return dict(open=ease(t,.2,7)*(1-ease(t,90,99)),macro=ease(t,2,12),
                down=ease(t,17,31),bed=ease(t,35,50),wide=ease(t,49,60),
                x=.045*ease(t,53,60)-.09*ease(t,60,68)+.045*ease(t,68,72),
                y=.045*ease(t,59,66)-.045*ease(t,66,72),
                lift=.0045*ease(t,73,86),whole=ease(t,87,99))
