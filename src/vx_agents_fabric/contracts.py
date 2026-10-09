"""Deterministic contracts shared by VX specialist agents."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def content_hash(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AgentSpec:
    role_id: str
    name: str
    family: str
    version: str
    capabilities: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    authority_scope: str
    required_evidence: tuple[str, ...] = ()
    required_proofs: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    enabled: bool = True
    admission_status: str = "DESIGN_ONLY"

    @property
    def key(self) -> str:
        return f"{self.role_id}@{self.version}"


@dataclass(frozen=True)
class MindSpec:
    mind_id: str
    purpose: str
    provider: str
    model_version: str
    role_ids: tuple[str, ...]
    independent_review: bool = True
    status: str = "DECLARED_NOT_CONNECTED"


@dataclass(frozen=True)
class TaskEnvelope:
    task_id: str
    workflow_id: str
    stage: str
    goal: str
    agent: AgentSpec
    payload: Mapping[str, Any]
    input_artifact_ids: tuple[str, ...]
    authority_scope: str
    required_output: str


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    kind: str
    status: str
    content: Mapping[str, Any]
    source_agent: str
    source_version: str
    input_artifact_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    sha256: str = ""

    def with_digest(self) -> "Artifact":
        material = {
            "artifact_id": self.artifact_id, "kind": self.kind, "status": self.status,
            "content": dict(self.content), "source_agent": self.source_agent,
            "source_version": self.source_version, "input_artifact_ids": list(self.input_artifact_ids),
            "evidence_refs": list(self.evidence_refs), "limitations": list(self.limitations),
        }
        return Artifact(**{**asdict(self), "sha256": content_hash(material)})


@dataclass(frozen=True)
class AgentRunResult:
    task_id: str
    agent_id: str
    agent_version: str
    stage: str
    status: str
    artifact_id: str | None
    error_code: str | None = None
    message: str = ""


@dataclass(frozen=True)
class WorkflowEvent:
    sequence: int
    workflow_id: str
    event_type: str
    subject_id: str
    payload_hash: str
    previous_hash: str
    event_hash: str


@dataclass(frozen=True)
class EngineeringDecision:
    status: str
    rationale: tuple[str, ...]
    reviewed_minds: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    production_authorized: bool = False


@dataclass
class WorkflowReport:
    workflow_id: str
    goal: str
    status: str
    results: list[AgentRunResult] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    decision: EngineeringDecision | None = None
    event_count: int = 0
    ledger_head: str = ""
    missing_adapters: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id, "goal": self.goal, "status": self.status,
            "result_count": len(self.results), "artifact_count": len(self.artifacts),
            "missing_adapters": sorted(set(self.missing_adapters)),
            "decision": asdict(self.decision) if self.decision else None,
            "event_count": self.event_count, "ledger_head": self.ledger_head,
        }
