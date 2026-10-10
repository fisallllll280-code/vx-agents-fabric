"""Evidence-gated lifecycle controller for VAIXLNS/VX.

Policy guard only. It performs no network probes or deployment, and its in-memory
history is not a substitute for the canonical VAIXLNS Event Ledger.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Any


class LoopState(str, Enum):
    INTAKE = "INTAKE"
    DISCOVERY = "DISCOVERY"
    INDEXED = "INDEXED"
    PLANNED = "PLANNED"
    SANDBOXED = "SANDBOXED"
    IMPLEMENTED = "IMPLEMENTED"
    TESTED = "TESTED"
    INDEPENDENTLY_VERIFIED = "INDEPENDENTLY_VERIFIED"
    PROOF_BOUND = "PROOF_BOUND"
    GOVERNANCE_PENDING = "GOVERNANCE_PENDING"
    ADMITTED = "ADMITTED"
    DEPLOYED = "DEPLOYED"
    OBSERVED = "OBSERVED"
    QUARANTINED = "QUARANTINED"
    RECOVERY_PLANNED = "RECOVERY_PLANNED"
    REPLAYED = "REPLAYED"
    REGRESSION_TESTED = "REGRESSION_TESTED"
    HOLD = "HOLD"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class TransitionDenied(ValueError):
    """Raised if an operation is out of sequence or lacks required evidence."""


@dataclass(frozen=True)
class GateEvidence:
    source_inventory_ref: str = ""
    coverage_report_ref: str = ""
    unresolved_gaps_ref: str = ""
    plan_ref: str = ""
    sandbox_ref: str = ""
    artifact_ref: str = ""
    artifact_sha256: str = ""
    test_report_ref: str = ""
    tests_passed: bool = False
    tested_artifact_sha256: str = ""
    implementer_id: str = ""
    verifier_id: str = ""
    verifier_report_ref: str = ""
    verified_artifact_sha256: str = ""
    proof_ref: str = ""
    proof_sha256: str = ""
    proof_input_sha256: str = ""
    policy_version: str = ""
    proof_policy_version: str = ""
    proof_expires_at: str = ""
    governance_decision: str = ""
    governance_authority_ref: str = ""
    deployment_authority_ref: str = ""
    rollback_plan_ref: str = ""
    observation_ref: str = ""
    drift_detected: bool = False
    failure_ref: str = ""
    recovery_plan_ref: str = ""
    replay_ref: str = ""
    replay_passed: bool = False
    regression_report_ref: str = ""
    regression_passed: bool = False
    recovery_accepted: bool = False
    hold_reason: str = ""
    rejection_reason: str = ""


@dataclass(frozen=True)
class LoopEvent:
    sequence: int
    from_state: str
    to_state: str
    recorded_at: str
    evidence_sha256: str
    previous_hash: str
    event_hash: str


_ALLOWED: dict[LoopState, set[LoopState]] = {
    LoopState.INTAKE: {LoopState.DISCOVERY},
    LoopState.DISCOVERY: {LoopState.INDEXED},
    LoopState.INDEXED: {LoopState.PLANNED},
    LoopState.PLANNED: {LoopState.SANDBOXED},
    LoopState.SANDBOXED: {LoopState.IMPLEMENTED},
    LoopState.IMPLEMENTED: {LoopState.TESTED},
    LoopState.TESTED: {LoopState.INDEPENDENTLY_VERIFIED},
    LoopState.INDEPENDENTLY_VERIFIED: {LoopState.PROOF_BOUND},
    LoopState.PROOF_BOUND: {LoopState.GOVERNANCE_PENDING},
    LoopState.GOVERNANCE_PENDING: {LoopState.ADMITTED, LoopState.REJECTED},
    LoopState.ADMITTED: {LoopState.DEPLOYED},
    LoopState.DEPLOYED: {LoopState.OBSERVED},
    LoopState.OBSERVED: {LoopState.CLOSED},
    LoopState.QUARANTINED: {LoopState.RECOVERY_PLANNED},
    LoopState.RECOVERY_PLANNED: {LoopState.REPLAYED},
    LoopState.REPLAYED: {LoopState.REGRESSION_TESTED},
    LoopState.REGRESSION_TESTED: {LoopState.PLANNED},
}


def _has(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", value or ""))


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _proof_is_fresh(evidence: GateEvidence, now: datetime) -> bool:
    if not _has(evidence.proof_expires_at):
        return False
    try:
        expiry_text = evidence.proof_expires_at.strip()
        if expiry_text.endswith("Z"):
            expiry_text = expiry_text[:-1] + "+00:00"
        expiry = datetime.fromisoformat(expiry_text)
    except (ValueError, TypeError):
        return False
    if expiry.tzinfo is None or expiry.utcoffset() is None:
        return False
    current = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    return expiry.astimezone(timezone.utc) > current.astimezone(timezone.utc)


class ClosedLoopController:
    """Validate state transitions and keep a hash-chained in-memory event history."""

    GENESIS_HASH = "0" * 64
    TERMINAL = {LoopState.HOLD, LoopState.REJECTED, LoopState.CLOSED}

    def __init__(self) -> None:
        self.state = LoopState.INTAKE
        self.events: list[LoopEvent] = []
        self._head = self.GENESIS_HASH

    @property
    def head_hash(self) -> str:
        return self._head

    @staticmethod
    def _require(evidence: GateEvidence, *fields: str) -> None:
        missing = [field for field in fields if not _has(getattr(evidence, field))]
        if missing:
            raise TransitionDenied("missing_evidence:" + ",".join(missing))

    @classmethod
    def _require_fresh_proof(cls, evidence: GateEvidence, now: datetime) -> None:
        cls._require(evidence, "proof_ref", "proof_sha256", "proof_input_sha256",
                     "artifact_sha256", "policy_version", "proof_policy_version",
                     "proof_expires_at")
        if not _valid_sha256(evidence.proof_sha256):
            raise TransitionDenied("invalid_proof_sha256")
        if not _valid_sha256(evidence.proof_input_sha256):
            raise TransitionDenied("invalid_proof_input_sha256")
        if evidence.proof_input_sha256 != evidence.artifact_sha256:
            raise TransitionDenied("proof_input_does_not_match_artifact")
        if evidence.policy_version != evidence.proof_policy_version:
            raise TransitionDenied("proof_policy_version_mismatch")
        if not _proof_is_fresh(evidence, now):
            raise TransitionDenied("proof_expired_or_timezone_ambiguous")

    def transition(
        self,
        target: LoopState | str,
        evidence: GateEvidence,
        *,
        now: datetime | None = None,
    ) -> LoopEvent:
        """A denied transition leaves both state and event history unchanged."""
        try:
            next_state = target if isinstance(target, LoopState) else LoopState(target)
        except ValueError as exc:
            raise TransitionDenied("unknown_target_state") from exc

        current = self.state
        if current in self.TERMINAL:
            raise TransitionDenied("terminal_state:" + current.value)

        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        if next_state == LoopState.HOLD:
            self._require(evidence, "hold_reason")
        elif next_state == LoopState.QUARANTINED:
            if not (_has(evidence.failure_ref) or evidence.drift_detected):
                raise TransitionDenied("quarantine_requires_failure_or_drift_evidence")
        elif next_state == LoopState.REJECTED:
            if current != LoopState.GOVERNANCE_PENDING:
                raise TransitionDenied("reject_only_from_governance_pending")
            self._require(evidence, "rejection_reason")
        elif next_state not in _ALLOWED.get(current, set()):
            raise TransitionDenied(f"illegal_transition:{current.value}->{next_state.value}")

        if next_state == LoopState.INDEXED:
            self._require(evidence, "source_inventory_ref", "coverage_report_ref", "unresolved_gaps_ref")
        elif next_state == LoopState.PLANNED:
            self._require(evidence, "plan_ref")
            if current == LoopState.REGRESSION_TESTED and not evidence.recovery_accepted:
                raise TransitionDenied("recovery_plan_not_accepted")
        elif next_state == LoopState.SANDBOXED:
            self._require(evidence, "sandbox_ref")
        elif next_state == LoopState.IMPLEMENTED:
            self._require(evidence, "artifact_ref", "artifact_sha256")
            if not _valid_sha256(evidence.artifact_sha256):
                raise TransitionDenied("invalid_artifact_sha256")
        elif next_state == LoopState.TESTED:
            self._require(evidence, "test_report_ref", "artifact_sha256", "tested_artifact_sha256")
            if not evidence.tests_passed:
                raise TransitionDenied("tests_not_passed")
            if (not _valid_sha256(evidence.artifact_sha256)
                    or evidence.tested_artifact_sha256 != evidence.artifact_sha256):
                raise TransitionDenied("tests_do_not_match_current_artifact")
        elif next_state == LoopState.INDEPENDENTLY_VERIFIED:
            self._require(evidence, "implementer_id", "verifier_id", "verifier_report_ref",
                          "artifact_sha256", "verified_artifact_sha256")
            if evidence.implementer_id == evidence.verifier_id:
                raise TransitionDenied("independent_verifier_must_differ_from_implementer")
            if evidence.verified_artifact_sha256 != evidence.artifact_sha256:
                raise TransitionDenied("verification_does_not_match_current_artifact")
        elif next_state in {LoopState.PROOF_BOUND, LoopState.GOVERNANCE_PENDING,
                            LoopState.ADMITTED, LoopState.DEPLOYED}:
            self._require_fresh_proof(evidence, current_time)
            if next_state == LoopState.ADMITTED:
                if evidence.governance_decision.strip().upper() not in {
                    "ACCEPT", "ACCEPTED", "APPROVE", "APPROVED"
                }:
                    raise TransitionDenied("explicit_governance_acceptance_required")
                self._require(evidence, "governance_authority_ref")
            elif next_state == LoopState.DEPLOYED:
                self._require(evidence, "deployment_authority_ref", "rollback_plan_ref")
        elif next_state in {LoopState.OBSERVED, LoopState.CLOSED}:
            self._require(evidence, "observation_ref")
            if next_state == LoopState.CLOSED and evidence.drift_detected:
                raise TransitionDenied("cannot_close_while_drift_is_detected")
        elif next_state == LoopState.RECOVERY_PLANNED:
            self._require(evidence, "failure_ref", "recovery_plan_ref")
        elif next_state == LoopState.REPLAYED:
            self._require(evidence, "replay_ref")
            if not evidence.replay_passed:
                raise TransitionDenied("replay_not_passed")
        elif next_state == LoopState.REGRESSION_TESTED:
            self._require(evidence, "regression_report_ref")
            if not evidence.regression_passed:
                raise TransitionDenied("regression_tests_not_passed")

        evidence_hash = sha256(_canonical(asdict(evidence)).encode("utf-8")).hexdigest()
        timestamp = current_time.astimezone(timezone.utc).isoformat()
        material = {
            "sequence": len(self.events) + 1,
            "from_state": current.value,
            "to_state": next_state.value,
            "recorded_at": timestamp,
            "evidence_sha256": evidence_hash,
            "previous_hash": self._head,
        }
        event_hash = sha256(_canonical(material).encode("utf-8")).hexdigest()
        event = LoopEvent(**material, event_hash=event_hash)
        self.events.append(event)
        self._head = event_hash
        self.state = next_state
        return event

    def verify_history(self) -> bool:
        previous_hash = self.GENESIS_HASH
        for sequence, event in enumerate(self.events, start=1):
            if event.sequence != sequence or event.previous_hash != previous_hash:
                return False
            material = {
                "sequence": event.sequence,
                "from_state": event.from_state,
                "to_state": event.to_state,
                "recorded_at": event.recorded_at,
                "evidence_sha256": event.evidence_sha256,
                "previous_hash": event.previous_hash,
            }
            expected = sha256(_canonical(material).encode("utf-8")).hexdigest()
            if expected != event.event_hash:
                return False
            previous_hash = event.event_hash
        return previous_hash == self._head
