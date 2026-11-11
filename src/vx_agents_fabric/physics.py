"""Bounded SI-unit mechanics models for independently checkable VX calculations."""
from __future__ import annotations

import math
from typing import Any


class PhysicsInputError(ValueError):
    """Input violates a physical model's declared domain."""


def _finite(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PhysicsInputError(name + "_must_be_numeric")
    result = float(value)
    if not math.isfinite(result) or abs(result) > 1e100:
        raise PhysicsInputError(name + "_must_be_finite_and_bounded")
    return result


def _nonnegative(name: str, value: Any) -> float:
    result = _finite(name, value)
    if result < 0:
        raise PhysicsInputError(name + "_must_be_nonnegative")
    return result


def constant_acceleration(initial_velocity_m_s: Any, acceleration_m_s2: Any,
                          time_s: Any) -> dict[str, float]:
    """1-D constant-acceleration model; all inputs and outputs use SI units."""
    u = _finite("initial_velocity_m_s", initial_velocity_m_s)
    a = _finite("acceleration_m_s2", acceleration_m_s2)
    t = _nonnegative("time_s", time_s)
    displacement = u * t + 0.5 * a * t * t
    final_velocity = u + a * t
    if not all(math.isfinite(x) and abs(x) <= 1e100 for x in (displacement, final_velocity)):
        raise PhysicsInputError("kinematics_result_out_of_bounds")
    return {"displacement_m": displacement, "final_velocity_m_s": final_velocity}


def newton_second_law(mass_kg: Any, acceleration_m_s2: Any) -> dict[str, float]:
    """Return net force from F=m*a; mass must be strictly positive."""
    mass = _finite("mass_kg", mass_kg)
    acceleration = _finite("acceleration_m_s2", acceleration_m_s2)
    if mass <= 0:
        raise PhysicsInputError("mass_kg_must_be_positive")
    force = mass * acceleration
    if not math.isfinite(force) or abs(force) > 1e100:
        raise PhysicsInputError("force_result_out_of_bounds")
    return {"net_force_N": force}


def kinetic_energy(mass_kg: Any, speed_m_s: Any) -> dict[str, float]:
    """Return translational kinetic energy E_k=1/2*m*v^2."""
    mass = _nonnegative("mass_kg", mass_kg)
    speed = _nonnegative("speed_m_s", speed_m_s)
    energy = 0.5 * mass * speed * speed
    if not math.isfinite(energy) or energy > 1e100:
        raise PhysicsInputError("kinetic_energy_out_of_bounds")
    return {"kinetic_energy_J": energy}


def gravitational_potential_energy(mass_kg: Any, height_m: Any,
                                   gravitational_acceleration_m_s2: Any = 9.80665) -> dict[str, float]:
    """Return near-Earth gravitational potential energy relative to height zero."""
    mass = _nonnegative("mass_kg", mass_kg)
    height = _finite("height_m", height_m)
    gravity = _finite("gravitational_acceleration_m_s2", gravitational_acceleration_m_s2)
    if gravity <= 0:
        raise PhysicsInputError("gravitational_acceleration_m_s2_must_be_positive")
    energy = mass * gravity * height
    if not math.isfinite(energy) or abs(energy) > 1e100:
        raise PhysicsInputError("potential_energy_out_of_bounds")
    return {"potential_energy_J": energy}


def linear_momentum(mass_kg: Any, velocity_m_s: Any) -> dict[str, float]:
    """Return 1-D linear momentum p=m*v, preserving the velocity sign."""
    mass = _nonnegative("mass_kg", mass_kg)
    velocity = _finite("velocity_m_s", velocity_m_s)
    momentum = mass * velocity
    if not math.isfinite(momentum) or abs(momentum) > 1e100:
        raise PhysicsInputError("momentum_out_of_bounds")
    return {"momentum_kg_m_s": momentum}


def projectile_range(initial_speed_m_s: Any, launch_angle_rad: Any,
                     gravitational_acceleration_m_s2: Any = 9.80665) -> dict[str, float]:
    """Ideal level-ground projectile range; no drag and equal launch/landing heights."""
    speed = _nonnegative("initial_speed_m_s", initial_speed_m_s)
    angle = _finite("launch_angle_rad", launch_angle_rad)
    gravity = _finite("gravitational_acceleration_m_s2", gravitational_acceleration_m_s2)
    if gravity <= 0:
        raise PhysicsInputError("gravitational_acceleration_m_s2_must_be_positive")
    if not 0 <= angle <= math.pi / 2:
        raise PhysicsInputError("launch_angle_rad_must_be_between_zero_and_pi_over_two")
    flight_time = 2.0 * speed * math.sin(angle) / gravity
    range_m = speed * speed * math.sin(2.0 * angle) / gravity
    if not all(math.isfinite(x) and abs(x) <= 1e100 for x in (flight_time, range_m)):
        raise PhysicsInputError("projectile_result_out_of_bounds")
    return {"flight_time_s": flight_time, "horizontal_range_m": range_m}
