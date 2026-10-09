import json
import unittest
from pathlib import Path

from vx_agents_fabric.registry import default_registry


ROOT = Path(__file__).resolve().parents[1]
ROUTING_PATH = ROOT / "config" / "office_skill_routing.v1.json"
ALLOWED_SKILLS = {
    "brainstorming",
    "using-git-worktrees",
    "writing-plans",
    "subagent-driven-development",
    "executing-plans",
    "test-driven-development",
    "systematic-debugging",
    "requesting-code-review",
    "receiving-code-review",
    "verification-before-completion",
    "finishing-a-development-branch",
}


class OfficeSkillRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(ROUTING_PATH.read_text(encoding="utf-8"))
        cls.registry = default_registry()
        cls.known_roles = {spec.role_id for spec in cls.registry.all_agents()}
        cls.known_roles.update(cls.registry.minds)

    def test_registry_is_versioned_and_explicitly_not_live_verified(self):
        self.assertEqual(self.config["schema_version"], "1.0.0")
        self.assertEqual(self.config["status"], "SPECIFIED")
        self.assertEqual(
            self.config["upstream"]["live_connection_status"], "NOT_VERIFIED"
        )
        self.assertFalse(self.config["upstream"]["is_mcp_server"])

    def test_every_route_uses_known_skills_and_registered_roles(self):
        phases = self.config["phase_routes"]
        self.assertGreaterEqual(len(phases), 8)
        self.assertEqual(len({phase["phase"] for phase in phases}), len(phases))
        for phase in phases:
            self.assertTrue(phase["skills"], phase["phase"])
            self.assertTrue(set(phase["skills"]).issubset(ALLOWED_SKILLS))
            self.assertTrue(phase["required_artifacts"], phase["phase"])
            self.assertTrue(set(phase["role_ids"]).issubset(self.known_roles))
            self.assertTrue(phase["gate"], phase["phase"])

    def test_office_role_ids_exist_in_the_versioned_registry(self):
        for office in self.config["offices"]:
            self.assertTrue(office["role_ids"], office["office_id"])
            self.assertTrue(set(office["role_ids"]).issubset(self.known_roles))

    def test_sensitive_side_effects_are_denied_by_default(self):
        policy = self.config["policy"]
        self.assertEqual(policy["unknown_skill_action"], "HOLD")
        self.assertEqual(policy["missing_adapter_action"], "HOLD")
        self.assertTrue(policy["require_independent_review"])
        self.assertFalse(policy["allow_canonical_mutation"])
        self.assertFalse(policy["allow_production_deploy"])
        self.assertFalse(policy["allow_source_deletion"])
        self.assertFalse(policy["allow_financial_transactions"])
        self.assertFalse(policy["allow_auto_merge"])

    def test_test_and_verification_gates_exist(self):
        routes = {item["phase"]: item for item in self.config["phase_routes"]}
        self.assertIn("test_commands", routes["TEST"]["required_artifacts"])
        self.assertIn("fresh_test_results", routes["VERIFY"]["required_artifacts"])
        self.assertEqual(routes["VERIFY"]["gate"], "INDEPENDENT_EVIDENCE_REQUIRED")

    def test_visual_research_office_uses_registered_roles_and_known_sources(self):
        offices = {item["office_id"]: item for item in self.config["offices"]}
        self.assertIn("Ω.DESIGN", offices)
        self.assertTrue(set(offices["Ω.DESIGN"]["role_ids"]).issubset(self.known_roles))
        sources = {item["source_id"]: item for item in self.config["visual_reference_sources"]}
        self.assertIn("PINTEREST", sources)
        self.assertIn("DRIBBBLE", sources)
        self.assertEqual(
            sources["PINTEREST"]["access_modes"][-1]["status"],
            "ANNOUNCED_PUBLIC_AVAILABILITY_NOT_CONFIRMED",
        )

    def test_visual_research_prohibits_scraping_and_unlicensed_model_training(self):
        sources = {item["source_id"]: item for item in self.config["visual_reference_sources"]}
        pinterest_policy = " ".join(sources["PINTEREST"]["policy_constraints"]).lower()
        dribbble_policy = " ".join(sources["DRIBBBLE"]["policy_constraints"]).lower()
        self.assertIn("scraping", pinterest_policy)
        self.assertIn("train", pinterest_policy)
        self.assertIn("scraping", dribbble_policy)
        routes = {item["phase"]: item for item in self.config["phase_routes"]}
        self.assertIn("VISUAL_RESEARCH", routes)
        self.assertEqual(routes["VISUAL_RESEARCH"]["write_scope"], "none")
        self.assertIn("abstract_pattern_matrix", routes["VISUAL_RESEARCH"]["required_artifacts"])


if __name__ == "__main__":
    unittest.main()
