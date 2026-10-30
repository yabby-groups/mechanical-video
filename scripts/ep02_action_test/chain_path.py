"""Planar constant-length drag-chain centreline for an internal motion study.

Distances are metres; this idealized path is not a CAD joint or collision model.
"""
import math


def geometry(fixed_x, moving_x, bend_x, lower_z, upper_z, displacement):
    radius = (upper_z - lower_z) / 2
    if radius <= 0:
        raise ValueError('upper run must be above lower run')
    bend = bend_x + displacement / 2
    moving = moving_x + displacement
    if bend >= min(fixed_x, moving):
        raise ValueError('movement exceeds the assumed U-shaped chain geometry')
    return fixed_x, moving, bend, lower_z, upper_z, radius


def length(fixed_x, moving_x, bend_x, lower_z, upper_z, displacement=0):
    fixed, moving, bend, _, _, radius = geometry(
        fixed_x, moving_x, bend_x, lower_z, upper_z, displacement)
    return fixed - bend + math.pi * radius + moving - bend


def point(distance, fixed_x, moving_x, bend_x, lower_z, upper_z, displacement=0):
    fixed, moving, bend, low, high, radius = geometry(
        fixed_x, moving_x, bend_x, lower_z, upper_z, displacement)
    first = fixed - bend
    arc = math.pi * radius
    total = first + arc + moving - bend
    if distance < -1e-12 or distance > total + 1e-12:
        raise ValueError('distance outside chain')
    distance = min(total, max(0.0, distance))
    if distance <= first:
        return (fixed - distance, low), (-1.0, 0.0)
    if distance <= first + arc:
        angle = -math.pi / 2 - (distance - first) / radius
        return (bend + radius * math.cos(angle), (low + high) / 2 + radius * math.sin(angle)), (math.sin(angle), -math.cos(angle))
    return (bend + distance - first - arc, high), (1.0, 0.0)
