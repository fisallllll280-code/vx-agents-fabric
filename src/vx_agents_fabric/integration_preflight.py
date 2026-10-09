"""Fail-closed preflight for externally hosted Prompt Office integrations.

A routing entry is a specification, not proof of installation or connectivity.
Only a trusted host-side probe may write and HMAC-sign runtime attestations.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping
from urllib.parse import urlparse

SCHEMA_VERSION = "1.0.0"
MAX_ATTESTATION_BYTES = 128_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# Official endpoints are trust anchors; runtime manifests may not introduce
# endpoints from user/model content.
POLICIES: dict[str, dict[str, Any]] = {
    "SUPERPOWERS": {
        "integration_type": "agent_skill",
        "official_endpoint": "https://github.com/obra/superpowers",
        "connect_capabilities": (
            "brainstorming", "writing_plans", "test_driven_development",
            "systematic_debugging", "verification_before_completion",
        ),
        "connect_evidence": ("skill_manifest",),
        "operational_evidence": ("skill_invocation_receipt",),
        "needs_operations": (),
    },
    "UI_UX_PRO_MAX": {
        "integration_type": "agent_skill",
        "official_endpoint": "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill",
        "connect_capabilities": ("design_system_generation",),
        "connect_evidence": ("skill_manifest", "version_metadata"),
        "operational_evidence": ("design_output_sample",),
        "needs_operations": (),
    },
    "HIGGSFIELD": {
        "integration_type": "remote_mcp",
        "official_endpoint": "https://mcp.higgsfield.ai/mcp",
        "connect_capabilities": ("image_generation", "video_generation"),
        "connect_evidence": ("mcp_initialize_receipt", "mcp_tools_list_receipt"),
        "operational_evidence": ("image_job_receipt", "video_job_receipt"),
        "needs_operations": ("image_generation", "video_generation"),
    },
    "WHATSAPP_BUSINESS_CLOUD_API": {
        "integration_type": "cloud_api",
        "official_endpoint_host": "graph.facebook.com",
        "connect_capabilities": (
            "outbound_send", "inbound_webhook", "delivery_status_webhook",
        ),
        "connect_evidence": ("business_account_check", "webhook_verification_receipt"),
        "operational_evidence": (
            "inbound_test_message_receipt", "outbound_test_message_receipt",
            "delivery_status_webhook_receipt", "signature_negative_test",
        ),
        "needs_operations": ("inbound_webhook", "outbound_send", "delivery_status_webhook"),
    },
}

TOP_LEVEL_KEYS = {
    "schema_version", "provider_id", "integration_type", "endpoint", "host_id",
    "observed_at", "expires_at", "probe_result", "capabilities",
    "available_operations", "evidence", "signature_hmac_sha256",
}
EVIDENCE_KEYS = {"kind", "sha256", "uri"}


@dataclass(frozen=True)
class IntegrationCheck:
    provider_id: str
    state: str
    connection_verified: bool
    operational_verified: bool
    reasons: tuple[str, ...]
    observed_at: str | None = None
    expires_at: str | None = None
    evidence_kinds: tuple[str, ...] = ()
    available_operations: tuple[str, ...] = ()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    )


def attestation_signature(payload: Mapping[str, Any], secret: str) -> str:
    """Sign an attestation payload; call only inside a trusted host-side probe."""
    if not isinstance(secret, str) or len(secret.encode("utf-8")) < 32:
        raise ValueError("attestation_key_must_be_at_least_32_bytes")
    unsigned = dict(payload)
    unsigned.pop("signature_hmac_sha256", None)
    return hmac.new(
        secret.encode("utf-8"),
        canonical_json(unsigned).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp_missing")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp_timezone_required")
    return parsed.astimezone(timezone.utc)


def _endpoint_matches(provider_id: str, endpoint: Any) -> bool:
    if not isinstance(endpoint, str):
        return False
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    policy = POLICIES[provider_id]
    if "official_endpoint" in policy:
        return endpoint.rstrip("/") == policy["official_endpoint"].rstrip("/")
    if provider_id == "WHATSAPP_BUSINESS_CLOUD_API":
        return (
            parsed.hostname == policy["official_endpoint_host"]
            and bool(re.match(r"^/v\d+\.\d+(?:/|$)", parsed.path))
        )
    return False


def _declared(config: Mapping[str, Any], provider_id: str) -> bool:
    if provider_id == "SUPERPOWERS":
        return (
            isinstance(config.get("upstream"), Mapping)
            and config["upstream"].get("name") == "Superpowers"
        )
    if provider_id == "UI_UX_PRO_MAX":
        return any(
            isinstance(item, Mapping) and item.get("integration_id") == provider_id
            for item in config.get("design_intelligence_integrations", [])
        )
    if provider_id == "HIGGSFIELD":
        return (
            isinstance(config.get("media_generation_provider"), Mapping)
            and config["media_generation_provider"].get("provider_id") == provider_id
        )
    if provider_id == "WHATSAPP_BUSINESS_CLOUD_API":
        return any(
            isinstance(item, Mapping) and item.get("integration_id") == provider_id
            for item in config.get("communication_integrations", [])
        )
    return False


def _validate_shape(attestation: Any) -> None:
    if not isinstance(attestation, Mapping):
        raise ValueError("attestation_root_must_be_object")
    if set(attestation.keys()) != TOP_LEVEL_KEYS:
        raise ValueError("attestation_keys_missing_or_unexpected")
    if attestation.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("attestation_schema_version_unsupported")
    for name in ("provider_id", "integration_type", "endpoint", "host_id"):
        if not isinstance(attestation.get(name), str) or not attestation[name].strip():
            raise ValueError("attestation_field_invalid:" + name)
    if attestation.get("probe_result") not in {"PASS", "FAIL"}:
        raise ValueError("attestation_probe_result_invalid")
    if not isinstance(attestation.get("capabilities"), list) or not all(
        isinstance(item, str) and item.strip() for item in attestation["capabilities"]
    ):
        raise ValueError("attestation_capabilities_invalid")
    if not isinstance(attestation.get("available_operations"), list) or not all(
        isinstance(item, str) and item.strip() for item in attestation["available_operations"]
    ):
        raise ValueError("attestation_available_operations_invalid")
    evidence = attestation.get("evidence")
    if not isinstance(evidence, list):
        raise ValueError("attestation_evidence_invalid")
    for item in evidence:
        if not isinstance(item, Mapping) or set(item.keys()) - EVIDENCE_KEYS:
            raise ValueError("attestation_evidence_item_invalid")
        if not isinstance(item.get("kind"), str) or not item["kind"].strip():
            raise ValueError("attestation_evidence_kind_invalid")
        if not isinstance(item.get("sha256"), str) or not SHA256_RE.fullmatch(item["sha256"]):
            raise ValueError("attestation_evidence_hash_invalid")
        if "uri" in item and (
            not isinstance(item["uri"], str)
            or not item["uri"].startswith(("https://", "file://", "artifact://"))
        ):
            raise ValueError("attestation_evidence_uri_invalid")
    signature = attestation.get("signature_hmac_sha256")
    if not isinstance(signature, str) or not SHA256_RE.fullmatch(signature):
        raise ValueError("attestation_signature_invalid_shape")


def evaluate_attestation(
    provider_id: str,
    attestation: Any,
    *,
    secret: str | None,
    now: datetime | None = None,
    max_age: timedelta = timedelta(hours=24),
) -> IntegrationCheck:
    """Validate signed host evidence and return CONNECTED/OPERATIONAL only when justified."""
    if provider_id not in POLICIES:
        return IntegrationCheck(provider_id, "UNKNOWN_INTEGRATION", False, False,
                                ("integration_not_in_preapproved_policy",))
    if attestation is None:
        return IntegrationCheck(provider_id, "NOT_CONFIGURED", False, False,
                                ("runtime_attestation_missing",))
    if not secret or len(secret.encode("utf-8")) < 32:
        return IntegrationCheck(provider_id, "ATTESTATION_KEY_NOT_CONFIGURED", False, False,
                                ("trusted_attestation_key_missing_or_too_short",))
    try:
        _validate_shape(attestation)
        if attestation["provider_id"] != provider_id:
            raise ValueError("attestation_provider_mismatch")
        policy = POLICIES[provider_id]
        if attestation["integration_type"] != policy["integration_type"]:
            raise ValueError("attestation_integration_type_mismatch")
        if not _endpoint_matches(provider_id, attestation["endpoint"]):
            raise ValueError("endpoint_not_in_official_allowlist")
        expected_signature = attestation_signature(attestation, secret)
        if not hmac.compare_digest(expected_signature, attestation["signature_hmac_sha256"]):
            raise ValueError("attestation_signature_mismatch")
        observed = _parse_time(attestation["observed_at"])
        expires = _parse_time(attestation["expires_at"])
        reference_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if observed > reference_now + timedelta(minutes=5):
            raise ValueError("attestation_observed_in_future")
        if expires <= observed:
            raise ValueError("attestation_expiry_not_after_observation")
        if reference_now - observed > max_age:
            return IntegrationCheck(provider_id, "EXPIRED", False, False,
                                    ("attestation_older_than_freshness_window",),
                                    observed.isoformat(), expires.isoformat())
        if expires <= reference_now:
            return IntegrationCheck(provider_id, "EXPIRED", False, False,
                                    ("attestation_expired",), observed.isoformat(), expires.isoformat())
        if attestation["probe_result"] != "PASS":
            return IntegrationCheck(provider_id, "PROBE_FAILED", False, False,
                                    ("host_probe_reported_failure",), observed.isoformat(),
                                    expires.isoformat())
        capabilities = set(attestation["capabilities"])
        needed_caps = set(policy["connect_capabilities"])
        missing_caps = sorted(needed_caps - capabilities)
        evidence_kinds = {item["kind"] for item in attestation["evidence"]}
        missing_evidence = sorted(set(policy["connect_evidence"]) - evidence_kinds)
        if provider_id == "HIGGSFIELD" and not attestation["available_operations"]:
            missing_evidence.append("actual_mcp_tools_list")
        if missing_caps or missing_evidence:
            reasons = tuple(
                ["missing_capabilities:" + ",".join(missing_caps)] if missing_caps else []
            ) + tuple(
                ["missing_connect_evidence:" + ",".join(missing_evidence)] if missing_evidence else []
            )
            return IntegrationCheck(provider_id, "INCOMPLETE", False, False, reasons,
                                    observed.isoformat(), expires.isoformat(),
                                    tuple(sorted(evidence_kinds)),
                                    tuple(sorted(attestation["available_operations"])))
        missing_operational = sorted(set(policy["operational_evidence"]) - evidence_kinds)
        missing_operations = sorted(set(policy["needs_operations"]) - capabilities)
        if missing_operational or missing_operations:
            reasons = tuple(
                ["missing_operational_evidence:" + ",".join(missing_operational)]
                if missing_operational else []
            ) + tuple(
                ["missing_operational_capabilities:" + ",".join(missing_operations)]
                if missing_operations else []
            )
            return IntegrationCheck(provider_id, "CONNECTED_NOT_OPERATIONAL", True, False,
                                    reasons, observed.isoformat(), expires.isoformat(),
                                    tuple(sorted(evidence_kinds)),
                                    tuple(sorted(attestation["available_operations"])))
        return IntegrationCheck(provider_id, "OPERATIONAL", True, True,
                                ("signed_fresh_probe_and_operational_evidence_passed",),
                                observed.isoformat(), expires.isoformat(),
                                tuple(sorted(evidence_kinds)),
                                tuple(sorted(attestation["available_operations"])))
    except (ValueError, TypeError, KeyError) as exc:
        reason = str(exc) or "attestation_invalid"
        return IntegrationCheck(provider_id, "INVALID_ATTESTATION", False, False, (reason,))


def preflight(
    config: Mapping[str, Any],
    attestation_dir: str | Path,
    *,
    secret: str | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Read-only status report; never opens external connections or starts paid jobs."""
    directory = Path(attestation_dir)
    checks: list[IntegrationCheck] = []
    for provider_id, policy in POLICIES.items():
        if not _declared(config, provider_id):
            checks.append(IntegrationCheck(
                provider_id, "NOT_DECLARED", False, False,
                ("integration_not_declared_in_routing_registry",),
            ))
            continue
        path = directory / (provider_id.lower() + ".json")
        if not path.exists():
            checks.append(IntegrationCheck(
                provider_id, "NOT_CONFIGURED", False, False,
                ("runtime_attestation_missing", "no_live_connection_claimed"),
            ))
            continue
        try:
            raw_bytes = path.read_bytes()
            if len(raw_bytes) > MAX_ATTESTATION_BYTES:
                raise ValueError("attestation_file_too_large")
            attestation = json.loads(raw_bytes.decode("utf-8"))
            checks.append(evaluate_attestation(provider_id, attestation, secret=secret, now=now))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            checks.append(IntegrationCheck(
                provider_id, "INVALID_ATTESTATION", False, False,
                ("attestation_read_or_parse_failed:" + type(exc).__name__,),
            ))
    states = [check.state for check in checks]
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "READ_ONLY_PREFLIGHT",
        "status": "OPERATIONAL" if checks and all(s == "OPERATIONAL" for s in states) else "PARTIAL",
        "operational_count": sum(check.operational_verified for check in checks),
        "connected_count": sum(check.connection_verified for check in checks),
        "integration_count": len(checks),
        "checks": [asdict(check) for check in checks],
        "safety": {
            "external_calls_made": False,
            "paid_jobs_submitted": False,
            "messages_sent": False,
            "canonical_state_mutated": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only preflight for Prompt Office integrations; never sends messages or generates media."
    )
    parser.add_argument("--config", default="config/office_skill_routing.v1.json")
    parser.add_argument("--attestation-dir", default="runtime/integration-attestations")
    parser.add_argument("--output", help="Optional output JSON path; stdout is the default.")
    args = parser.parse_args(argv)
    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        if not isinstance(config, Mapping):
            raise ValueError("routing_config_root_must_be_object")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        sys.stderr.write("integration_preflight_config_error:" + type(exc).__name__ + "\n")
        return 4
    report = preflight(config, args.attestation_dir,
                       secret=os.environ.get("VX_INTEGRATION_ATTESTATION_HMAC_KEY"))
    rendered = json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        try:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            sys.stderr.write("integration_preflight_output_error:" + type(exc).__name__ + "\n")
            return 4
    else:
        sys.stdout.write(rendered)
    return 0 if report["status"] == "OPERATIONAL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
