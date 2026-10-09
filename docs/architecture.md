# VX Agents Fabric — Architecture and Integration Contract

## Responsibility boundary

- NEXENT discovers gaps, explores alternatives and creates candidate architectures.
- VAIXLNS is canonical registry and governance authority; it adopts only candidates that satisfy policy and proof gates.
- VX routes scoped tasks, invokes adapters, records lineage, verifies results and supports recovery.
- Ω Parent Multi-Mind coordinates independent architecture, research, finance, security and proof reviews. It proposes decisions; it has no unrestricted write authority.

Do not connect every agent to every system. Each agent connects to VX through a declared adapter and contract, then receives only scoped access to the subsystem needed for its task.

## Agent identity and versions

A logical role is identified by role_id. Each immutable implementation is role_id@version. Parallel versions remain available for comparison and rollback. Routing without a pinned version chooses the highest enabled SemVer-like version; deployed workflows should pin versions after validation. Alias collisions and attempts to overwrite an existing version are rejected.

Catalog registration does not mean that a model is connected, the role is production-admitted or its behavior is proven. Agent adapters are injected through EngineeringOrchestrator(adapters=...). Parent mind adapters are independently injected through mind_adapters. Every mind defaults to DECLARED_NOT_CONNECTED until a provider/model version is bound.

## Independent mind council

Five declared review perspectives:
1. Systems architecture and constraints.
2. Research evidence, provenance and uncertainty.
3. Financial viability, costs and downside scenarios.
4. Security and adversarial failure analysis.
5. Proof obligations, test validity and reproducibility.

A mind review is listed as reviewed only after its configured adapter returns an accepted state. Agreement cannot override hard failures, missing evidence, missing adapters or an invalid ledger. All parent reviews are retained as hashed outputs.

## Lifecycle and automation

INTAKE → RESEARCH → FINANCIAL_FEASIBILITY → ARCHITECTURE → INNOVATION → BUILD_PLAN_AND_IMPLEMENTATION → VALIDATION → OPERATIONS_AND_LEARNING → PARENT_DECISION.

For each stage the orchestrator creates a task envelope, invokes the configured adapter, records missing adapters/errors, hashes artifacts, preserves input lineage and computes a parent decision. All tasks receive guardrails to preserve provenance, distinguish facts/assumptions/hypotheses, never claim unrun tests, and avoid canonical mutation.

The orchestration is automatic; actual research, model inference and code execution depend on configured providers and tools. An absent adapter is recorded as NOT_CONFIGURED and forces HOLD.

## No-loss and failure-learning protocol

Each task preserves workflow_id, task_id, role ID/version, input artifact IDs, evidence references, output hash, limitations, error code and predecessor event hash. Failures and missing adapters remain in the workflow report. Recovery adapters should persist resumable checkpoints, replayable events and a dead-letter queue.

The included IntegrityLedger is in-memory and not durable across process restarts. A production deployment must replace it with the VAIXLNS Event/Ledger adapter and test crash recovery and replay.

## Scope controls

Allowed scopes are read-only, research, analysis, planning, proposal, verification, sandbox, sandbox-write and decision-proposal. The default boundary denies canonical mutation, production deployment, source deletion, payments, transfers, trading, access-policy changes and irreversible publishing. Financial agents are analysis/proposal only; they do not execute transactions.

Tool permissions must be enforced by the calling runtime, outside the model. Implement adapters with least privilege, network restrictions, budgets/timeouts, dependency pinning, secret isolation, sandbox execution and audit logs.

## VAIXLNS and Ω-RAC integration

Send candidate artifacts, hashes, lineage and evidence references to the VAIXLNS admission interface; invoke the configured Ω-RAC/proof verifier; consume an explicit governance decision with policy-version reference; and never use this package as a substitute for canonical authority or proof verification.

No live credentials, financial-account access or production authority are embedded in this repository.


## Explicit team data boundaries

Agent contracts declare input families. Research roles receive shared and research context only; finance roles may receive shared, research and finance context; engineering roles may receive shared, research, finance and engineering context; governance-level review may inspect the assembled record. Prior artifacts are filtered by the producing agent's registered family before they enter a specialist task. Domain-specific context should be passed under explicit keys named shared, research, finance, engineering or governance; do not put secrets in shared context.

The default catalog preserves several specialist contract variants at version 1.0.0 and 1.1.0. Workflows can pin role versions, while adapters may be registered at role_id@version to keep distinct implementations side by side. A role-level adapter is a fallback, not proof that the underlying model versions are distinct.


## Optional model/provider bindings

An OpenAI-compatible chat endpoint is opt-in. Configure VX_OPENAI_COMPAT_BASE_URL; family defaults can be selected with VX_RESEARCH_MODEL, VX_FINANCE_MODEL and VX_ENGINEERING_MODEL. Each parent mind must be bound explicitly, for example VX_MIND_MODEL_MIND_SYS_ARCH, VX_MIND_MODEL_MIND_RESEARCH, VX_MIND_MODEL_MIND_FINANCE, VX_MIND_MODEL_MIND_SECURITY and VX_MIND_MODEL_MIND_PROOF. API credentials are read from VX_OPENAI_COMPAT_API_KEY and must not be committed.

Exact role-version overrides use variables such as VX_AGENT_MODEL_VX_ENG_TEST_1_0_0 and VX_AGENT_MODEL_VX_ENG_TEST_1_1_0. Use build_from_env() from vx_agents_fabric.providers, then inject its agent_adapters and mind_adapters into EngineeringOrchestrator. The factory makes no network call itself; provider calls occur only on dispatch.

This adapter supplies chat inference, not web search, repository access or code execution. Those must be separately connected and sandboxed. Returned evidence references are accepted only when exact matches exist in the supplied context or prior artifact evidence. If sources or adapters are absent, the workflow must remain HOLD.


Downstream specialist tasks and the Ω Parent reviewers receive the **content** of allowed prior artifacts, not just artifact IDs and hashes. The orchestrator filters the artifact set by declared input families before sharing it, and records the same lineage and evidence references. This preserves actual handoff utility while preventing indiscriminate broadcast across agent families.
