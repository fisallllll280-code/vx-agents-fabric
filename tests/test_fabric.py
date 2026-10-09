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

    def test_default_catalog_retains_parallel_specialist_versions(self):
        registry = default_registry()
        self.assertEqual(len(registry.versions("VX-ENG-TEST")), 2)
        self.assertEqual(registry.resolve("VX-ENG-TEST").version, "1.1.0")
        self.assertEqual(registry.resolve("VX-ENG-TEST", "1.0.0").version, "1.0.0")
        self.assertGreater(
            registry.resolve("VX-ENG-TEST").outputs.count("replay_report"), 0
        )

    def test_agent_input_families_are_explicitly_scoped(self):
        registry = default_registry()
        research = registry.resolve("VX-RES-SOURCE")
        finance = registry.resolve("VX-FIN-RISK")
        engineering = registry.resolve("VX-ENG-ARCH")
        self.assertEqual(set(research.input_families), {"shared", "research"})
        self.assertEqual(set(finance.input_families), {"shared", "research", "finance"})
        self.assertIn("engineering", engineering.input_families)
        self.assertNotIn("finance", research.input_families)


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

    def test_missing_adapters_force_hold_and_are_not_misreported_as_reviews(self):
        report = EngineeringOrchestrator().run("Design a resilient engineering workflow")
        self.assertEqual(report.status, "HOLD")
        self.assertGreater(len(report.missing_adapters), 0)
        self.assertFalse(report.decision.production_authorized)
        self.assertTrue(report.ledger_head)
        self.assertEqual(report.decision.reviewed_minds, ())
        self.assertTrue(any(item.startswith("live_adapters_missing") for item in report.decision.rationale))

    def test_configured_agent_and_mind_adapters_produce_governance_candidate_only(self):
        registry = default_registry()
        observed_context = {}
        def agent_adapter(envelope):
            observed_context[envelope.agent.role_id] = {
                "context": dict(envelope.payload["context"]),
                "visible_families": tuple(envelope.payload["visible_input_families"]),
                "prior_sources": tuple(item["source_agent"] for item in envelope.payload["prior_artifacts"]),
            }
            return {
                "artifact_id": envelope.task_id + ":artifact",
                "kind": envelope.required_output,
                "status": "PASS",
                "content": {"task_id": envelope.task_id, "goal": envelope.goal},
                "evidence_refs": ["fixture://evidence/" + envelope.agent.role_id],
            }
        agent_adapters = {spec.role_id: agent_adapter for spec in registry.all_agents()}
        def make_mind_adapter(mind_id):
            return lambda context: {
                "status": "PASS",
                "rationale": ["independent fixture review only"],
                "evidence_refs": ["fixture://mind-review/" + mind_id],
                "hard_gate_failures": [],
            }
        mind_adapters = {mind_id: make_mind_adapter(mind_id) for mind_id in registry.minds}
        orchestrator = EngineeringOrchestrator(
            registry, agent_adapters, mind_adapters, version_pins={"VX-ENG-TEST": "1.0.0"}
        )
        report = orchestrator.run(
            "Test the engineering pipeline", workflow_id="WF-TEST-FULL",
            context={
                "shared": {"intent": "safe-to-share"},
                "research": {"source_note": "research-only"},
                "finance": {"budget_note": "finance-only"},
                "engineering": {"design_note": "engineering-only"},
            },
        )
        self.assertEqual(report.status, "CANDIDATE_READY_FOR_GOVERNANCE")
        self.assertIn("finance", observed_context["VX-FIN-RISK"]["context"])
        self.assertNotIn("engineering", observed_context["VX-FIN-RISK"]["context"])
        self.assertNotIn("finance", observed_context["VX-RES-SOURCE"]["context"])
        self.assertIn("research", observed_context["VX-ENG-ARCH"]["context"])
        self.assertIn("finance", observed_context["VX-ENG-ARCH"]["context"])
        self.assertNotIn("finance", observed_context["VX-RES-SOURCE"]["visible_families"])
        self.assertNotIn("VX-ENG-COORD", observed_context["VX-FIN-RISK"]["prior_sources"])
        test_result = next(item for item in report.results if item.agent_id == "VX-ENG-TEST")
        self.assertEqual(test_result.agent_version, "1.0.0")
        self.assertEqual(len(report.mind_reviews), len(registry.minds))
        self.assertEqual(set(report.decision.reviewed_minds), set(registry.minds))
        self.assertFalse(report.decision.production_authorized)
        allowed, reason = orchestrator.authorize_release(report, governance_approval_ref="GOV-EXAMPLE")
        self.assertFalse(allowed)
        self.assertIn("GOVERNANCE_ADAPTER_NOT_CONNECTED", reason)


if __name__ == "__main__":
    unittest.main()
