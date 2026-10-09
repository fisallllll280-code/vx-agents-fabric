"""Optional fail-closed VLNS pre-activation gate for VX specialist agents.

This adapter keeps model calls off until VLNS returns a receipt bound to the
signed activation envelope and acknowledges an evidence event. No network call
is made when a guarded wrapper is created.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import hmac
import json
import os
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .contracts import Artifact, TaskEnvelope, content_hash


SCHEMA_VERSION = "vlns.activation-envelope.v1"
SIGNATURE_ALGORITHM = "HMAC-SHA256"
IDENTITY_FIELDS = (
    "schema_version", "model_id", "provider", "model_version", "role",
    "capability_profile", "context_hash", "tool_profile", "permission_profile",
    "constraints", "provenance",
)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _csv(environ: Mapping[str, str], name: str) -> frozenset[str]:
    return frozenset(item.strip() for item in environ.get(name, "").split(",") if item.strip())


def _fragment(value: str) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()


def _role_for_family(family: str) -> str:
    return {
        "research": "research_mind",
        "finance": "financial_mind",
        "engineering": "engineering_mind",
        "governance": "governance_mind",
        "operations": "operations_mind",
    }.get(family, "reasoning_mind")


@dataclass(frozen=True)
class VLNSGateConfig:
    required: bool
    base_url: str
    activation_path: str
    event_path: str
    token: str | None
    signing_key: bytes
    provider: str
    allowed_providers: frozenset[str]
    allowed_capabilities: frozenset[str]
    allowed_tools: frozenset[str]
    timeout_seconds: float = 8.0

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "VLNSGateConfig":
        env = environ if environ is not None else os.environ
        required = env.get("VX_VLNS_ACTIVATION_REQUIRED", "false").strip().lower() in {"1", "true", "yes"}
        raw_timeout = env.get("VX_VLNS_ACTIVATION_TIMEOUT", "8")
        try:
            timeout = float(raw_timeout)
        except ValueError as exc:
            raise ValueError("VX_VLNS_ACTIVATION_TIMEOUT_must_be_numeric") from exc
        if timeout <= 0:
            raise ValueError("VX_VLNS_ACTIVATION_TIMEOUT_must_be_positive")
        raw_key = env.get("VLNS_ACTIVATION_SIGNING_KEY", "")
        return cls(
            required=required,
            base_url=env.get("VLNS_SERVER_URL", "").strip().rstrip("/"),
            activation_path=env.get("VLNS_SERVER_ACTIVATION_PATH", "/v1/activations").strip(),
            event_path=env.get("VLNS_SERVER_EVENT_PATH", "/events").strip(),
            token=env.get("VLNS_SERVER_TOKEN") or None,
            signing_key=raw_key.encode("utf-8"),
            provider=env.get("VX_VLNS_PROVIDER_ID", "openai-compatible").strip(),
            allowed_providers=_csv(env, "VLNS_ALLOWED_PROVIDERS"),
            allowed_capabilities=_csv(env, "VLNS_ALLOWED_CAPABILITIES"),
            allowed_tools=_csv(env, "VLNS_ALLOWED_TOOLS"),
            timeout_seconds=timeout,
        )


@dataclass(frozen=True)
class ActivationResult:
    ok: bool
    status: str
    activation_id: str = ""
    envelope_hash: str = ""
    reason: str = ""

    @property
    def evidence_refs(self) -> tuple[str, ...]:
        if not self.ok:
            return ()
        return (
            f"vlns-activation://{self.activation_id}",
            f"vlns-envelope-sha256://{self.envelope_hash}",
        )


class VLNSActivationGate:
    def __init__(self, config: VLNSGateConfig) -> None:
        self.config = config

    def _request(self, path: str, payload: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        url = self.config.base_url + "/" + path.lstrip("/")
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.config.token:
            headers["Authorization"] = "Bearer " + self.config.token
        body = canonical_json(dict(payload)).encode("utf-8")
        with urlopen(
            Request(url, data=body, headers=headers, method="POST"),
            timeout=self.config.timeout_seconds,
        ) as response:
            raw = response.read()
            decoded = json.loads(raw.decode("utf-8")) if raw else {}
            if not isinstance(decoded, Mapping):
                raise ValueError("VLNS_RESPONSE_MUST_BE_OBJECT")
            return response.status, decoded

    def activate(
        self,
        *,
        model_id: str,
        model_version: str,
        role: str,
        capabilities: tuple[str, ...],
        task_id: str,
        source_id: str,
        context: Mapping[str, Any],
        tools: tuple[str, ...] = (),
    ) -> ActivationResult:
        cfg = self.config
        if not cfg.required:
            return ActivationResult(False, "NOT_REQUIRED", reason="activation gate is not required")
        parsed = urlsplit(cfg.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ActivationResult(False, "NOT_CONFIGURED", reason="VLNS_SERVER_URL_NOT_CONFIGURED")
        if len(cfg.signing_key) < 32:
            return ActivationResult(False, "NOT_CONFIGURED", reason="VLNS_ACTIVATION_SIGNING_KEY_TOO_SHORT_OR_MISSING")
        if cfg.provider not in cfg.allowed_providers:
            return ActivationResult(False, "POLICY_BLOCKED", reason="PROVIDER_NOT_ALLOWLISTED")
        if not capabilities or set(capabilities) - set(cfg.allowed_capabilities):
            return ActivationResult(False, "POLICY_BLOCKED", reason="CAPABILITY_NOT_ALLOWLISTED")
        if set(tools) - set(cfg.allowed_tools):
            return ActivationResult(False, "POLICY_BLOCKED", reason="TOOL_NOT_ALLOWLISTED")

        context_digest = content_hash(dict(context))
        provenance = {
            "task_id": task_id,
            "source_id": source_id,
            "source_digest": context_digest,
        }
        identity = {
            "schema_version": SCHEMA_VERSION,
            "model_id": model_id,
            "provider": cfg.provider,
            "model_version": model_version,
            "role": role,
            "capability_profile": sorted(set(capabilities)),
            "context_hash": context_digest,
            "tool_profile": sorted(set(tools)),
            "permission_profile": ["propose", "read"],
            "constraints": ["no_canonical_mutation", "no_unreviewed_execution"],
            "provenance": provenance,
        }
        activation_id = "VLNS-ACT-" + content_hash(identity)[:24]
        envelope: dict[str, Any] = {
            **identity,
            "activation_id": activation_id,
            "status": "PREPARED",
            "signature_algorithm": SIGNATURE_ALGORITHM,
        }
        envelope["signature"] = hmac.new(
            cfg.signing_key, canonical_json(envelope).encode("utf-8"), hashlib.sha256
        ).hexdigest()
        digest = content_hash(envelope)
        try:
            status_code, receipt = self._request(cfg.activation_path, envelope)
            if not 200 <= status_code < 300:
                return ActivationResult(False, "TRANSPORT_FAILED", activation_id, digest, "ACTIVATION_HTTP_STATUS")
            if receipt.get("status") != "ACTIVATED":
                return ActivationResult(False, "REMOTE_REJECTED", activation_id, digest, str(receipt.get("reason", receipt.get("status", "REMOTE_REJECTED"))))
            if receipt.get("activation_id") != activation_id or receipt.get("envelope_hash") != digest:
                return ActivationResult(False, "RECEIPT_INVALID", activation_id, digest, "RECEIPT_ID_OR_HASH_MISMATCH")
            event = {
                "event_type": "VLNS_MODEL_ACTIVATION_CONFIRMED",
                "activation_id": activation_id,
                "envelope_hash": digest,
                "provider": cfg.provider,
                "model_id": model_id,
                "model_version": model_version,
                "role": role,
                "context_hash": context_digest,
                "provenance": provenance,
                "evidence_status": "REMOTE_RECEIPT_VALIDATED",
            }
            event_status, _event_receipt = self._request(cfg.event_path, event)
            if not 200 <= event_status < 300:
                return ActivationResult(False, "ACTIVATED_EVIDENCE_PENDING", activation_id, digest, "EVIDENCE_EVENT_NOT_ACKNOWLEDGED")
            return ActivationResult(True, "ACTIVATED_AND_RECORDED", activation_id, digest)
        except HTTPError as exc:
            return ActivationResult(False, "TRANSPORT_FAILED", activation_id, digest, f"HTTP_ERROR_{exc.code}")
        except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            return ActivationResult(False, "TRANSPORT_FAILED", activation_id, digest, "TRANSPORT_OR_RESPONSE_ERROR:" + type(exc).__name__)


class VLNSGuardedAgentAdapter:
    def __init__(
        self,
        adapter: Callable[[TaskEnvelope], Artifact],
        gate: VLNSActivationGate,
        model_id: str,
        model_version: str,
    ) -> None:
        self.adapter = adapter
        self.gate = gate
        self.model_id = model_id
        self.model_version = model_version

    def __call__(self, task: TaskEnvelope) -> Artifact:
        context = {
            "task_id": task.task_id, "workflow_id": task.workflow_id, "stage": task.stage,
            "goal": task.goal, "payload": dict(task.payload),
            "input_artifact_ids": list(task.input_artifact_ids),
            "agent": {"role_id": task.agent.role_id, "version": task.agent.version, "family": task.agent.family},
        }
        outcome = self.gate.activate(
            model_id=self.model_id,
            model_version=self.model_version,
            role=_role_for_family(task.agent.family),
            capabilities=tuple(task.agent.capabilities),
            task_id=task.task_id,
            source_id=f"vx-workflow://{task.workflow_id}/{task.task_id}",
            context=context,
            tools=tuple(task.payload.get("tool_profile", ())) if isinstance(task.payload.get("tool_profile", ()), (list, tuple)) else (),
        )
        if not outcome.ok:
            output_kind = task.agent.outputs[0] if task.agent.outputs else "activation_gate"
            return Artifact(
                artifact_id=task.task_id + ":vlns-gate",
                kind=output_kind,
                status="HOLD",
                content={"activation_status": outcome.status, "reason": outcome.reason},
                source_agent=task.agent.role_id,
                source_version=task.agent.version,
                input_artifact_ids=task.input_artifact_ids,
                limitations=("VLNS_ACTIVATION_GATE_BLOCKED", outcome.status, outcome.reason),
            )
        result = self.adapter(task)
        return replace(
            result,
            evidence_refs=tuple(dict.fromkeys((*result.evidence_refs, *outcome.evidence_refs))),
            limitations=tuple(dict.fromkeys((*result.limitations, "VLNS_PRE_ACTIVATION_CONFIRMED"))),
        )


__all__ = [
    "ActivationResult", "VLNSActivationGate", "VLNSGateConfig", "VLNSGuardedAgentAdapter",
]
