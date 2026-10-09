import json
import unittest
from unittest.mock import patch

from vx_agents_fabric.contracts import AgentSpec, TaskEnvelope
from vx_agents_fabric.providers import OpenAICompatibleProvider, ProviderError, build_from_env
from vx_agents_fabric.registry import default_registry


class FakeResponse:
    def __init__(self, body):
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def read(self):
        return self.body


class ProviderBindingTests(unittest.TestCase):
    def test_no_endpoint_means_no_provider_connected(self):
        bindings = build_from_env(environ={})
        self.assertFalse(bindings.enabled)
        self.assertEqual(dict(bindings.agent_adapters), {})
        self.assertTrue(bindings.unconfigured_agent_versions)

    def test_family_and_exact_version_model_routing(self):
        registry = default_registry()
        env = {
            "VX_OPENAI_COMPAT_BASE_URL": "http://127.0.0.1:11434/v1",
            "VX_RESEARCH_MODEL": "research-model",
            "VX_FINANCE_MODEL": "finance-model",
            "VX_ENGINEERING_MODEL": "engineering-model",
            "VX_AGENT_MODEL_VX_ENG_TEST_1_1_0": "test-v1.1",
            "VX_AGENT_MODEL_VX_ENG_TEST_1_0_0": "test-v1.0",
        }
        for mind_id in registry.minds:
            env["VX_MIND_MODEL_" + mind_id.replace("-", "_")] = "review-" + mind_id.lower()
        bindings = build_from_env(registry, env)
        self.assertTrue(bindings.enabled)
        self.assertEqual(bindings.agent_models["VX-ENG-TEST@1.1.0"], "test-v1.1")
        self.assertEqual(bindings.agent_models["VX-ENG-TEST@1.0.0"], "test-v1.0")
        self.assertEqual(bindings.agent_models["VX-FIN-RISK@1.1.0"], "finance-model")
        self.assertEqual(len(bindings.mind_adapters), 5)

    def test_model_cannot_add_new_evidence_reference(self):
        provider = OpenAICompatibleProvider("http://127.0.0.1:11434/v1", "test-model")
        spec = AgentSpec("VX-TEST", "Test Agent", "research", "1.0.0", ("research",),
                         ("goal",), ("research_report",), "research")
        payload = {
            "context": {"research": {"sources": [{"url": "https://evidence.example/paper"}]}},
            "prior_artifacts": [{"evidence_refs": ["ledger://evidence-001"]}],
        }
        task = TaskEnvelope("WF:task", "WF", "RESEARCH", "Test", spec, payload, (), "research", "research_report")
        model_result = {
            "status": "PROPOSED", "kind": "research_report", "content": {"finding": "tentative"},
            "evidence_refs": ["https://evidence.example/paper", "ledger://evidence-001", "https://invented.example/"],
            "limitations": [],
        }
        api_result = {"choices": [{"message": {"content": json.dumps(model_result)}}]}
        with patch("vx_agents_fabric.providers.openai_compatible.urlopen",
                   return_value=FakeResponse(json.dumps(api_result).encode("utf-8"))):
            artifact = provider.agent_adapter(task)
        self.assertEqual(artifact.evidence_refs, ("https://evidence.example/paper", "ledger://evidence-001"))
        self.assertIn("unverified_provider_evidence_refs_filtered", artifact.limitations)

    def test_invalid_provider_response_fails_closed(self):
        provider = OpenAICompatibleProvider("http://127.0.0.1:11434/v1", "test-model")
        with patch("vx_agents_fabric.providers.openai_compatible.urlopen",
                   return_value=FakeResponse(b"not-json")):
            with self.assertRaises(ProviderError):
                provider._ask("Return JSON", {"task": "test"})


if __name__ == "__main__":
    unittest.main()
