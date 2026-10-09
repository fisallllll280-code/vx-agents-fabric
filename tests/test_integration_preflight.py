"""No-network tests for the signed integration preflight gate."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import tempfile
import unittest
from pathlib import Path

from vx_agents_fabric.integration_preflight import (
    SCHEMA_VERSION,
    attestation_signature,
    evaluate_attestation,
    preflight,
)

SECRET = "test-only-key-with-more-than-thirty-two-bytes"
NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def make_attestation(
    provider_id,
    *,
    endpoint=None,
    capabilities=None,
    evidence=None,
    operations=None,
    probe_result="PASS",
    observed=None,
    expires=None,
):
    endpoints = {
        "SUPERPOWERS": "https://github.com/obra/superpowers",
        "UI_UX_PRO_MAX": "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill",
        "HIGGSFIELD": "https://mcp.higgsfield.ai/mcp",
        "WHATSAPP_BUSINESS_CLOUD_API": "https://graph.facebook.com/v23.0/123456/messages",
    }
    types = {
        "SUPERPOWERS": "agent_skill",
        "UI_UX_PRO_MAX": "agent_skill",
        "HIGGSFIELD": "remote_mcp",
        "WHATSAPP_BUSINESS_CLOUD_API": "cloud_api",
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "provider_id": provider_id,
        "integration_type": types[provider_id],
        "endpoint": endpoint or endpoints[provider_id],
        "host_id": "trusted-test-probe",
        "observed_at": (observed or NOW).isoformat(),
        "expires_at": (expires or (NOW + timedelta(hours=12))).isoformat(),
        "probe_result": probe_result,
        "capabilities": list(capabilities or []),
        "available_operations": list(operations or []),
        "evidence": [
            {
                "kind": item,
                "sha256": ("a" * 64),
                "uri": "artifact://test/" + item,
            }
            for item in (evidence or [])
        ],
    }
    payload["signature_hmac_sha256"] = attestation_signature(payload, SECRET)
    return payload


class IntegrationPreflightTests(unittest.TestCase):
    def test_no_attestation_never_claims_connected(self):
        result = evaluate_attestation("HIGGSFIELD", None, secret=SECRET, now=NOW)
        self.assertEqual(result.state, "NOT_CONFIGURED")
        self.assertFalse(result.connection_verified)
        self.assertFalse(result.operational_verified)

    def test_invalid_signature_fails_closed(self):
        att = make_attestation(
            "SUPERPOWERS",
            capabilities=[
                "brainstorming", "writing_plans", "test_driven_development",
                "systematic_debugging", "verification_before_completion",
            ],
            evidence=["skill_manifest", "skill_invocation_receipt"],
        )
        att["signature_hmac_sha256"] = "0" * 64
        result = evaluate_attestation("SUPERPOWERS", att, secret=SECRET, now=NOW)
        self.assertEqual(result.state, "INVALID_ATTESTATION")
        self.assertIn("attestation_signature_mismatch", result.reasons)

    def test_wrong_endpoint_is_rejected(self):
        att = make_attestation(
            "HIGGSFIELD",
            endpoint="https://lookalike.example/mcp",
            capabilities=["image_generation", "video_generation"],
            evidence=["mcp_initialize_receipt", "mcp_tools_list_receipt",
                      "image_generation_approval_receipt", "image_job_receipt",
                      "video_generation_approval_receipt", "video_job_receipt"],
            operations=["create_image", "create_video"],
        )
        result = evaluate_attestation("HIGGSFIELD", att, secret=SECRET, now=NOW)
        self.assertEqual(result.state, "INVALID_ATTESTATION")
        self.assertIn("endpoint_not_in_official_allowlist", result.reasons)

    def test_stale_attestation_is_expired_even_if_signature_is_valid(self):
        observed = NOW - timedelta(hours=30)
        att = make_attestation(
            "UI_UX_PRO_MAX",
            capabilities=["design_system_generation"],
            evidence=["skill_manifest", "version_metadata", "design_output_sample"],
            observed=observed,
            expires=NOW + timedelta(hours=12),
        )
        result = evaluate_attestation("UI_UX_PRO_MAX", att, secret=SECRET, now=NOW)
        self.assertEqual(result.state, "EXPIRED")
        self.assertFalse(result.connection_verified)

    def test_higgsfield_can_be_connected_but_not_operational_without_job_receipts(self):
        att = make_attestation(
            "HIGGSFIELD",
            capabilities=["image_generation", "video_generation"],
            evidence=["mcp_initialize_receipt", "mcp_tools_list_receipt"],
            operations=["actual_image_tool", "actual_video_tool"],
        )
        result = evaluate_attestation("HIGGSFIELD", att, secret=SECRET, now=NOW)
        self.assertEqual(result.state, "CONNECTED_NOT_OPERATIONAL")
        self.assertTrue(result.connection_verified)
        self.assertFalse(result.operational_verified)
        self.assertTrue(any("image_job_receipt" in item for item in result.reasons))

    def test_higgsfield_requires_real_tool_discovery_and_image_video_evidence(self):
        att = make_attestation(
            "HIGGSFIELD",
            capabilities=["image_generation", "video_generation"],
            evidence=["mcp_initialize_receipt", "mcp_tools_list_receipt",
                      "image_generation_approval_receipt", "image_job_receipt",
                      "video_generation_approval_receipt", "video_job_receipt"],
            operations=["actual_image_tool", "actual_video_tool"],
        )
        result = evaluate_attestation("HIGGSFIELD", att, secret=SECRET, now=NOW)
        self.assertEqual(result.state, "OPERATIONAL")
        self.assertEqual(set(result.available_operations), {"actual_image_tool", "actual_video_tool"})

    def test_whatsapp_needs_connection_and_live_acceptance_evidence(self):
        capabilities = ["inbound_webhook", "outbound_send", "delivery_status_webhook", "recipient_consent_gate"]
        connected_evidence = ["business_account_check", "webhook_verification_receipt"]
        att = make_attestation("WHATSAPP_BUSINESS_CLOUD_API",
                               capabilities=capabilities, evidence=connected_evidence)
        result = evaluate_attestation("WHATSAPP_BUSINESS_CLOUD_API", att, secret=SECRET, now=NOW)
        self.assertEqual(result.state, "CONNECTED_NOT_OPERATIONAL")
        operational_evidence = connected_evidence + [
            "inbound_test_message_receipt", "outbound_test_message_receipt",
            "delivery_status_webhook_receipt", "signature_negative_test", "consent_negative_test",
        ]
        att = make_attestation("WHATSAPP_BUSINESS_CLOUD_API",
                               capabilities=capabilities, evidence=operational_evidence)
        result = evaluate_attestation("WHATSAPP_BUSINESS_CLOUD_API", att, secret=SECRET, now=NOW)
        self.assertEqual(result.state, "OPERATIONAL")

    def test_missing_skill_capabilities_never_count_as_connected(self):
        att = make_attestation("SUPERPOWERS",
                               capabilities=["brainstorming"],
                               evidence=["skill_manifest", "skill_invocation_receipt"])
        result = evaluate_attestation("SUPERPOWERS", att, secret=SECRET, now=NOW)
        self.assertEqual(result.state, "INCOMPLETE")
        self.assertFalse(result.connection_verified)

    def test_attestation_requires_timezone_aware_timestamps(self):
        att = make_attestation("UI_UX_PRO_MAX",
                               capabilities=["design_system_generation"],
                               evidence=["skill_manifest", "version_metadata", "design_output_sample"])
        att["observed_at"] = "2026-10-09T12:00:00"
        att["signature_hmac_sha256"] = attestation_signature(att, SECRET)
        result = evaluate_attestation("UI_UX_PRO_MAX", att, secret=SECRET, now=NOW)
        self.assertEqual(result.state, "INVALID_ATTESTATION")
        self.assertIn("timestamp_timezone_required", result.reasons)

    def test_preflight_is_read_only_and_returns_all_missing_integrations(self):
        config = {
            "upstream": {"name": "Superpowers"},
            "design_intelligence_integrations": [{"integration_id": "UI_UX_PRO_MAX"}],
            "media_generation_provider": {"provider_id": "HIGGSFIELD"},
            "communication_integrations": [{"integration_id": "WHATSAPP_BUSINESS_CLOUD_API"}],
        }
        with tempfile.TemporaryDirectory() as temp:
            result = preflight(config, temp, secret=None, now=NOW)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["operational_count"], 0)
        self.assertEqual(result["integration_count"], 4)
        self.assertTrue(all(x["state"] == "NOT_CONFIGURED" for x in result["checks"]))
        self.assertFalse(result["safety"]["external_calls_made"])
        self.assertFalse(result["safety"]["paid_jobs_submitted"])
        self.assertFalse(result["safety"]["messages_sent"])
        self.assertFalse(result["safety"]["canonical_state_mutated"])

    def test_short_signing_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "at_least_32_bytes"):
            attestation_signature({"provider_id": "HIGGSFIELD"}, "short")


if __name__ == "__main__":
    unittest.main(verbosity=2)
