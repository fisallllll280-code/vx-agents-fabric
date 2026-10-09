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


## Optional model connections

The opt-in OpenAI-compatible adapter can bind research, finance and engineering roles and five parent-mind reviewers. Configure VX_OPENAI_COMPAT_BASE_URL, family model variables and individual VX_MIND_MODEL_* variables. Exact role-version variables can bind multiple versions to different models. The provider factory makes no network call until an orchestrated task runs.

This adapter supplies chat inference only; web search, repository credentials, a sandbox, durable VAIXLNS ledger storage and release authority must be connected separately. Model-invented evidence references are filtered out.


## Runnable workflow entry point

With the package source on \`PYTHONPATH\`:

    PYTHONPATH=src python -m vx_agents_fabric.cli --goal "Design and validate an engineering capability" --workflow-id WF-ENG-001 --output reports/WF-ENG-001.json

Use \`--goal-file\` for a longer goal and \`--context-file\` for a JSON object with explicit \`shared\`, \`research\`, \`finance\`, \`engineering\` and \`governance\` sections. Pin an exact specialist version with, for example, \`VX_AGENT_VERSION_PIN_VX_ENG_TEST=1.0.0\`.

Example opt-in configuration (names are examples; credentials must be configured securely):

    VX_OPENAI_COMPAT_BASE_URL=http://127.0.0.1:11434/v1
    VX_RESEARCH_MODEL=<model-name>
    VX_FINANCE_MODEL=<model-name>
    VX_ENGINEERING_MODEL=<model-name>
    VX_MIND_MODEL_MIND_SYS_ARCH=<independent-review-model>
    VX_MIND_MODEL_MIND_RESEARCH=<independent-review-model>
    VX_MIND_MODEL_MIND_FINANCE=<independent-review-model>
    VX_MIND_MODEL_MIND_SECURITY=<independent-review-model>
    VX_MIND_MODEL_MIND_PROOF=<independent-review-model>

To preserve operations across process restarts, configure protected local paths:

    VX_EVENT_LEDGER_PATH=/var/lib/vx-agents/events.jsonl
    VX_ARTIFACT_ARCHIVE_PATH=/var/lib/vx-agents/artifacts.jsonl
    VX_FAILURE_MEMORY_PATH=/var/lib/vx-agents/failures.jsonl

The command returns exit code 0 only when it produces a candidate eligible for separate VAIXLNS governance review; 2 means HOLD/incomplete evidence or missing adapters, 3 means REJECT, and 4 means a local configuration/input error. A zero exit code is **not** production-release approval. A chat model connection alone does not provide web search, GitHub repository access or a code-execution sandbox; configure and validate those adapters separately.


## Closed-loop archive, server and software engineering extension

The specialist catalog now includes a read-only server/repository reconnaissance role, a zero-loss archive indexer, an index reconciliation analyst, a programming/repair engineer, a compiler/toolchain engineer and a development/CI engineer. They are routed through the same versioned contracts and VX boundary as the existing research and engineering roles.

The lifecycle controller in \`src/vx_agents_fabric/closed_loop.py\` enforces evidence-gated transitions for indexing, sandbox implementation, tests, independent verification, proof freshness, governance admission, deployment approval, runtime observation and recovery/replay. It is a policy module—not a server scanner, GitHub credential, live provider, production deployment or replacement for the canonical VAIXLNS ledger.

See \`docs/server_repository_inventory_v1.md\` for the dated inventory of previously referenced repositories, infrastructure requirements and server endpoints. Private-LAN endpoints are recorded as unverified references and are not probed from an external environment.
