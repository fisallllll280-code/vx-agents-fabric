"""VX-gated engineering workflow orchestration with explicit missing-adapter handling."""
from __future__ import annotations
from dataclasses import asdict
from typing import Any, Callable, Mapping
from .contracts import AgentRunResult, Artifact, EngineeringDecision, TaskEnvelope, WorkflowReport, content_hash
from .ledger import IntegrityLedger
from .registry import AgentRegistry, default_registry

AgentAdapter = Callable[[TaskEnvelope], Artifact | Mapping[str, Any]]

PIPELINE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("INTAKE", ("VX-ENG-COORD", "VX-RES-COORD")),
    ("RESEARCH", ("VX-RES-SOURCE", "VX-RES-LITERATURE", "VX-RES-REPO", "VX-RES-REPRO", "VX-RES-CONTRA", "VX-RES-SYNTH")),
    ("FINANCIAL_FEASIBILITY", ("VX-FIN-COORD", "VX-FIN-MARKET", "VX-FIN-UNIT", "VX-FIN-COST", "VX-FIN-PRICE", "VX-FIN-RISK", "VX-FIN-COMP", "VX-FIN-PORT")),
    ("ARCHITECTURE", ("VX-ENG-REQ", "VX-ENG-ARCH")),
    ("INNOVATION", ("VX-ENG-INNOV",)),
    ("BUILD_PLAN_AND_IMPLEMENTATION", ("VX-ENG-BUILD",)),
    ("VALIDATION", ("VX-ENG-TEST", "VX-ENG-RED", "VX-ENG-PROOF")),
    ("OPERATIONS_AND_LEARNING", ("VX-ENG-OPS", "VX-ENG-LEARN")),
)


class VXExecutionBoundary:
    FORBIDDEN_ACTIONS = {
        "canonical_mutation", "production_deploy", "delete_source", "external_payment",
        "execute_trade", "transfer_funds", "change_access_policy", "publish_irreversible",
    }
    ALLOWED_SCOPES = {
        "read-only", "research", "analysis", "planning", "proposal", "verification",
        "sandbox", "sandbox-write", "decision-proposal",
    }

    @classmethod
    def authorize(cls, action: str, authority_scope: str) -> tuple[bool, str]:
        if action in cls.FORBIDDEN_ACTIONS:
            return False, "SENSITIVE_SIDE_EFFECT_REQUIRES_SEPARATE_AUTHORITY"
        if authority_scope not in cls.ALLOWED_SCOPES:
            return False, "UNKNOWN_OR_UNGRANTED_AUTHORITY_SCOPE"
        return True, "WITHIN_DECLARED_SCOPE"


class EngineeringDecisionEngine:
    MIND_IDS = ("MIND-SYS-ARCH", "MIND-RESEARCH", "MIND-FINANCE", "MIND-SECURITY", "MIND-PROOF")

    @classmethod
    def decide(cls, results: list[AgentRunResult], artifacts: list[Artifact],
               missing_adapters: list[str], ledger_valid: bool) -> EngineeringDecision:
        rationale: list[str] = []
        evidence_refs = sorted({ref for artifact in artifacts for ref in artifact.evidence_refs})
        statuses = {result.status for result in results}
        if not ledger_valid:
            rationale.append("workflow_ledger_integrity_failed")
            status = "REJECT"
        elif any(result.status in {"FAIL", "BLOCKED"} for result in results):
            rationale.append("one_or_more_specialists_failed_or_were_blocked")
            status = "REJECT"
        elif missing_adapters:
            rationale.append("live_adapters_missing:" + ",".join(sorted(set(missing_adapters)))
            status = "HOLD"
        elif not artifacts:
            rationale.append("no_artifacts_generated")
            status = "HOLD"
        elif not evidence_refs:
            rationale.append("no_external_or_reproducible_evidence_references")
            status = "HOLD"
        elif not {"PASS", "VERIFIED"}.intersection(statuses):
            rationale.append("no_specialist_report_marked_pass_or_verified")
            status = "HOLD"
        else:
            rationale.append("candidate_outputs_present; governance and release authorization remain separate")
            status = "CANDIDATE_READY_FOR_GOVERNANCE"
        return EngineeringDecision(status, tuple(rationale), cls.MIND_IDS, tuple(evidence_refs), False)


class EngineeringOrchestrator:
    def __init__(self, registry: AgentRegistry | None = None,
                 adapters: Mapping[str, AgentAdapter] | None = None,
                 ledger: IntegrityLedger | None = None) -> None:
        self.registry = registry or default_registry()
        self.adapters = dict(adapters or {})
        self.ledger = ledger or IntegrityLedger()
        self.boundary = VXExecutionBoundary()

    def run(self, goal: str, *, workflow_id: str = "WF-ENGINEERING-001",
            context: Mapping[str, Any] | None = None) -> WorkflowReport:
        if not goal.strip():
            raise ValueError("goal_required")
        context_payload = dict(context or {})
        report = WorkflowReport(workflow_id=workflow_id, goal=goal, status="RUNNING")
        self.ledger.append(workflow_id, "WORKFLOW_STARTED", workflow_id, {"goal_hash": content_hash(goal)})

        for stage, role_ids in PIPELINE:
            for role_id in role_ids:
                spec = self.registry.resolve(role_id)
                task_id = f"{workflow_id}:{stage}:{role_id}"
                inputs = tuple(artifact.artifact_id for artifact in report.artifacts)
                task_payload = {
                    "goal": goal, "context": context_payload,
                    "prior_artifacts": [
                        {"artifact_id": a.artifact_id, "kind": a.kind, "status": a.status,
                         "sha256": a.sha256, "evidence_refs": list(a.evidence_refs)}
                        for a in report.artifacts
                    ],
                    "stage": stage, "required_output": spec.outputs,
                    "invariants": [
                        "preserve_source_lineage", "separate_fact_assumption_hypothesis",
                        "do_not_claim_unrun_tests", "do_not_mutate_canonical_state",
                    ],
                }
                envelope = TaskEnvelope(task_id, workflow_id, stage, goal, spec, task_payload,
                                        inputs, spec.authority_scope, ",".join(spec.outputs))
                permitted, reason = self.boundary.authorize("analyze_or_propose", spec.authority_scope)
                if not permitted:
                    result = AgentRunResult(task_id, role_id, spec.version, stage, "BLOCKED", None,
                                            "AUTHORITY_DENIED", reason)
                    report.results.append(result)
                    self.ledger.append(workflow_id, "AGENT_BLOCKED", task_id, asdict(result))
                    continue
                adapter = self.adapters.get(role_id)
                if adapter is None:
                    report.missing_adapters.append(role_id)
                    result = AgentRunResult(task_id, role_id, spec.version, stage, "NOT_CONFIGURED", None,
                                            "PROVIDER_ADAPTER_MISSING",
                                            "Role registered; provider/model adapter has not been connected.")
                    report.results.append(result)
                    self.ledger.append(workflow_id, "ADAPTER_MISSING", task_id, asdict(result))
                    continue
                try:
                    raw = adapter(envelope)
                    if isinstance(raw, Artifact):
                        artifact = raw
                    elif isinstance(raw, Mapping):
                        artifact = Artifact(
                            artifact_id=str(raw.get("artifact_id", task_id + ":artifact")),
                            kind=str(raw.get("kind", spec.outputs[0])),
                            status=str(raw.get("status", "PROPOSED")),
                            content=dict(raw.get("content", raw)), source_agent=role_id,
                            source_version=spec.version, input_artifact_ids=inputs,
                            evidence_refs=tuple(raw.get("evidence_refs", ())),
                            limitations=tuple(raw.get("limitations", ())),
                        )
                    else:
                        raise TypeError("adapter_must_return_Artifact_or_mapping")
                    if artifact.source_agent != role_id or artifact.source_version != spec.version:
                        raise ValueError("artifact_provenance_does_not_match_invoked_agent")
                    if tuple(artifact.input_artifact_ids) != inputs:
                        raise ValueError("artifact_input_lineage_mismatch")
                    artifact = artifact.with_digest()
                    report.artifacts.append(artifact)
                    result = AgentRunResult(task_id, role_id, spec.version, stage, artifact.status,
                                            artifact.artifact_id)
                    self.ledger.append(workflow_id, "ARTIFACT_RECORDED", artifact.artifact_id, {
                        "sha256": artifact.sha256, "source_agent": role_id,
                        "source_version": spec.version, "input_artifact_ids": inputs,
                        "evidence_refs": artifact.evidence_refs,
                    })
                except Exception as exc:
                    result = AgentRunResult(task_id, role_id, spec.version, stage, "FAIL", None,
                                            "AGENT_EXECUTION_ERROR", type(exc).__name__ + ":" + str(exc))
                    self.ledger.append(workflow_id, "AGENT_FAILED", task_id, asdict(result))
                report.results.append(result)

        decision = EngineeringDecisionEngine.decide(
            report.results, report.artifacts, report.missing_adapters, self.ledger.verify()
        )
        report.decision = decision
        self.ledger.append(workflow_id, "PARENT_DECISION", workflow_id, asdict(decision))
        report.status = decision.status
        report.event_count = len(self.ledger.events())
        report.ledger_head = self.ledger.head
        return report

    def authorize_release(self, report: WorkflowReport, *, governance_approval_ref: str | None = None) -> tuple[bool, str]:
        """A separate connected governance system must actually authorize production effects."""
        if not governance_approval_ref or not governance_approval_ref.strip():
            return False, "GOVERNANCE_APPROVAL_REFERENCE_REQUIRED"
        if report.decision is None or report.decision.status != "CANDIDATE_READY_FOR_GOVERNANCE":
            return False, "CANDIDATE_HAS_NOT_PASSED_READINESS_GATES"
        if not self.ledger.verify():
            return False, "LEDGER_INTEGRITY_FAILED"
        return False, "GOVERNANCE_ADAPTER_NOT_CONNECTED; no production side effect performed"
