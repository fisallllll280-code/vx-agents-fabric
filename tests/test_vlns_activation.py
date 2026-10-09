from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from vx_agents_fabric.contracts import AgentSpec, Artifact, TaskEnvelope, content_hash
from vx_agents_fabric.providers import build_from_env
from vx_agents_fabric.registry import AgentRegistry
from vx_agents_fabric.vlns_activation import (
    VLNSActivationGate,
    VLNSGateConfig,
    VLNSGuardedAgentAdapter,
    VLNSGuardedMindAdapter,
    VXActivationEvidenceJournal,
)


KEY = b"test-only-vlns-signing-key-at-least-32-bytes"


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.payload


def task(family="engineering", capabilities=("engineering", "code_review")):
    spec = AgentSpec(
        role_id="VX-ENG-ARCH",
        name="Architecture Engineer",
        family=family,
        version="1.0.0",
        capabilities=capabilities,
        inputs=("goal",),
        outputs=("architecture_report",),
        authority_scope="planning",
    )
    return TaskEnvelope(
        task_id="task-001",
        workflow_id="WF-001",
        stage="ARCHITECTURE",
        goal="Design an integration contract",
        agent=spec,
        payload={"goal": "Design an integration contract"},
        input_artifact_ids=(),
        authority_scope="proposal",
        required_output="architecture_report",
    )


def config(*, base_url="https://vlns.example", capabilities=("engineering", "code_review")):
    return VLNSGateConfig(
        required=True,
        base_url=base_url,
        activation_path="/v1/activations",
        evidence_path=":memory:",
        token="test-token",
        signing_key=KEY,
        provider="openai-compatible",
        allowed_providers=frozenset({"openai-compatible"}),
        allowed_capabilities=frozenset(capabilities),
        allowed_tools=frozenset(),
        mind_capabilities=("reasoning", "verification"),
    )


class VLNSActivationGateTests(unittest.TestCase):
    def test_missing_server_configuration_blocks_before_inference(self):
        calls = []
        inner = lambda _: calls.append("called") or Artifact(
            artifact_id="a", kind="architecture_report", status="PROPOSED",
            content={}, source_agent="VX-ENG-ARCH", source_version="1.0.0"
        )
        guarded = VLNSGuardedAgentAdapter(inner, VLNSActivationGate(config(base_url="")), "model-x", "model-x:v1")
        result = guarded(task())
        self.assertEqual(result.status, "HOLD")
        self.assertIn("NOT_CONFIGURED", result.limitations)
        self.assertEqual(calls, [])

    def test_remote_receipt_and_local_ledger_gate_model_inference(self):
        calls = []

        def opener(request, timeout):
            if request.full_url.endswith("/v1/activations"):
                envelope = json.loads(request.data.decode("utf-8"))
                return FakeResponse(json.dumps({
                    "status": "ACTIVATED",
                    "activation_id": envelope["activation_id"],
                    "envelope_hash": content_hash(envelope),
                }).encode("utf-8"))
            raise AssertionError("VLNS server must not receive local VX evidence events: " + request.full_url)

        inner = lambda _: calls.append("model-called") or Artifact(
            artifact_id="a", kind="architecture_report", status="PROPOSED",
            content={"design": "candidate"}, source_agent="VX-ENG-ARCH", source_version="1.0.0"
        )
        guarded = VLNSGuardedAgentAdapter(inner, VLNSActivationGate(config()), "model-x", "model-x:rev-1")
        with patch("vx_agents_fabric.vlns_activation.urlopen", side_effect=opener):
            result = guarded(task())

        self.assertEqual(calls, ["model-called"])
        self.assertEqual(result.status, "PROPOSED")
        self.assertTrue(any(ref.startswith("vlns-activation://") for ref in result.evidence_refs))
        self.assertTrue(any(ref.startswith("vlns-envelope-sha256://") for ref in result.evidence_refs))
        self.assertIn("VLNS_PRE_ACTIVATION_CONFIRMED", result.limitations)

    def test_mismatched_receipt_blocks_model_inference(self):
        calls = []

        def opener(request, timeout):
            envelope = json.loads(request.data.decode("utf-8"))
            return FakeResponse(json.dumps({
                "status": "ACTIVATED",
                "activation_id": "VLNS-ACT-wrong",
                "envelope_hash": content_hash(envelope),
            }).encode("utf-8"))

        inner = lambda _: calls.append("model-called")
        guarded = VLNSGuardedAgentAdapter(
            inner, VLNSActivationGate(config()), "model-x", "model-x:rev-1"
        )
        with patch("vx_agents_fabric.vlns_activation.urlopen", side_effect=opener):
            result = guarded(task())

        self.assertEqual(result.status, "HOLD")
        self.assertIn("RECEIPT_INVALID", result.limitations)
        self.assertEqual(calls, [])

    def test_server_url_is_ignored_when_server_enable_flag_is_false(self):
        cfg = VLNSGateConfig.from_env({
            "VX_VLNS_ACTIVATION_REQUIRED": "true",
            "VLNS_SERVER_URL": "https://vlns.example",
            "VLNS_SERVER_ENABLED": "false",
            "VLNS_ACTIVATION_SIGNING_KEY": KEY.decode("utf-8"),
            "VX_VLNS_PROVIDER_ID": "openai-compatible",
            "VLNS_ALLOWED_PROVIDERS": "openai-compatible",
            "VLNS_ALLOWED_CAPABILITIES": "reasoning,verification",
        })
        self.assertEqual(cfg.base_url, "")
        outcome = VLNSActivationGate(cfg).activate(
            model_id="review-model", model_version="review-model:rev-1",
            role="verifier_mind", capabilities=("reasoning", "verification"),
            task_id="test-disabled", source_id="review-source", context={"claim": "test"},
        )
        self.assertFalse(outcome.ok)
        self.assertEqual(outcome.status, "NOT_CONFIGURED")

    def test_missing_capability_allowlist_blocks_activation(self):
        gate = VLNSActivationGate(config(capabilities=("engineering",)))
        result = gate.activate(
            model_id="model-x",
            model_version="model-x:rev-1",
            role="engineering_mind",
            capabilities=("engineering", "code_review"),
            task_id="task-001",
            source_id="source-001",
            context={"goal": "review"},
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "POLICY_BLOCKED")
        self.assertEqual(result.reason, "CAPABILITY_NOT_ALLOWLISTED")

    def test_parent_mind_is_also_gated(self):
        calls = []
        gate = VLNSActivationGate(config(capabilities=("reasoning", "verification")))
        review = VLNSGuardedMindAdapter(
            lambda _: calls.append("review-called") or {
                "status": "PASS", "rationale": [], "evidence_refs": [], "hard_gate_failures": []
            },
            gate, "MIND_FINANCE", "finance-model", "finance-model:rev-1"
        )

        with patch("vx_agents_fabric.vlns_activation.urlopen", side_effect=OSError("not configured")):
            result = review({"claim": "candidate decision"})

        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(calls, [])
        self.assertTrue(result["hard_gate_failures"][0].startswith("VLNS_ACTIVATION_"))



    def test_local_vx_evidence_journal_is_hash_linked_and_idempotent(self):
        event = {
            "event_type": "VLNS_MODEL_ACTIVATION_CONFIRMED",
            "activation_id": "VLNS-ACT-" + "a" * 24,
            "envelope_hash": "a" * 64,
            "provider": "openai-compatible",
            "model_id": "model-x",
            "model_version": "model-x:rev-1",
            "role": "engineering_mind",
            "context_hash": "b" * 64,
            "provenance": {"task_id": "task-001", "source_id": "src-001", "source_digest": "c" * 64},
            "evidence_status": "REMOTE_RECEIPT_VALIDATED",
        }
        with tempfile.TemporaryDirectory() as tmp:
            journal = VXActivationEvidenceJournal(os.path.join(tmp, "activation-events.sqlite3"))
            first = journal.record(event)
            second = journal.record(event)
            self.assertTrue(first["ok"])
            self.assertEqual(first["status"], "LOCAL_VX_EVENT_RECORDED")
            self.assertTrue(second["ok"])
            self.assertEqual(second["status"], "LOCAL_VX_EVENT_ALREADY_RECORDED")
            self.assertTrue(journal.verify_integrity())

    def test_factory_wraps_configured_agents_when_gate_is_required(self):
        registry = AgentRegistry()
        spec = AgentSpec(
            role_id="VX-RES-COORD", name="Research Coordinator", family="research",
            version="1.0.0", capabilities=("research", "decomposition"),
            inputs=("goal",), outputs=("research_plan",), authority_scope="planning",
        )
        registry.register(spec)
        env = {
            "VX_OPENAI_COMPAT_BASE_URL": "http://127.0.0.1:11434/v1",
            "VX_RESEARCH_MODEL": "research-model",
            "VX_VLNS_ACTIVATION_REQUIRED": "true",
            "VX_VLNS_PROVIDER_ID": "openai-compatible",
            "VLNS_ALLOWED_PROVIDERS": "openai-compatible",
            "VLNS_ALLOWED_CAPABILITIES": "research,decomposition",
            "VLNS_ALLOWED_TOOLS": "",
            "VLNS_ACTIVATION_SIGNING_KEY": KEY.decode("utf-8"),
        }
        bindings = build_from_env(registry, env)
        self.assertTrue(bindings.vlns_activation_required)
        self.assertFalse(bindings.vlns_gate_configured)
        guarded = bindings.agent_adapters["VX-RES-COORD@1.0.0"]
        result = guarded(TaskEnvelope(
            task_id="T1", workflow_id="WF1", stage="INTAKE", goal="discover",
            agent=spec, payload={"goal": "discover"}, input_artifact_ids=(),
            authority_scope="planning", required_output="research_plan",
        ))
        self.assertEqual(result.status, "HOLD")
        self.assertIn("NOT_CONFIGURED", result.limitations)

if __name__ == "__main__":
    unittest.main()
