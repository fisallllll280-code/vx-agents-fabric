"""Deterministic proposal packet builder for the VX innovation stage.

This module turns a scoped request into a reviewable work packet. It does not
invent evidence, execute generated code, spend money, or mutate canonical data.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

SCHEMA_VERSION = "1.0.0"

INDEX_REFS = (
    {"index_id": "VAIXLNS.INDEX.INNOVATION_OPERATION.V1", "source": "VAIXLNS/registry/innovation-operation-index.v1.json", "state": "RECOVERED_WITH_REVIEW_DEBT", "snapshot": "433969a43b604563e22b70b8cb88223aff539fad"},
    {"index_id": "VAIXLNS.INDEX.OMEGA_000", "source": "VAIXLNS/registry/omega/omega-000-master-index.json", "state": "PROTECTED_READ_ONLY", "snapshot": "433969a43b604563e22b70b8cb88223aff539fad"},
    {"index_id": "NEXENT.INDEX.MASTER_FEDERATED", "source": "NEXENT/docs/MASTER_FEDERATED_INDEX.md", "state": "SOURCE_PINNED", "snapshot": "f62cf5920174551f9a8f88deb420f9515bedc284"},
    {"index_id": "NEXENT.INDEX.CANONICAL_INNOVATION", "source": "NEXENT/docs/NEXENT_CANONICAL_INNOVATION_INDEX_V1.md", "state": "SOURCE_PINNED", "snapshot": "f62cf5920174551f9a8f88deb420f9515bedc284"},
    {"index_id": "VX.INDEX.OMEGA_SYMBOL.V1", "source": "docs/indexes/OMEGA_SYMBOL_INDEX_V1.md", "state": "PROPOSED", "snapshot": "VX_PULL_REQUEST_HEAD"},
)

TOOL_ROUTES = (
    {"tool_id": "math.evaluate", "mode": "LOCAL_BOUNDED", "default": "AVAILABLE"},
    {"tool_id": "math.solve_linear_system", "mode": "LOCAL_BOUNDED", "default": "AVAILABLE"},
    {"tool_id": "engineering.convert_units", "mode": "LOCAL_BOUNDED", "default": "AVAILABLE"},
    {"tool_id": "github.fetch_file", "mode": "REMOTE_READ_ONLY", "default": "CONFIGURATION_REQUIRED"},
    {"tool_id": "sandbox.execute_python", "mode": "REMOTE_SANDBOX", "default": "NOT_CONFIGURED"},
    {"tool_id": "engineering.solver.submit", "mode": "EXTERNAL_SOLVER", "default": "NOT_CONFIGURED_APPROVAL_GATED"},
)

STAGES = (
    ("FORMULATE", "Turn the request into a falsifiable opportunity and record unknowns."),
    ("INDEX_LOOKUP", "Resolve relevant index records and preserve their pinned source snapshots."),
    ("REQUIREMENTS", "Specify constraints, users, measurable acceptance criteria and failure cases."),
    ("FORMAL_MODEL", "Define a mathematical, state, data or interface model appropriate to the domain."),
    ("CONTRACTS", "Define inputs, outputs, invariants, resource limits and evidence obligations."),
    ("FEASIBILITY", "Select only configured tools; simulation stays NOT_RUN until a solver is available."),
    ("IMPLEMENTATION_PLAN", "Produce a bounded build sequence and rollback plan."),
    ("VALIDATION", "Require reproducible tests, adversarial review and independent assurance."),
    ("CANONICAL_ADMISSION", "Keep promotion blocked until authorized governance accepts evidence."),
)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def build_innovation_packet(request: Mapping[str, Any]) -> dict[str, Any]:
    """Create a stable, evidence-aware packet from a validated JSON request."""
    goal = request.get("goal")
    if not isinstance(goal, str) or not goal.strip() or len(goal.encode("utf-8")) > 12000:
        return {"schema_version": SCHEMA_VERSION, "status": "HOLD_INVALID_GOAL", "error_code": "goal_required_or_too_large"}
    constraints = request.get("constraints", [])
    if not isinstance(constraints, list) or any(not isinstance(item, str) for item in constraints):
        return {"schema_version": SCHEMA_VERSION, "status": "HOLD_INVALID_CONSTRAINTS", "error_code": "constraints_must_be_string_list"}
    requested_indices = request.get("index_ids", [])
    if not isinstance(requested_indices, list) or any(not isinstance(item, str) for item in requested_indices):
        return {"schema_version": SCHEMA_VERSION, "status": "HOLD_INVALID_INDEX_IDS", "error_code": "index_ids_must_be_string_list"}
    available = {item["index_id"] for item in INDEX_REFS}
    unknown = sorted(set(requested_indices) - available)
    selected = [item for item in INDEX_REFS if not requested_indices or item["index_id"] in requested_indices]
    source_refs = request.get("source_refs", [])
    if not isinstance(source_refs, list) or any(not isinstance(item, str) for item in source_refs):
        return {"schema_version": SCHEMA_VERSION, "status": "HOLD_INVALID_SOURCE_REFS", "error_code": "source_refs_must_be_string_list"}

    blockers = []
    if unknown:
        blockers.append({"code": "INDEX_ID_UNRESOLVED", "items": unknown})
    blockers.extend([
        {"code": "INDEX_RECORD_LOOKUP_NOT_CONNECTED", "detail": "The catalogue identifies pinned source families; per-record search adapters are not connected."},
        {"code": "NXL_GRAMMARS_AND_COMPILERS_PROPOSED", "detail": "NXL translation remains on HOLD until formal grammar, semantics and compiler evidence are recovered."},
        {"code": "PROVIDER_AND_SOLVER_ADAPTERS_NOT_CONFIGURED", "detail": "Remote sandbox and engineering solver availability must be checked per deployment."},
        {"code": "INDEPENDENT_ASSURANCE_NOT_RUN", "detail": "ARC-X and independent reviewer evidence are required before admission."},
    ])
    materials = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "VX_INNOVATION_PACKET",
        "status": "PROPOSAL",
        "goal": goal.strip(),
        "goal_sha256": hashlib.sha256(goal.strip().encode("utf-8")).hexdigest(),
        "constraints": constraints,
        "domain": request.get("domain") if isinstance(request.get("domain"), str) else "unspecified",
        "requested_languages": request.get("requested_languages", []),
        "index_refs": selected,
        "caller_source_refs": sorted(set(source_refs)),
        "unresolved_index_ids": unknown,
        "tool_routes": list(TOOL_ROUTES),
        "stages": [{"name": name, "purpose": purpose, "state": "NOT_RUN"} for name, purpose in STAGES],
        "acceptance_criteria": [
            "Each factual claim has a source reference and a freshness check.",
            "Requirements have measurable pass and fail conditions.",
            "The selected model and contracts are reviewable and versioned.",
            "Any executed tool returns a bounded receipt with input and output hashes.",
            "Tests, adversarial review and proof obligations have independent evidence.",
            "Canonical promotion requires separate governance approval.",
        ],
        "blockers": blockers,
        "execution_state": "PLANNING_ONLY",
        "external_spend_sar": 0,
        "source_mutation_allowed": False,
        "canonical_mutation_allowed": False,
        "code_execution_performed": False,
        "evidence_state": "NOT_VERIFIED",
        "limitations": [
            "A deterministic packet builder structures work; novelty, feasibility and correctness are not inferred.",
            "Unknowns remain explicit blockers until a connected source, tool or reviewer supplies evidence.",
        ],
    }
    materials["packet_id"] = "VX-INNOV-" + _sha(materials)[:20].upper()
    materials["replay_id"] = _sha({"packet_id": materials["packet_id"], "schema_version": SCHEMA_VERSION})
    return materials


def build_innovation_adapter():
    """Return a local adapter for the opt-in VX-ENG-INNOV stage."""
    def adapter(envelope: Any) -> Mapping[str, Any]:
        payload = getattr(envelope, "payload", {})
        context = payload.get("context", {}) if isinstance(payload, Mapping) else {}
        engineering = context.get("engineering", {}) if isinstance(context, Mapping) else {}
        request = engineering.get("innovation_request") if isinstance(engineering, Mapping) else None
        if not isinstance(request, Mapping):
            return {"status": "HOLD_REQUEST_MISSING", "kind": "innovation_packet",
                    "content": {"error_code": "engineering.innovation_request_required"}}
        packet = build_innovation_packet(request)
        return {
            "artifact_id": str(getattr(envelope, "task_id", "VX-INNOV-TASK")) + ":innovation",
            "kind": "innovation_packet",
            "status": packet["status"],
            "content": packet,
            "evidence_refs": ["sha256:" + packet.get("goal_sha256", _sha({"request": "invalid"}))],
            "limitations": packet.get("limitations", ["Invalid request; no innovation work executed."]),
        }
    return adapter
