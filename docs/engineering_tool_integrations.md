# VX Engineering Tool Integrations v1

## Status

This module defines a governed registry for engineering tools. Local mathematics and unit conversion are executable without network credentials. GitHub access is read-only. Python execution and CAD/CAE/CFD jobs require an explicitly configured gateway, an authorized scope, and explicit approval. A connector contract is not proof that a remote provider is installed or connected.

## Tools

| Tool ID | Purpose | Permission / capability | Provider setup |
|---|---|---|---|
| math.evaluate | Bounded numeric expression evaluation; no imports or attribute access | analysis/research/verification + math_evaluation | None |
| math.solve_linear_system | Dense square linear solver with singularity checks | analysis/research/verification + linear_algebra | None |
| engineering.convert_units | SI-derived unit conversion with dimension validation | analysis/research/verification + unit_conversion | None |
| github.fetch_file | Retrieve a UTF-8 repository file with blob SHA and source URL | read-only/research/analysis/verification | Public API or optional read-only VX_GITHUB_TOKEN |
| sandbox.execute_python | Run Python through a remote sandbox gateway | sandbox + explicit approval | VX_SANDBOX_ENDPOINT and optional VX_SANDBOX_TOKEN |
| engineering.solver.submit | Submit a CAD/CAE/CFD/numerical job through a standardized gateway | sandbox/sandbox-write + explicit approval | VX_ENGINEERING_SOLVER_GATEWAY and optional VX_ENGINEERING_SOLVER_TOKEN |

## Security invariants

- Unknown tools, unapproved caller families, missing capabilities, wrong scopes and oversized inputs are blocked before the handler runs.
- Code and solver execution require explicit approval. Missing endpoint configuration returns NOT_CONFIGURED; it never becomes a fabricated success.
- Network endpoints come from trusted runtime configuration, not model-provided URLs. HTTPS is required except explicit loopback HTTP for development.
- GitHub only performs GET requests to the Contents API. It cannot create, update or delete repository contents.
- The sandbox and solver adapters are gateway clients, not sandbox implementations or native adapters for each solver. The gateway must enforce container/VM isolation, no host secrets, deny-by-default egress, resource limits, bounded storage, ownership, and audit logging.
- Provider receipts are validated for required identifiers. Captured input/output payloads receive canonical SHA-256 digests and source references.
- A digest proves integrity of the captured data, not scientific correctness or engineering safety.
- These tools cannot mutate canonical VAIXLNS state, change access policy, deploy to production, publish irreversible changes, or execute financial transactions.

## Runtime configuration

Store tokens in a secret manager or private runtime environment. Do not commit secrets.

- VX_GITHUB_TOKEN — optional least-privilege token.
- VX_GITHUB_API_BASE_URL — defaults to https://api.github.com; HTTPS or loopback only.
- VX_SANDBOX_ENDPOINT and optional VX_SANDBOX_TOKEN.
- VX_ENGINEERING_SOLVER_GATEWAY and optional VX_ENGINEERING_SOLVER_TOKEN.

## Remote sandbox request/receipt contract

The endpoint accepts POST JSON with language=python, the code, and timeout_seconds between 1 and 60. The response must include execution_id (string) and exit_code (integer); stdout, stderr, timed_out and status are optional. The adapter caps code at 64 KiB and output streams at 200 KiB.

The gateway must implement the real isolation boundary. This client must not be treated as a security sandbox by itself.

## Engineering solver gateway contract

The endpoint accepts POST JSON containing solver, job (a JSON object), and request_id. Solver labels are cadquery, freecad, openfoam, calculix, gmsh, fenics, scipy, or custom. The response must contain job_id and status; result_uri is optional. This is a provider-neutral gateway contract, not proof any solver is available.

## Using the hub from a specialist adapter

Call build_engineering_tool_hub() at adapter startup. Invoke a tool only with the registered caller family, exact capability set, and current authority scope. Preserve ToolEvidence alongside the produced artifact and attach the result to the VX workflow lineage. Tool outputs must be independently checked where correctness matters; source hashes alone are not verification. The existing EngineeringOrchestrator remains responsible for workflow lineage and failures, while VAIXLNS retains canonical governance/admission.

## Verification

The tests use fake provider responses and no network credentials. CI's green result verifies adapter logic only; it does not prove a live GitHub, sandbox or solver service is connected.
