"""Continuous, action-led EP01 choreography; motion is illustrative."""
def ease(t,a,b):
    x=max(0.,min(1.,(t-a)/(b-a)))
    return x*x*x*(10+x*(-15+6*x))
def state(t):
    return dict(open=ease(t,0,4.5)*(1-ease(t,90,99)),macro=ease(t,.25,6),
                down=ease(t,11,25),bed=ease(t,28,43),wide=ease(t,45,58),
                detail=ease(t,66,72)*(1-ease(t,82,88)),
                x=.065*ease(t,49,56)-.13*ease(t,56,65)+.065*ease(t,65,72),
                y=.055*ease(t,54,61)-.055*ease(t,61,70),
                lift=.0045*ease(t,73,86),whole=ease(t,87,100))
