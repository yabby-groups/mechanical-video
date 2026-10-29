"""Continuous, action-led EP01 choreography; motion is illustrative."""
def ease(t,a,b):
    x=max(0.,min(1.,(t-a)/(b-a)))
    return x*x*x*(10+x*(-15+6*x))
def deposition(t):
    return ease(t,42,72)+ease(t,77,86)

def make_path(rows, rotate=False):
    points=[(-1,-1),(1,-1),(1,1),(-1,1),(-1,-1)]
    for row in range(1,rows+1):
        y=-1+2*row/(rows+1)
        x=-1 if row%2 else 1
        points.extend(((x,y),(-x,y)))
    if points[-1][0]!=-1:
        points.append((points[-1][0],-1))
    points.append((-1,-1))
    if rotate:
        points=[(y,x) for x,y in points]
    lengths=[((b[0]-a[0])**2+(b[1]-a[1])**2)**.5 for a,b in zip(points,points[1:])]
    total=sum(lengths)
    fractions=[0.0]
    for length in lengths:
        fractions.append(fractions[-1]+length/total)
    return points,lengths,total,fractions

PATHS=[make_path(19),make_path(6,rotate=True)]

def deposition_point(progress,layer=0):
    points,lengths,total,_=PATHS[layer]
    remaining=max(0,min(1,progress))*total
    for a,b,length in zip(points,points[1:],lengths):
        if remaining<=length:
            f=remaining/length
            return (a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f)
        remaining-=length
    return points[-1]
def state(t):
    return dict(open=ease(t,0,4.5)*(1-ease(t,90,99)),macro=ease(t,.25,6),
                down=ease(t,11,25),bed=ease(t,28,43),wide=ease(t,45,58),
                detail=ease(t,66,72)*(1-ease(t,82,88)),
                x=0, y=0,
                lift=.0015*ease(t,73,76),whole=ease(t,87,100))
