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
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
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
    token: str | None
    signing_key: bytes
    provider: str
    allowed_providers: frozenset[str]
    allowed_capabilities: frozenset[str]
    allowed_tools: frozenset[str]
    mind_capabilities: tuple[str, ...] = ("reasoning", "verification")
    evidence_path: str = "var/vx_vlns_evidence.sqlite3"
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
        server_enabled = env.get("VLNS_SERVER_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
        configured_url = env.get("VLNS_SERVER_URL", "").strip().rstrip("/") if server_enabled else ""
        return cls(
            required=required,
            base_url=configured_url,
            activation_path=env.get("VLNS_SERVER_ACTIVATION_PATH", "/v1/activations").strip(),
            token=env.get("VLNS_SERVER_TOKEN") or None,
            signing_key=raw_key.encode("utf-8"),
            provider=env.get("VX_VLNS_PROVIDER_ID", "openai-compatible").strip(),
            allowed_providers=_csv(env, "VLNS_ALLOWED_PROVIDERS"),
            allowed_capabilities=_csv(env, "VLNS_ALLOWED_CAPABILITIES"),
            allowed_tools=_csv(env, "VLNS_ALLOWED_TOOLS"),
            mind_capabilities=tuple(sorted(_csv(env, "VX_VLNS_MIND_CAPABILITIES") or {"reasoning", "verification"})),
            evidence_path=env.get("VX_VLNS_EVIDENCE_DB", "var/vx_vlns_evidence.sqlite3").strip(),
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
        if not capabilities or any(not isinstance(item, str) or not item.strip() for item in capabilities):
            return ActivationResult(False, "POLICY_BLOCKED", reason="CAPABILITY_PROFILE_INVALID")
        if set(capabilities) - set(cfg.allowed_capabilities):
            return ActivationResult(False, "POLICY_BLOCKED", reason="CAPABILITY_NOT_ALLOWLISTED")
        if any(not isinstance(item, str) or not item.strip() for item in tools):
            return ActivationResult(False, "POLICY_BLOCKED", reason="TOOL_PROFILE_INVALID")
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
            local_record = VXActivationEvidenceJournal(cfg.evidence_path).record(event)
            if not local_record.get("ok"):
                return ActivationResult(False, "ACTIVATED_EVIDENCE_PENDING", activation_id, digest, str(local_record.get("status", "LOCAL_VX_EVIDENCE_WRITE_FAILED")))
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
        raw_tools = task.payload.get("tool_profile", ())
        if not isinstance(raw_tools, (list, tuple)):
            output_kind = task.agent.outputs[0] if task.agent.outputs else "activation_gate"
            return Artifact(
                artifact_id=task.task_id + ":vlns-gate", kind=output_kind, status="HOLD",
                content={"activation_status": "POLICY_BLOCKED", "reason": "TOOL_PROFILE_INVALID"},
                source_agent=task.agent.role_id, source_version=task.agent.version,
                input_artifact_ids=task.input_artifact_ids,
                limitations=("VLNS_ACTIVATION_GATE_BLOCKED", "TOOL_PROFILE_INVALID"),
            )
        outcome = self.gate.activate(
            model_id=self.model_id,
            model_version=self.model_version,
            role=_role_for_family(task.agent.family),
            capabilities=tuple(task.agent.capabilities),
            task_id=task.task_id,
            source_id=f"vx-workflow://{task.workflow_id}/{task.task_id}",
            context=context,
            tools=tuple(raw_tools),
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


class VLNSGuardedMindAdapter:
    """Gate parent-review mind calls with their own model activation evidence."""

    def __init__(
        self,
        adapter: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        gate: VLNSActivationGate,
        mind_id: str,
        model_id: str,
        model_version: str,
    ) -> None:
        self.adapter = adapter
        self.gate = gate
        self.mind_id = mind_id
        self.model_id = model_id
        self.model_version = model_version

    def __call__(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        safe_payload = dict(payload)
        review_digest = content_hash(safe_payload)
        task_id = str(safe_payload.get("task_id") or ("mind-review-" + self.mind_id + "-" + review_digest[:16]))
        context = {"mind_id": self.mind_id, "review_payload": safe_payload}
        upper = self.mind_id.upper()
        role = (
            "financial_mind" if "FINANCE" in upper else
            "security_mind" if "SECURITY" in upper else
            "verifier_mind" if "PROOF" in upper else
            "architecture_mind" if "ARCH" in upper else
            "research_mind" if "RESEARCH" in upper else
            "governance_mind"
        )
        result = self.gate.activate(
            model_id=self.model_id,
            model_version=self.model_version,
            role=role,
            capabilities=self.gate.config.mind_capabilities,
            task_id=task_id,
            source_id="vx-mind-review://" + self.mind_id,
            context=context,
        )
        if not result.ok:
            return {
                "status": "HOLD",
                "rationale": ["VLNS activation gate blocked parent review: " + result.status, result.reason],
                "evidence_refs": [],
                "hard_gate_failures": ["VLNS_ACTIVATION_" + result.status],
            }
        reviewed = self.adapter(safe_payload)
        if not isinstance(reviewed, Mapping):
            return {
                "status": "HOLD",
                "rationale": ["Parent review returned a non-object result after model activation."],
                "evidence_refs": list(result.evidence_refs),
                "hard_gate_failures": ["PARENT_REVIEW_SCHEMA_INVALID"],
            }
        output = dict(reviewed)
        refs = output.get("evidence_refs", [])
        if not isinstance(refs, list):
            refs = []
        output["evidence_refs"] = list(dict.fromkeys([*refs, *result.evidence_refs]))
        return output


class VXActivationEvidenceJournal:
    """Local, durable, append-only and hash-linked activation evidence journal."""

    def __init__(self, path: str) -> None:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("VX_VLNS_EVIDENCE_DB_REQUIRED")
        self.path = path.strip()

    @staticmethod
    def _digest(value: Mapping[str, Any]) -> str:
        return hashlib.sha256(canonical_json(dict(value)).encode("utf-8")).hexdigest()

    def record(self, event: Mapping[str, Any]) -> dict[str, Any]:
        activation_id = event.get("activation_id")
        if not isinstance(activation_id, str) or not activation_id:
            return {"ok": False, "status": "LOCAL_EVENT_ID_REQUIRED"}
        if event.get("event_type") != "VLNS_MODEL_ACTIVATION_CONFIRMED":
            return {"ok": False, "status": "LOCAL_EVENT_TYPE_INVALID"}
        event_id = "vlns-activation:" + activation_id
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)

        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(self.path)
            with connection:
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS activation_events (
                        sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT NOT NULL UNIQUE,
                        event_type TEXT NOT NULL,
                        aggregate_id TEXT NOT NULL,
                        actor_id TEXT NOT NULL,
                        capability TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        previous_hash TEXT NOT NULL,
                        event_hash TEXT NOT NULL UNIQUE
                    )"""
                )
                existing = connection.execute(
                    "SELECT sequence,event_type,aggregate_id,payload_json,event_hash FROM activation_events WHERE event_id=?",
                    (event_id,),
                ).fetchone()
                payload_json = canonical_json(dict(event))
                if existing is not None:
                    if (
                        existing[1] == event["event_type"]
                        and existing[2] == activation_id
                        and existing[3] == payload_json
                        and self.verify_integrity(connection)
                    ):
                        head = connection.execute(
                            "SELECT event_hash FROM activation_events ORDER BY sequence DESC LIMIT 1"
                        ).fetchone()
                        return {
                            "ok": True, "status": "LOCAL_VX_EVENT_ALREADY_RECORDED",
                            "data": {"event_id": event_id, "event_hash": existing[4],
                                     "sequence": existing[0], "ledger_head": head[0] if head else "GENESIS"},
                        }
                    return {"ok": False, "status": "LOCAL_VX_EVENT_ID_COLLISION_OR_LEDGER_INVALID"}

                head = connection.execute(
                    "SELECT event_hash FROM activation_events ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                previous_hash = head[0] if head else "GENESIS"
                created_at = datetime.now(timezone.utc).isoformat()
                body = {
                    "event_id": event_id,
                    "event_type": str(event["event_type"]),
                    "aggregate_id": activation_id,
                    "actor_id": "VX:vx-agents-fabric",
                    "capability": "model_activation",
                    "payload": dict(event),
                    "created_at": created_at,
                }
                event_hash = self._digest({**body, "previous_hash": previous_hash})
                cursor = connection.execute(
                    """INSERT INTO activation_events(
                        event_id,event_type,aggregate_id,actor_id,capability,payload_json,
                        created_at,previous_hash,event_hash
                    ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (event_id, body["event_type"], activation_id, body["actor_id"], body["capability"],
                     payload_json, created_at, previous_hash, event_hash),
                )
                if not self.verify_integrity(connection):
                    return {"ok": False, "status": "LOCAL_VX_LEDGER_INTEGRITY_FAILED"}
                return {
                    "ok": True,
                    "status": "LOCAL_VX_EVENT_RECORDED",
                    "data": {
                        "event_id": event_id, "event_hash": event_hash,
                        "sequence": int(cursor.lastrowid), "ledger_head": event_hash,
                    },
                }
        except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
            return {"ok": False, "status": "LOCAL_VX_EVIDENCE_WRITE_FAILED:" + type(exc).__name__}
        finally:
            if connection is not None:
                connection.close()

    def verify_integrity(self, connection: sqlite3.Connection | None = None) -> bool:
        owned = connection is None
        conn = connection or sqlite3.connect(self.path)
        try:
            rows = conn.execute(
                """SELECT event_id,event_type,aggregate_id,actor_id,capability,payload_json,
                          created_at,previous_hash,event_hash
                   FROM activation_events ORDER BY sequence"""
            ).fetchall()
            previous = "GENESIS"
            for row in rows:
                event_id, event_type, aggregate_id, actor_id, capability, payload_json, created_at, previous_hash, event_hash = row
                try:
                    payload = json.loads(payload_json)
                except json.JSONDecodeError:
                    return False
                body = {
                    "event_id": event_id, "event_type": event_type, "aggregate_id": aggregate_id,
                    "actor_id": actor_id, "capability": capability, "payload": payload,
                    "created_at": created_at, "previous_hash": previous,
                }
                if previous_hash != previous or self._digest(body) != event_hash:
                    return False
                previous = event_hash
            return True
        except sqlite3.Error:
            return False
        finally:
            if owned:
                conn.close()


__all__ = [
    "ActivationResult", "VLNSActivationGate", "VLNSGateConfig", "VLNSGuardedAgentAdapter", "VLNSGuardedMindAdapter", "VXActivationEvidenceJournal",
]
