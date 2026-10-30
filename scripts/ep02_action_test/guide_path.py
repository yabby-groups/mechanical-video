"""Illustrative fixed-length polyline with one moving endpoint."""
import numpy as np


def solve(points, displacement, iterations=500, tolerance=1e-8):
    source = np.asarray(points, dtype=float)
    if source.ndim != 2 or source.shape[1] != 3 or len(source) < 3:
        raise ValueError('expected at least three 3D points')
    lengths = np.linalg.norm(np.diff(source, axis=0), axis=1)
    if np.any(lengths <= 1e-10):
        raise ValueError('zero-length segment')
    start = source[0] + np.asarray(displacement, dtype=float)
    end = source[-1].copy()
    if np.linalg.norm(end - start) >= lengths.sum():
        raise ValueError('endpoints exceed available length')
    result = source.copy()
    result += np.linspace(1, 0, len(result))[:, None] * (start - source[0])
    for _ in range(iterations):
        result[-1] = end
        for i in range(len(lengths) - 1, -1, -1):
            delta = result[i] - result[i + 1]
            result[i] = result[i + 1] + delta * (lengths[i] / np.linalg.norm(delta))
        result[0] = start
        for i, length in enumerate(lengths):
            delta = result[i + 1] - result[i]
            result[i + 1] = result[i] + delta * (length / np.linalg.norm(delta))
        if np.linalg.norm(result[-1] - end) < tolerance:
            result[-1] = end
            return result
    raise RuntimeError('guide path did not converge')
