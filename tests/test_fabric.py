import unittest
from vx_agents_fabric.contracts import AgentSpec
from vx_agents_fabric.ledger import IntegrityLedger
from vx_agents_fabric.orchestrator import EngineeringOrchestrator, VXExecutionBoundary
from vx_agents_fabric.registry import AgentRegistry, default_registry


class RegistryTests(unittest.TestCase):
    def test_multiple_versions_are_retained_and_latest_resolves(self):
        registry = AgentRegistry()
        base = dict(role_id="VX-TEST", name="Test", family="test", capabilities=("testing",),
                    inputs=("goal",), outputs=("test_report",), authority_scope="sandbox")
        registry.register(AgentSpec(version="1.0.0", **base))
        registry.register(AgentSpec(version="1.1.0", **base))
        self.assertEqual(registry.resolve("VX-TEST").version, "1.1.0")
        self.assertEqual(len(registry.versions("VX-TEST")), 2)
        self.assertEqual(registry.resolve("VX-TEST", "1.0.0").version, "1.0.0")

    def test_version_identity_cannot_be_silently_overwritten(self):
        registry = AgentRegistry()
        registry.register(AgentSpec("VX-X", "X", "test", "1.0.0", ("a",), ("in",), ("out",), "analysis"))
        with self.assertRaises(ValueError):
            registry.register(AgentSpec("VX-X", "X2", "test", "1.0.0", ("a",), ("in",), ("out",), "analysis"))

    def test_parent_has_separate_review_minds(self):
        registry = default_registry()
        self.assertGreaterEqual(len(registry.minds), 5)
        self.assertIn("MIND-PROOF", registry.minds)


class SafetyAndLineageTests(unittest.TestCase):
    def test_financial_transactions_are_denied_by_default(self):
        self.assertEqual(VXExecutionBoundary.authorize("transfer_funds", "analysis"),
                         (False, "SENSITIVE_SIDE_EFFECT_REQUIRES_SEPARATE_AUTHORITY"))
        self.assertTrue(VXExecutionBoundary.authorize("analyze_or_propose", "analysis")[0])

    def test_ledger_hash_chain_verifies(self):
        ledger = IntegrityLedger()
        first = ledger.append("WF-1", "START", "WF-1", {"goal": "test"})
        second = ledger.append("WF-1", "RESULT", "AG-1", {"status": "PASS"})
        self.assertTrue(ledger.verify())
        self.assertEqual(second.previous_hash, first.event_hash)

    def test_missing_adapters_force_hold(self):
        report = EngineeringOrchestrator().run("Design a resilient engineering workflow")
        self.assertEqual(report.status, "HOLD")
        self.assertGreater(len(report.missing_adapters), 0)
        self.assertFalse(report.decision.production_authorized)
        self.assertTrue(report.ledger_head)
        self.assertTrue(any(item.startswith("live_adapters_missing") for item in report.decision.rationale))

    def test_release_stays_blocked_until_readiness(self):
        orchestrator = EngineeringOrchestrator()
        report = orchestrator.run("Test release gate")
        allowed, reason = orchestrator.authorize_release(report, governance_approval_ref="GOV-123")
        self.assertFalse(allowed)
        self.assertEqual(reason, "CANDIDATE_HAS_NOT_PASSED_READINESS_GATES")


if __name__ == "__main__":
    unittest.main()
