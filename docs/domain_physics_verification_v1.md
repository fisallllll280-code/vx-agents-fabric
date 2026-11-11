# Domain Physics Verification v1

## Scope

This additive layer extends the existing bounded numeric-expression, linear-system and SI unit-conversion tools with deterministic classical-mechanics reference models. It is not a general-purpose physics engine and does not claim experimental validation.

## Models implemented

| Tool | Model | SI inputs | SI output |
|---|---|---|---|
| physics.constant_acceleration | 1-D constant acceleration | u (m/s), a (m/s²), t (s) | displacement (m), final velocity (m/s) |
| physics.newton_second_law | F = m a | mass (kg), acceleration (m/s²) | net force (N) |
| physics.kinetic_energy | E = ½ m v² | mass (kg), speed (m/s) | energy (J) |
| physics.gravitational_potential_energy | U = m g h | mass (kg), height (m), g (m/s²) | energy (J) |
| physics.linear_momentum | p = m v | mass (kg), velocity (m/s) | momentum (kg·m/s) |
| physics.projectile_range | ideal level-ground projectile | speed (m/s), angle (rad), g (m/s²) | flight time (s), range (m) |

## Assumptions and boundaries

- Classical mechanics only; no relativistic, quantum, aerodynamic-drag, variable-gravity or multi-body claims.
- Projectile motion assumes level launch/landing heights, constant gravity and zero air resistance.
- Inputs are finite bounded numbers; mass and speed domains are checked; angles are radians.
- Each tool is registered through the existing EngineeringToolHub, so scope/capability checks and input/output SHA-256 evidence remain in force.
- SHA-256 establishes integrity of captured inputs/outputs, not physical truth. High-consequence designs require independent domain review, uncertainty analysis and validation against trusted measurements or a qualified solver.
- This module does not connect to a local/cloud host, execute CAD/CAE/CFD jobs, change canonical VAIXLNS state, or grant production authority.

## Verification

Run from repository root:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

The dedicated test module covers reference cases, invalid domains, tool registration, capability denial and hash evidence. A green test result verifies the implementation contract only, not live infrastructure or experimental accuracy.
