# VX Agents Fabric — VAIXLNS Research, Finance & Engineering Swarm

A provider-agnostic coordination layer for versioned specialist agents, an Ω Parent Multi-Mind Council, traceable artifacts and a default-deny VX execution boundary.

## Canonical boundary

NEXENT discovers, researches and proposes candidate architectures. VAIXLNS owns canonical identity, policy, governance and adoption. VX routes scoped tasks, executes through declared adapters, observes results and preserves verification evidence. The Ω Parent coordinates independent architecture, research, finance, security and proof perspectives but has no unrestricted write authority.

## Specialist groups

- VX Research Intelligence: source quality, literature and patent discovery, repository archaeology, reproducibility, contradiction detection and evidence synthesis.
- VX Financial Intelligence: market sizing, unit economics, engineering/compute costs, pricing scenarios, risk, compliance questions and portfolio prioritization. Analysis and proposals only; no payments, fund transfers or asset trades.
- VX Engineering Intelligence: requirements, architecture, innovation, implementation, tests, adversarial review, proof packaging, operations, recovery and lessons learned.
- Ω Parent Multi-Mind: independent review perspectives synthesize ACCEPT_PROPOSAL, HOLD, REJECT or ESCALATE. Missing evidence and hard failures cannot be outvoted.

## Version and no-loss rules

A role has immutable versions identified by role_id plus semantic version. Parallel versions are retained; aliases cannot silently collide; outputs keep source agent/version, input artifact IDs, evidence references and content hashes. Missing provider adapters and failures are recorded, never silently skipped.

## Automated engineering lifecycle

INTAKE → RESEARCH → FINANCIAL_FEASIBILITY → ARCHITECTURE → INNOVATION → BUILD_PLAN_AND_IMPLEMENTATION → VALIDATION → OPERATIONS_AND_LEARNING → PARENT_DECISION.

The orchestrator routes all stages automatically when provider adapters exist. Unconfigured roles return NOT_CONFIGURED and force HOLD; no research, tests, proofs or successful builds are fabricated. Production deployment, canonical mutation, payments and trading remain outside default authority.

## Quick start

Requires Python 3.10+ and no runtime third-party dependencies.

    python -m unittest discover -s tests -v

See docs/architecture.md for integration contracts. This repository is a coordination scaffold: model/provider connectivity, durable storage and live execution adapters must be configured and validated separately.
