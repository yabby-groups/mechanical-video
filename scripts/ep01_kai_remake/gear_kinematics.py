"""Derive illustrative feed-gear rotations from the source assembly axes."""
import math


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def norm(v):
    return math.sqrt(dot(v, v))


def unit(v):
    length = norm(v)
    if length < 1e-12:
        raise ValueError('zero-length gear axis or contact vector')
    return tuple(x/length for x in v)


def subtract(a, b):
    return tuple(x-y for x, y in zip(a, b))


def scale(v, factor):
    return tuple(x*factor for x in v)


def perpendicular(v, axis):
    return subtract(v, scale(axis, dot(v, axis)))


def feed_gear(center, axis, filament_center, filament_radius, feed_speed):
    """Return angular rate and velocity at the gear/filament surface contact."""
    axis = unit(axis)
    radial = perpendicular(subtract(filament_center, center), axis)
    distance = norm(radial)
    contact_radius = distance - filament_radius
    if contact_radius <= 0 or feed_speed <= 0:
        raise ValueError('invalid filament contact geometry or feed speed')
    contact = scale(unit(radial), contact_radius)
    tangent = cross(axis, contact)
    if abs(tangent[2]) < .99*norm(tangent):
        raise ValueError('gear contact tangent does not align with filament direction')
    rate = -feed_speed/tangent[2]
    velocity = scale(tangent, rate)
    return dict(axis=axis, rate_rad_s=rate, contact_vector_m=contact,
                contact_velocity_m_s=velocity, contact_radius_m=contact_radius)


def coaxial_gear(center, axis, drive_center, drive):
    """Give the large gear the same world angular velocity as its shaft."""
    axis = unit(axis)
    drive_axis = unit(drive['axis'])
    alignment = dot(axis, drive_axis)
    radial_offset = norm(perpendicular(subtract(center, drive_center), drive_axis))
    if abs(alignment) < .999 or radial_offset > .0002:
        raise ValueError('large gear and drive gear are not coaxial')
    rate = drive['rate_rad_s']*alignment
    return dict(axis=axis, rate_rad_s=rate, shaft_axis_alignment=alignment,
                shaft_radial_offset_m=radial_offset)


def tooth_cycle_frequency(rate_rad_s, tooth_count, sampled_fps):
    """Keep repeated teeth below 80% of the preview Nyquist frequency."""
    if tooth_count <= 0 or sampled_fps <= 0:
        raise ValueError('invalid tooth count or frame rate')
    frequency = abs(rate_rad_s)*tooth_count/(2*math.pi)
    if frequency >= .4*sampled_fps:
        raise ValueError('gear teeth can appear to reverse at this sampling rate')
    return frequency
