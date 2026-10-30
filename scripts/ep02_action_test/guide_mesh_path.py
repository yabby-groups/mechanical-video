"""Map a tube mesh to a sampled centreline for illustrative bending."""
import numpy as np

from guide_path import solve


def bind(vertices, centres):
    vertices = np.asarray(vertices, dtype=float)
    centres = np.asarray(centres, dtype=float)
    segments = np.diff(centres, axis=0)
    lengths2 = np.sum(segments * segments, axis=1)
    if np.any(lengths2 <= 1e-16):
        raise ValueError('degenerate centreline segment')
    indices, fractions = [], []
    for chunk in np.array_split(vertices, max(1, (len(vertices) + 511) // 512)):
        delta = chunk[:, None, :] - centres[None, :-1, :]
        fraction = np.clip(np.einsum('nsi,si->ns', delta, segments) / lengths2, 0, 1)
        diff = delta - fraction[:, :, None] * segments[None, :, :]
        index = np.argmin(np.einsum('nsi,nsi->ns', diff, diff), axis=1)
        indices.extend(index)
        fractions.extend(fraction[np.arange(len(chunk)), index])
    index = np.asarray(indices, dtype=int)
    fraction = np.asarray(fractions)
    origin = centres[index] + fraction[:, None] * segments[index]
    tangents = np.gradient(centres, axis=0)
    tangent = tangents[index] * (1 - fraction[:, None]) + tangents[index + 1] * fraction[:, None]
    tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    return index, fraction, vertices - origin, tangent


def deform(binding, centres, displacement):
    index, fraction, offset, old_tangent = binding
    moving_sections = 4
    fixed_start = 25
    move = np.array((displacement, 0, 0))
    middle = solve(centres[moving_sections:fixed_start], move, iterations=2000)
    path = np.concatenate((centres[:moving_sections] + move, middle, centres[fixed_start:]))
    segments = np.diff(path, axis=0)
    tangents = np.gradient(path, axis=0)
    tangent = tangents[index] * (1 - fraction[:, None]) + tangents[index + 1] * fraction[:, None]
    tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    axis = np.cross(old_tangent, tangent)
    dot = np.sum(old_tangent * tangent, axis=1)
    if np.any(dot < -.99):
        raise ValueError('centreline tangent reverses')
    cross = np.cross(axis, offset)
    rotated = offset + cross + np.cross(axis, cross) / (1 + dot)[:, None]
    return path[index] + fraction[:, None] * segments[index] + rotated, path
