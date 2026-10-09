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

    def test_higgsfield_is_declared_as_official_remote_mcp_but_not_live_verified(self):
        provider = self.config["media_generation_provider"]
        self.assertEqual(provider["canonical_name"], "Higgsfield")
        self.assertIn("Xfield", provider["accepted_aliases"])
        self.assertEqual(provider["official_mcp_endpoint"], "https://mcp.higgsfield.ai/mcp")
        self.assertEqual(provider["connection_status"], "NOT_VERIFIED")
        self.assertEqual(provider["tool_discovery_status"], "NOT_VERIFIED")
        self.assertIn("text-to-image", provider["capabilities_intents"])
        self.assertIn("image-to-video", provider["capabilities_intents"])

    def test_media_routes_have_cost_rights_and_acceptance_gates(self):
        routes = {item["phase"]: item for item in self.config["phase_routes"]}
        self.assertIn("Ω.MEDIA", {item["office_id"] for item in self.config["offices"]})
        self.assertEqual(
            routes["MEDIA_COST_AND_APPROVAL"]["on_unknown_cost"], "HOLD_COST_UNKNOWN"
        )
        self.assertFalse(routes["MEDIA_COST_AND_APPROVAL"]["auto_top_up"])
        self.assertEqual(
            routes["IMAGE_GENERATION"]["gate"],
            "CONNECTED_TOOL_AND_APPROVED_COST_CEILING_REQUIRED",
        )
        self.assertFalse(routes["IMAGE_GENERATION"]["auto_publish"])
        self.assertFalse(routes["VIDEO_GENERATION"]["auto_publish"])
        self.assertFalse(routes["MEDIA_REVIEW_AND_LEARNING"]["auto_canonical_adoption"])
        self.assertIn("asset_sha256", routes["IMAGE_GENERATION"]["required_artifacts"])
        self.assertIn("playback_and_motion_review", routes["VIDEO_GENERATION"]["required_artifacts"])

    def test_higgsfield_example_config_uses_the_official_remote_endpoint(self):
        example_path = ROOT / "config" / "higgsfield_mcp.example.json"
        example = json.loads(example_path.read_text(encoding="utf-8"))
        self.assertEqual(
            example["mcpServers"]["higgsfield"]["url"],
            "https://mcp.higgsfield.ai/mcp",
        )
        self.assertEqual(example["mcpServers"]["higgsfield"]["type"], "http")
        self.assertEqual(set(example.keys()), {"mcpServers"})

    def test_ui_ux_pro_max_route_and_official_install_metadata(self):
        integration = next(
            item for item in self.config["design_intelligence_integrations"]
            if item["integration_id"] == "UI_UX_PRO_MAX"
        )
        self.assertEqual(
            integration["upstream_repository"],
            "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill",
        )
        self.assertEqual(integration["installed_status"], "NOT_VERIFIED")
        self.assertTrue(integration["install_for_claude_code"])
        routes = {item["phase"]: item for item in self.config["phase_routes"]}
        self.assertIn("UIUX_DESIGN_SYSTEM", routes)
        self.assertEqual(routes["UIUX_DESIGN_SYSTEM"]["design_engine"], "UI_UX_PRO_MAX")
        self.assertEqual(
            routes["UIUX_DESIGN_SYSTEM"]["gate"],
            "DESIGN_SYSTEM_REVIEW_BEFORE_CANONICAL_PERSISTENCE",
        )
        self.assertTrue(routes["UIUX_DESIGN_SYSTEM"]["canonical_persist_requires_approval"])
        self.assertIn("accessibility_review", routes["UIUX_DESIGN_SYSTEM"]["required_artifacts"])


if __name__ == "__main__":
    unittest.main()
