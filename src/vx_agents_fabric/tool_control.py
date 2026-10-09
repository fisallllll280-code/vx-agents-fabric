"""VX action-time gate for tool dispatch and hash-chained invocation receipts.

The gate is a local enforcement layer for BoundEngineeringToolDispatcher. It does not
authenticate credentials, contact the canonical policy service, or provide durable storage.
Providers should receive the bound dispatcher, never the low-level EngineeringToolHub.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
import copy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping

AUTHORITY_BY_SCOPE = {
    "read-only": "A1_RESEARCH",
    "research": "A1_RESEARCH",
    "analysis": "A1_RESEARCH",
    "verification": "A1_RESEARCH",
    "planning": "A2_PROPOSE",
    "proposal": "A2_PROPOSE",
    "decision-proposal": "A2_PROPOSE",
    "sandbox": "A3_SANDBOX_MUTATE",
    "sandbox-write": "A3_SANDBOX_MUTATE",
}
AUTHORITY_RANK = {
    "A0_OBSERVE": 0,
    "A1_RESEARCH": 1,
    "A2_PROPOSE": 2,
    "A3_SANDBOX_MUTATE": 3,
    "A4_BRANCH_MUTATE": 4,
    "A5_RELEASE_PREPARE": 5,
    "A6_RELEASE_DEPLOY": 6,
    "A7_IRREVERSIBLE_OR_PHYSICAL": 7,
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _policy_view(policy: Any) -> dict[str, Any]:
    if is_dataclass(policy):
        return asdict(policy)
    if isinstance(policy, Mapping):
        return dict(policy)
    return {"unreadable_policy": type(policy).__name__}


class VXToolControlGate:
    """Bounded tool-action policy evaluator with append-only in-memory receipts.

    The gate is intentionally fail-closed. Its event chain is process-local; production
    use still requires a durable VAIXLNS Event/Ledger adapter and atomic idempotency.
    """

    HARD_MAX_TOOL_CALLS = 256
    HARD_MAX_TOTAL_INPUT_BYTES = 4_000_000
    HARD_MAX_ELAPSED_SECONDS = 3600.0

    def __init__(self, *, max_tool_calls: int = 64,
                 max_total_input_bytes: int = 1_000_000,
                 max_elapsed_seconds: float = 300.0) -> None:
        if not 1 <= max_tool_calls <= self.HARD_MAX_TOOL_CALLS:
            raise ValueError("max_tool_calls_out_of_hard_bounds")
        if not 1 <= max_total_input_bytes <= self.HARD_MAX_TOTAL_INPUT_BYTES:
            raise ValueError("max_total_input_bytes_out_of_hard_bounds")
        if not 1 <= max_elapsed_seconds <= self.HARD_MAX_ELAPSED_SECONDS:
            raise ValueError("max_elapsed_seconds_out_of_hard_bounds")
        self.max_tool_calls = max_tool_calls
        self.max_total_input_bytes = max_total_input_bytes
        self.max_elapsed_seconds = float(max_elapsed_seconds)
        self._events: list[dict[str, Any]] = []
        self._previous_hash = "0" * 64
        self._emergency_stop = False
        self._emergency_reason = "not_active"

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        """Copy of this process's receipts; not a durable production ledger."""
        return tuple(copy.deepcopy(event) for event in self._events)

    def verify_event_chain(self) -> bool:
        previous = "0" * 64
        for stored in self._events:
            event = copy.deepcopy(stored)
            claimed = event.pop("event_sha256", None)
            if event.get("previous_event_sha256") != previous or not isinstance(claimed, str):
                return False
            if _digest(event) != claimed:
                return False
            previous = claimed
        return previous == self._previous_hash

    def activate_emergency_stop(self, reason: str = "operator_stop") -> None:
        self._emergency_stop = True
        self._emergency_reason = reason or "operator_stop"

    def clear_emergency_stop(self, *, authorized: bool = False) -> None:
        if not authorized:
            raise PermissionError("emergency_stop_clear_requires_authorized_operator")
        self._emergency_stop = False
        self._emergency_reason = "cleared_by_authorized_operator"

    def evaluate(
        self,
        *,
        policy: Any,
        tool_spec: Any | None,
        tool_id: str,
        arguments: Mapping[str, Any],
        explicit_approval: bool,
        attempted_calls: int,
        cumulative_input_bytes: int,
        elapsed_seconds: float,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Return a decision record; never calls a tool handler."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        policy_data = _policy_view(policy)
        policy_digest = _digest(policy_data)
        role_id = str(getattr(policy, "role_id", "unknown-role"))
        role_version = str(getattr(policy, "role_version", "unknown-version"))

        try:
            raw = _canonical_bytes(dict(arguments))
        except (TypeError, ValueError):
            raw = b""
            input_error = True
        else:
            input_error = False
        input_sha256 = hashlib.sha256(raw).hexdigest()
        action_id = "VX-ACT-" + hashlib.sha256(
            f"{role_id}@{role_version}|{tool_id}|{attempted_calls}|{input_sha256}".encode("utf-8")
        ).hexdigest()[:20]

        decision = "ALLOW"
        reason = "within_bound_vx_tool_policy"
        scope = str(getattr(policy, "authority_scope", ""))
        authority = AUTHORITY_BY_SCOPE.get(scope, "NONE")

        if self._emergency_stop:
            decision, reason = "REJECT", "emergency_stop_active:" + self._emergency_reason
        elif input_error:
            decision, reason = "REJECT", "arguments_not_json_serializable"
        elif not tool_id or tool_id not in tuple(getattr(policy, "allowed_tool_ids", ())):
            decision, reason = "REJECT", "tool_not_in_role_allowlist"
        elif tool_spec is None:
            decision, reason = "QUARANTINE", "tool_not_registered"
        elif attempted_calls >= self.max_tool_calls:
            decision, reason = "HOLD", "vx_budget_tool_call_limit"
        elif elapsed_seconds > self.max_elapsed_seconds:
            decision, reason = "HOLD", "vx_budget_elapsed_limit"
        elif len(raw) > int(getattr(policy, "max_input_bytes_per_call", 1_000_000)):
            decision, reason = "HOLD", "vx_budget_input_per_call"
        elif cumulative_input_bytes + len(raw) > min(
            self.max_total_input_bytes,
            int(getattr(policy, "max_total_input_bytes", self.max_total_input_bytes)),
        ):
            decision, reason = "HOLD", "vx_budget_total_input_bytes"
        elif authority == "NONE":
            decision, reason = "REJECT", "unknown_or_ungranted_authority_scope"
        elif scope not in tuple(getattr(tool_spec, "allowed_scopes", ())):
            decision, reason = "REJECT", "authority_scope_not_authorized"
        elif str(getattr(policy, "caller_family", "")) not in tuple(getattr(tool_spec, "allowed_families", ())):
            decision, reason = "REJECT", "caller_family_not_authorized"
        elif str(getattr(policy, "role_id", "")) == "" or str(getattr(policy, "role_version", "")) == "":
            decision, reason = "REJECT", "role_identity_and_version_required"
        elif bool(getattr(tool_spec, "requires_explicit_approval", False)) and not explicit_approval:
            decision, reason = "HOLD", "explicit_approval_required"
        elif not set(getattr(tool_spec, "required_capabilities", ())).issubset(
            set(getattr(policy, "capabilities", ()))
        ):
            decision, reason = "REJECT", "required_capability_missing"
        elif len(raw) > int(getattr(tool_spec, "max_input_bytes", 1_000_000)):
            decision, reason = "HOLD", "tool_input_size_limit"

        return {
            "schema_version": "1.0.0",
            "gate": "VX_FEDERATION_GATE",
            "decision": decision,
            "reason_code": reason,
            "action_id": action_id,
            "evaluated_at": now,
            "actor": {"role_id": role_id, "role_version": role_version},
            "tool": {
                "tool_id": tool_id,
                "tool_version": str(getattr(tool_spec, "version", "UNKNOWN")),
            },
            "scope": scope,
            "effective_authority": authority if decision == "ALLOW" else "NONE",
            "policy_digest": policy_digest,
            "input_sha256": input_sha256,
            "input_bytes": len(raw),
            "idempotency_key": idempotency_key,
            "execution_status": "NOT_STARTED",
        }

    def record(self, decision: Mapping[str, Any], *,
               execution_status: str, output_sha256: str | None = None,
               error_code: str | None = None) -> dict[str, Any]:
        """Append a hash-chained receipt without arguments or secret values."""
        event: dict[str, Any] = {
            "sequence": len(self._events) + 1,
            "event_type": "VX_TOOL_INVOCATION",
            "previous_event_sha256": self._previous_hash,
            "action_id": decision.get("action_id"),
            "gate": decision.get("gate", "VX_FEDERATION_GATE"),
            "decision": decision.get("decision", "HOLD"),
            "reason_code": decision.get("reason_code", "missing_decision"),
            "actor": decision.get("actor", {}),
            "tool": decision.get("tool", {}),
            "scope": decision.get("scope"),
            "effective_authority": decision.get("effective_authority", "NONE"),
            "policy_digest": decision.get("policy_digest"),
            "input_sha256": decision.get("input_sha256"),
            "input_bytes": decision.get("input_bytes"),
            "idempotency_key": decision.get("idempotency_key"),
            "execution_status": execution_status,
            "output_sha256": output_sha256,
            "error_code": error_code,
            "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        event["event_sha256"] = _digest(event)
        self._events.append(copy.deepcopy(event))
        self._previous_hash = event["event_sha256"]
        return copy.deepcopy(event)
