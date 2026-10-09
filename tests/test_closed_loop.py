import unittest
from datetime import datetime, timezone, timedelta

from vx_agents_fabric.closed_loop import (
    ClosedLoopController, GateEvidence, LoopState, TransitionDenied
)


ARTIFACT_HASH = "a" * 64
PROOF_HASH = "b" * 64
NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


def evidence(**overrides):
    values = {
        "source_inventory_ref": "archive://inventory/1",
        "coverage_report_ref": "evidence://coverage/1",
        "unresolved_gaps_ref": "registry://gaps/1",
        "plan_ref": "plan://1",
        "sandbox_ref": "sandbox://1",
        "artifact_ref": "artifact://patch/1",
        "artifact_sha256": ARTIFACT_HASH,
        "test_report_ref": "test://report/1",
        "tests_passed": True,
        "tested_artifact_sha256": ARTIFACT_HASH,
        "implementer_id": "agent-code@1.0.0",
        "verifier_id": "agent-verifier@1.0.0",
        "verifier_report_ref": "verification://report/1",
        "verified_artifact_sha256": ARTIFACT_HASH,
        "proof_ref": "proof://1",
        "proof_sha256": PROOF_HASH,
        "proof_input_sha256": ARTIFACT_HASH,
        "policy_version": "policy-1",
        "proof_policy_version": "policy-1",
        "proof_expires_at": (NOW + timedelta(hours=1)).isoformat(),
        "governance_decision": "ACCEPT",
        "governance_authority_ref": "governance://decision/1",
        "deployment_authority_ref": "authority://deploy/1",
        "rollback_plan_ref": "rollback://plan/1",
        "observation_ref": "observation://1",
        "drift_detected": False,
        "failure_ref": "incident://1",
        "recovery_plan_ref": "recovery://plan/1",
        "replay_ref": "replay://1",
        "replay_passed": True,
        "regression_report_ref": "regression://1",
        "regression_passed": True,
        "recovery_accepted": True,
        "hold_reason": "adapter unavailable",
        "rejection_reason": "hard-gate failure",
    }
    values.update(overrides)
    return GateEvidence(**values)


def advance_to_independent_verification(controller):
    ev = evidence()
    for state in [
        LoopState.DISCOVERY, LoopState.INDEXED, LoopState.PLANNED,
        LoopState.SANDBOXED, LoopState.IMPLEMENTED, LoopState.TESTED,
        LoopState.INDEPENDENTLY_VERIFIED,
    ]:
        controller.transition(state, ev, now=NOW)


class ClosedLoopTests(unittest.TestCase):
    def test_normal_path_requires_each_gate_and_closes_with_verified_history(self):
        controller = ClosedLoopController()
        ev = evidence()
        for state in [
            LoopState.DISCOVERY, LoopState.INDEXED, LoopState.PLANNED,
            LoopState.SANDBOXED, LoopState.IMPLEMENTED, LoopState.TESTED,
            LoopState.INDEPENDENTLY_VERIFIED, LoopState.PROOF_BOUND,
            LoopState.GOVERNANCE_PENDING, LoopState.ADMITTED, LoopState.DEPLOYED,
            LoopState.OBSERVED, LoopState.CLOSED,
        ]:
            controller.transition(state, ev, now=NOW)
        self.assertEqual(controller.state, LoopState.CLOSED)
        self.assertTrue(controller.verify_history())
        self.assertEqual(len(controller.events), 13)

    def test_index_can_have_known_gaps_but_must_record_them(self):
        controller = ClosedLoopController()
        controller.transition(LoopState.DISCOVERY, evidence(), now=NOW)
        with self.assertRaisesRegex(TransitionDenied, "unresolved_gaps_ref"):
            controller.transition(LoopState.INDEXED, evidence(unresolved_gaps_ref=""), now=NOW)
        self.assertEqual(controller.state, LoopState.DISCOVERY)
        controller.transition(
            LoopState.INDEXED, evidence(unresolved_gaps_ref="registry://known-gaps/three"), now=NOW
        )

    def test_test_report_must_match_current_artifact(self):
        controller = ClosedLoopController()
        ev = evidence()
        for state in [LoopState.DISCOVERY, LoopState.INDEXED, LoopState.PLANNED,
                      LoopState.SANDBOXED, LoopState.IMPLEMENTED]:
            controller.transition(state, ev, now=NOW)
        with self.assertRaisesRegex(TransitionDenied, "tests_do_not_match_current_artifact"):
            controller.transition(LoopState.TESTED, evidence(tested_artifact_sha256="c" * 64), now=NOW)
        self.assertEqual(controller.state, LoopState.IMPLEMENTED)

    def test_independent_verifier_must_differ_from_implementer(self):
        controller = ClosedLoopController()
        ev = evidence()
        for state in [LoopState.DISCOVERY, LoopState.INDEXED, LoopState.PLANNED,
                      LoopState.SANDBOXED, LoopState.IMPLEMENTED, LoopState.TESTED]:
            controller.transition(state, ev, now=NOW)
        with self.assertRaisesRegex(TransitionDenied, "independent_verifier_must_differ"):
            controller.transition(
                LoopState.INDEPENDENTLY_VERIFIED,
                evidence(verifier_id="agent-code@1.0.0"),
                now=NOW,
            )

    def test_expired_or_policy_mismatched_proof_fails_closed(self):
        controller = ClosedLoopController()
        advance_to_independent_verification(controller)
        with self.assertRaisesRegex(TransitionDenied, "proof_expired"):
            controller.transition(
                LoopState.PROOF_BOUND,
                evidence(proof_expires_at=(NOW - timedelta(seconds=1)).isoformat()),
                now=NOW,
            )
        with self.assertRaisesRegex(TransitionDenied, "proof_policy_version_mismatch"):
            controller.transition(
                LoopState.PROOF_BOUND, evidence(proof_policy_version="policy-old"), now=NOW
            )
        self.assertEqual(controller.state, LoopState.INDEPENDENTLY_VERIFIED)

    def test_admission_requires_governance_and_deployment_requires_rollback(self):
        controller = ClosedLoopController()
        advance_to_independent_verification(controller)
        ev = evidence()
        controller.transition(LoopState.PROOF_BOUND, ev, now=NOW)
        controller.transition(LoopState.GOVERNANCE_PENDING, ev, now=NOW)
        with self.assertRaisesRegex(TransitionDenied, "explicit_governance_acceptance_required"):
            controller.transition(LoopState.ADMITTED, evidence(governance_decision="HOLD"), now=NOW)
        controller.transition(LoopState.ADMITTED, ev, now=NOW)
        with self.assertRaisesRegex(TransitionDenied, "rollback_plan_ref"):
            controller.transition(LoopState.DEPLOYED, evidence(rollback_plan_ref=""), now=NOW)

    def test_drift_enters_quarantine_replay_and_regression_before_replanning(self):
        controller = ClosedLoopController()
        ev = evidence()
        controller.transition(LoopState.DISCOVERY, ev, now=NOW)
        controller.transition(LoopState.QUARANTINED, evidence(drift_detected=True), now=NOW)
        controller.transition(LoopState.RECOVERY_PLANNED, ev, now=NOW)
        controller.transition(LoopState.REPLAYED, ev, now=NOW)
        controller.transition(LoopState.REGRESSION_TESTED, ev, now=NOW)
        controller.transition(LoopState.PLANNED, ev, now=NOW)
        self.assertEqual(controller.state, LoopState.PLANNED)
        self.assertTrue(controller.verify_history())

    def test_arbitrary_transition_fails_without_mutating_state_or_history(self):
        controller = ClosedLoopController()
        with self.assertRaisesRegex(TransitionDenied, "illegal_transition"):
            controller.transition(LoopState.DEPLOYED, evidence(), now=NOW)
        self.assertEqual(controller.state, LoopState.INTAKE)
        self.assertEqual(controller.events, [])
        self.assertEqual(controller.head_hash, controller.GENESIS_HASH)

    def test_hold_requires_reason_and_is_terminal(self):
        controller = ClosedLoopController()
        with self.assertRaisesRegex(TransitionDenied, "hold_reason"):
            controller.transition(LoopState.HOLD, evidence(hold_reason=""), now=NOW)
        controller.transition(LoopState.HOLD, evidence(), now=NOW)
        with self.assertRaisesRegex(TransitionDenied, "terminal_state"):
            controller.transition(LoopState.DISCOVERY, evidence(), now=NOW)


class AgentRoutingTests(unittest.TestCase):
    def test_new_index_server_and_development_roles_are_registered_and_routed(self):
        from vx_agents_fabric.orchestrator import PIPELINE
        from vx_agents_fabric.registry import default_registry

        registry = default_registry()
        required = {
            "VX-SRV-RECON",
            "VX-IDX-ARCHIVE",
            "VX-IDX-RECON",
            "VX-ENG-CODE",
            "VX-ENG-COMPILER",
            "VX-ENG-DEV",
        }
        registered = {item.role_id for item in registry.all_agents()}
        self.assertTrue(required.issubset(registered))
        routed = {role_id for _, role_ids in PIPELINE for role_id in role_ids}
        self.assertTrue(required.issubset(routed))
        self.assertEqual(registry.resolve("VX-SRV-RECON").authority_scope, "read-only")
        self.assertEqual(registry.resolve("VX-IDX-ARCHIVE").authority_scope, "read-only")


if __name__ == "__main__":
    unittest.main()
