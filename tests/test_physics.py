"""Deterministic tests for bounded SI mechanics models and VX tool exposure."""
from __future__ import annotations

import math
import unittest

from vx_agents_fabric.physics import (
    PhysicsInputError,
    constant_acceleration,
    gravitational_potential_energy,
    kinetic_energy,
    linear_momentum,
    newton_second_law,
    projectile_range,
)
from vx_agents_fabric.engineering_tools import build_engineering_tool_hub


class MechanicsModelTests(unittest.TestCase):
    def test_constant_acceleration_reference_case(self):
        result = constant_acceleration(0, 2, 5)
        self.assertAlmostEqual(result["displacement_m"], 25.0)
        self.assertAlmostEqual(result["final_velocity_m_s"], 10.0)

    def test_newton_second_law(self):
        self.assertEqual(newton_second_law(4, 3)["net_force_N"], 12.0)

    def test_kinetic_energy(self):
        self.assertEqual(kinetic_energy(2, 3)["kinetic_energy_J"], 9.0)

    def test_gravitational_potential_energy(self):
        self.assertAlmostEqual(gravitational_potential_energy(2, 10)["potential_energy_J"], 196.133)

    def test_momentum_preserves_direction(self):
        self.assertEqual(linear_momentum(3, -4)["momentum_kg_m_s"], -12.0)

    def test_projectile_45_degree_range(self):
        result = projectile_range(10, math.pi / 4)
        self.assertAlmostEqual(result["horizontal_range_m"], 100 / 9.80665)
        self.assertAlmostEqual(result["flight_time_s"], math.sqrt(2) * 10 / 9.80665)

    def test_projectile_vertical_launch_has_zero_range(self):
        self.assertAlmostEqual(projectile_range(10, math.pi / 2)["horizontal_range_m"], 0.0)

    def test_invalid_physical_domains_are_rejected(self):
        invalid_calls = (
            lambda: newton_second_law(0, 4),
            lambda: kinetic_energy(-1, 2),
            lambda: gravitational_potential_energy(1, 2, 0),
            lambda: projectile_range(10, math.pi),
            lambda: constant_acceleration(0, float("nan"), 1),
            lambda: linear_momentum(True, 1),
        )
        for call in invalid_calls:
            with self.subTest(call=call), self.assertRaises(PhysicsInputError):
                call()


class PhysicsToolIntegrationTests(unittest.TestCase):
    def test_physics_tools_are_registered_and_emit_hash_evidence(self):
        hub = build_engineering_tool_hub(environ={})
        result = hub.invoke(
            "physics.kinetic_energy", {"mass_kg": 2, "speed_m_s": 3},
            caller_family="engineering", authority_scope="analysis",
            caller_capabilities=("physics_mechanics",),
        )
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.result["kinetic_energy_J"], 9.0)
        self.assertEqual(len(result.evidence.input_sha256), 64)
        self.assertEqual(len(result.evidence.output_sha256), 64)

    def test_physics_tool_requires_declared_capability(self):
        hub = build_engineering_tool_hub(environ={})
        result = hub.invoke(
            "physics.newton_second_law", {"mass_kg": 2, "acceleration_m_s2": 3},
            caller_family="engineering", authority_scope="analysis",
        )
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.error_code, "required_capability_missing")


if __name__ == "__main__":
    unittest.main()
