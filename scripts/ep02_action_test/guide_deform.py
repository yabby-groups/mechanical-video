"""Illustrative guide-tube displacement weights, not a physical bend model."""


def displacement_weight(y, low, high):
    if high <= low:
        raise ValueError('guide extent must be positive')
    u = max(0.0, min(1.0, (y-low)/(high-low)))
    return 1.0 - u*u*(3.0-2.0*u)
