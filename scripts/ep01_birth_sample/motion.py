"""Continuous, accelerated schematic print of a small open cup."""
import math

TURNS = 14
BASE_TURNS = 3
RADIUS = .012
HEIGHT = .0132


def ease(t, start, end):
    x = max(0.0, min(1.0, (t-start)/(end-start)))
    return x*x*x*(10+x*(-15+6*x))


def progress(t):
    return TURNS*ease(t, .8, 14.0)


def point(turn):
    turn = max(0.0, min(float(TURNS), turn))
    radius = RADIUS*min(1.0, turn/BASE_TURNS)
    height = HEIGHT*max(0.0, (turn-BASE_TURNS)/(TURNS-BASE_TURNS))
    angle = turn*2*math.pi
    return radius*math.cos(angle), radius*math.sin(angle), height
