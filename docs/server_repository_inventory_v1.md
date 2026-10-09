# VAIXLNS / VLNS — Server, Repository and Agent Inventory v1

Research snapshot: 2026-10-09 UTC. This is an evidence inventory, not a deployment certificate.

## 1. Mandatory status model

Do not collapse the states below:
- MENTIONED: present in an archive or design.
- DISCOVERED: repository/service metadata found.
- CONFIGURED: adapter or endpoint explicitly configured.
- REACHABLE: connection observed at a timestamp.
- FUNCTIONAL: authenticated behavior passed a test.
- VERIFIED: identity, tests, policy, runtime and recovery/replay evidence satisfy the governing contract.
- ADMITTED / DEPLOYED: separate VAIXLNS decisions.

Names, README claims and a successful unit-test workflow do not prove a server is running.

## 2. User-owned system/repository surfaces checked

| Resource | Observed responsibility in project records | Verification boundary |
|---|---|---|
| [VAIXLNS](https://github.com/fisallllll280-code/VAIXLNS) | Canonical registry, governance, recovery and architecture hub | Public repository metadata confirmed. Documentation does not prove production deployment. |
| [NEXENT](https://github.com/fisallllll280-code/NEXENT) | Discovery, architecture search and research | Public repo inspected. It is not the same repo as the upstream ModelEngine Nexent project below. |
| [VAIXLNS-unified](https://github.com/fisallllll280-code/VAIXLNS-unified) | Integrated runtime surface | Public repo exists; runtime status record calls it partial and requires evidence matching implementation claims. |
| [vaixlns-core](https://github.com/fisallllll280-code/vaixlns-core) | Focused core/vertical slice | Public repo exists. README claims tested status, while the canonical runtime report says specification/reconciliation-needed; preserve this as a conflict until executed independently. |
| [vaixlns-csd-kernel](https://github.com/fisallllll280-code/vaixlns-csd-kernel) | Specialized kernel/DSL | Public repo exists; canonical runtime report calls it specified, not runtime-verified. |
| [VX-runtime](https://github.com/fisallllll280-code/VX-runtime) | VX execution contracts/runtime surface | Public repo exists; canonical status classifies the inspected tree as specification-first. |
| [VX50_COMPLETE_BUILD](https://github.com/fisallllll280-code/VX50_COMPLETE_BUILD) | Historical/build surface for VX | Private repo metadata visible to the linked GitHub connection; inspect tree and tests before claiming executable completeness. |
| [vaixlns-nexent-vx](https://github.com/fisallllll280-code/vaixlns-nexent-vx) | NEXENT-to-VX integration surface | Public repo exists; integration and boundary status require current test references. |
| [NAXLNS](https://github.com/fisallllll280-code/NAXLNS) | Candidate knowledge/adversarial-analysis surface | Private repo metadata visible. The identity mapping VLNS ↔ NAXLNS remains UNVERIFIED. |
| [VAIXLNS-Intent-to-Reality](https://github.com/fisallllll280-code/VAIXLNS-Intent-to-Reality) | Intent-to-execution surface | Private repo exists; canonical records classify it as incomplete/recovery-related. |
| [vx-financial-kernel](https://github.com/fisallllll280-code/vx-financial-kernel) | Financial computation boundary candidate | Private repo exists. Agent financial scope remains analysis/proposal, not payment or trading authority. |
| [vx-agents-fabric](https://github.com/fisallllll280-code/vx-agents-fabric) | Versioned research/engineering multi-agent coordination | Public repo. PR #1 merged; latest observed main CI run for commit c95563ae41c6a7dfd7b22522c924deedcd8148d7 passed at 2026-10-09 09:36 UTC. This confirms the repository's unit-test workflow only, not live providers, server connectivity, canonical ledger integration or production operation. |
| [vx-agents-system](https://github.com/fisallllll280-code/vx-agents-system) | Adjacent agent-system candidate | Its inspected main tree has only a short README; do not treat it as an equally implemented runtime. |

Canonical source maps:
- [Repository federation index](https://github.com/fisallllll280-code/VAIXLNS/blob/main/docs/indexes/REPOSITORY_FEDERATION_INDEX.md)
- [Repository runtime status](https://github.com/fisallllll280-code/VAIXLNS/blob/main/docs/indexes/REPOSITORY_RUNTIME_STATUS_V1.md)
- [Four-system reconciliation](https://github.com/fisallllll280-code/VAIXLNS/blob/main/docs/indexes/FOUR_SYSTEM_RECONCILIATION_V1.md)
- [Federation manifest](https://github.com/fisallllll280-code/VAIXLNS/blob/main/deploy/federation/federation.yaml)

Do not silently collapse repository identities:
- VLNS ↔ NAXLNS: UNVERIFIED.
- NEXNET ↔ NEXENT: UNVERIFIED.
- VX is represented by multiple distinct repository surfaces; the name VX50_COMPLETE_BUILD does not itself establish that its current build works.

The factory manifest contains planned repositories (repository-orchestrator, performance-fabric, development-fabric, innovation-factory, integration-lab). These are targets in a manifest, not confirmed existing repositories.

## 3. Servers and endpoints mentioned in the project archive

### 3.1 Private network address

Mentioned value: http://172.20.10.4:20429/t
- Host 172.20.10.4, port 20429, path /t.
- Status: MENTIONED / PRIVATE NETWORK / CURRENT REACHABILITY UNKNOWN.
- No current health response, server owner/process, credentials, test, or execution evidence was available in the reviewed records.
- It was not probed from the external environment. An authorized operator must test it from the correct network and then record source, observation time, identity, authentication mode, allowed operations, health result and evidence reference.
- Never treat a private IP address as proof that a server is reachable or trusted.

### 3.2 Local model endpoint

The agent README gives http://127.0.0.1:11434/v1 as an example OpenAI-compatible endpoint for local Ollama. That is a sample setting, not evidence Ollama is installed or running. Provider calls occur only when a configured workflow dispatches a role. Model ID, exact version and endpoint should be separate fields; credentials must not be committed or included in archive context.

### 3.3 Four-system deployment manifest

The canonical federation manifest declares:
- ingress: required;
- API gateway: required;
- event bus: required;
- PostgreSQL: required;
- Redis: optional;
- Vault or secret manager: required;
- metrics and logs: required;
- traces: recommended.

These are desired infrastructure declarations, not discovered or deployed hosts. Required evidence includes source revision, dependency resolution, startup, health, tests, execution evidence, verification status and timestamp.

## 4. External upstream references — not attached infrastructure

### 4.1 ModelEngine-Group Nexent upstream

Links: [upstream repository](https://github.com/ModelEngine-Group/nexent) and [official installation guide](https://github.com/ModelEngine-Group/nexent/blob/develop/doc/docs/en/quick-start/installation.md).

The upstream documents Docker Compose and Kubernetes profiles with application services, PostgreSQL, Elasticsearch, MinIO and Redis. Its published Docker guidance gives around 4 CPU / 8 GiB RAM / 40 GiB disk as minimum and 8 CPU / 16 GiB RAM / 100 GiB disk as recommended. Its documented ports include web 3000 and service/API ports 5010–5015. Those are upstream figures, not a measured VAIXLNS resource assessment; verify actual binds and the chosen profile before creating firewall rules.

Critical identity boundary: user-owned fisallllll280-code/NEXENT is a different repository from ModelEngine-Group/nexent. A common name does not authorize copying code, merging repositories or granting trust.

### 4.2 n8n workflow catalog

Links: [Zie619/n8n-workflows](https://github.com/Zie619/n8n-workflows), [n8n documentation](https://docs.n8n.io/), [integration catalog](https://n8n.io/integrations).

The external community catalog README describes a FastAPI + SQLite FTS5 search interface that can be run locally on port 8000 or in Docker. This is a catalog/search interface, not proof an actual n8n automation server is running. Imported community workflows need node/version checks, credential/permission inspection, isolated execution, negative tests, replay and explicit admission. Never import embedded secrets.

### 4.3 PostgreSQL, Redis, Docker, Compose and Kubernetes

The project archive mentions these technologies and the canonical deployment manifest requires PostgreSQL and marks Redis optional. The reviewed records did not identify live hostnames, clusters, credentials or successful connectivity for them. Their current project status is REQUIRED/OPTIONAL IN DESIGN, not DEPLOYED.

Redis' official security guidance recommends against direct exposure to untrusted networks: [Redis security](https://redis.io/docs/latest/operate/oss_and_stack/management/security/). Use private binding, firewall restrictions, ACLs/authentication and TLS appropriate to the deployment. Redis availability does not make it the canonical identity/admission/evidence authority; VAIXLNS remains authoritative.

## 5. Required admission protocol for any server, repository, model or tool

DISCOVER → RECORD_SOURCE → IDENTITY_AND_CONTRACT → QUARANTINE → ISOLATED_PROBE → FUNCTIONAL_TEST → FAILURE_AND_RECOVERY_TEST → REPLAY → INDEPENDENT_VERIFICATION → FRESH_PROOF → AUTHORITY_CHECK → ADMISSION → RUNTIME → CONTINUOUS_REVALIDATION

Each inventory row must retain immutable resource ID, aliases, kind, canonical owner, unresolved identity state, source URL/private-endpoint reference (never secret values), revision/image digest/software version, exposure/auth mode, permissions, capabilities, dependencies, resource budgets, timeouts, allowed/forbidden operations, source and observation timestamps, test/evidence artifact IDs and hashes, recovery/replay result, proof freshness, policy version, approval reference, next revalidation condition and lineage edges.

The reconnaissance agent is read-only by default. Private endpoints are not probed until the operator supplies explicit authorization and a destination allowlist. Discovery does not confer execution authority.

## 6. Agent roles to bind through declared VX contracts

| Agent | Default authority | Required artifacts |
|---|---|---|
| VX-SRV-RECON | Read-only | Source-backed repository/server/endpoint inventory; UNKNOWN where no live observation exists |
| VX-IDX-ARCHIVE | Read-only | Atomic records, source spans, SHA-256, lineage IDs and coverage report |
| VX-IDX-RECON | Analysis | Alias/duplicate/conflict map; explicit MISSING, CONFLICT and UNRESOLVED states; no silent merge |
| VX-ENG-CODE | Sandbox-write | Patch diff, changed-file list, source revision and limitations |
| VX-ENG-COMPILER | Sandbox | Toolchain/dependency versions, exact build command and build log |
| VX-ENG-DEV | Sandbox | CI/workflow result, test report and release-candidate manifest |
| VX-ENG-TEST | Sandbox | Tests bound to exact artifact SHA |
| VX-ENG-RED | Analysis | Threat model, negative-test evidence, failure cases |
| VX-ENG-PROOF | Verification | Fresh proof tied to artifact, dependencies, environment and policy version |
| VX-ENG-OPS | Sandbox | Health/incident evidence, recovery plan and replay result |
| Ω Parent Multi-Mind | Decision proposal only | ACCEPT_PROPOSAL / HOLD / REJECT / ESCALATE; cannot override hard-gate failures |

Credentials and runtime authority belong to adapters and the execution boundary, not to agent prompt text. Each adapter must declare destination, identity, allowed capabilities, budget, timeout and failure behavior. No all-to-all unrestricted agent networking.

## 7. Closed loop and recovery

Normal route:
OBSERVE → DISCOVER → INDEX → PLAN → SANDBOX → IMPLEMENT → TEST → INDEPENDENTLY VERIFY → BIND FRESH PROOF → VAIXLNS ADMISSION → DEPLOY WITH ROLLBACK → OBSERVE

Failure/drift route:
QUARANTINE → RECOVERY PLAN → REPLAY → REGRESSION TEST → NEW PLAN → REPEAT ALL GATES

The new controller rejects illegal transitions, missing index coverage records, changed artifact hashes, self-verification, stale/policy-mismatched proof, missing governance approval, deployments without rollback evidence and closure while drift remains. HOLD is incomplete work, not success. CLOSED and REJECTED are terminal for that workflow; a new artifact must start a new revision with explicit lineage.

## 8. Explicit gaps not claimed as implemented

The available evidence does not prove:
- the private endpoint 172.20.10.4:20429/t is reachable now or identify the process that owns it;
- that a production ingress, gateway, event bus, database or cluster is already deployed;
- that the local Ollama example endpoint is running;
- that vx-agents-fabric has live browser/search, private repository and code-sandbox adapters;
- that the local JSONL journals are connected to the canonical VAIXLNS Event Ledger;
- that workflow execution automatically resumes after a crash;
- that any system has passed the full admission, recovery/replay and sustained-operation sequence.

These stay explicit gates in the inventory, rather than assumptions filled in by the agents.
