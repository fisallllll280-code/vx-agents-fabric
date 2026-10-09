"""Version-aware specialist and multi-mind registries."""
from __future__ import annotations
from dataclasses import dataclass, field
import re
from typing import Iterable
from .contracts import AgentSpec, MindSpec


def _version_key(version: str) -> tuple[int, int, int, str]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:[-+]([0-9A-Za-z.-]+))?", version)
    if not match:
        raise ValueError(f"version_must_be_semver_like:{version}")
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)), match.group(4) or "")


@dataclass
class AgentRegistry:
    _versions: dict[str, dict[str, AgentSpec]] = field(default_factory=dict)
    _aliases: dict[str, str] = field(default_factory=dict)
    minds: dict[str, MindSpec] = field(default_factory=dict)

    def register(self, spec: AgentSpec) -> None:
        if not spec.role_id.strip() or not spec.name.strip():
            raise ValueError("agent_identity_required")
        _version_key(spec.version)
        versions = self._versions.setdefault(spec.role_id, {})
        if spec.version in versions:
            if versions[spec.version] != spec:
                raise ValueError(f"immutable_version_conflict:{spec.key}")
            return
        for alias in spec.aliases:
            key = alias.strip().casefold()
            owner = self._aliases.get(key)
            if key and owner and owner != spec.role_id:
                raise ValueError(f"alias_collision:{alias}")
        versions[spec.version] = spec
        for alias in spec.aliases:
            if alias.strip():
                self._aliases[alias.strip().casefold()] = spec.role_id

    def register_mind(self, mind: MindSpec) -> None:
        old = self.minds.get(mind.mind_id)
        if old and old != mind:
            raise ValueError(f"mind_identity_conflict:{mind.mind_id}")
        self.minds[mind.mind_id] = mind

    def resolve(self, role_or_alias: str, version: str | None = None) -> AgentSpec:
        role_id = role_or_alias if role_or_alias in self._versions else self._aliases.get(role_or_alias.casefold())
        if not role_id or role_id not in self._versions:
            raise KeyError(f"agent_not_found:{role_or_alias}")
        versions = self._versions[role_id]
        if version is not None:
            if version not in versions:
                raise KeyError(f"agent_version_not_found:{role_id}@{version}")
            spec = versions[version]
            if not spec.enabled:
                raise PermissionError(f"agent_disabled:{spec.key}")
            return spec
        available = [item for item in versions.values() if item.enabled]
        if not available:
            raise PermissionError(f"no_enabled_version:{role_id}")
        return max(available, key=lambda item: _version_key(item.version))

    def versions(self, role_id: str) -> tuple[AgentSpec, ...]:
        return tuple(sorted(self._versions.get(role_id, {}).values(), key=lambda item: _version_key(item.version)))

    def all_agents(self) -> tuple[AgentSpec, ...]:
        return tuple(item for role_id in sorted(self._versions) for item in self.versions(role_id))

    def find_capability(self, capability: str) -> tuple[AgentSpec, ...]:
        matches = [item for item in self.all_agents() if item.enabled and capability in item.capabilities]
        return tuple(sorted(matches, key=lambda item: (item.family, item.role_id, _version_key(item.version))))

    def add_many(self, specs: Iterable[AgentSpec]) -> None:
        for spec in specs:
            self.register(spec)


def _spec(role_id: str, name: str, family: str, caps: tuple[str, ...],
          inputs: tuple[str, ...], outputs: tuple[str, ...], authority: str,
          evidence: tuple[str, ...] = (), aliases: tuple[str, ...] = ()) -> AgentSpec:
    return AgentSpec(role_id, name, family, "1.0.0", caps, inputs, outputs, authority,
                     evidence, ("output_schema_valid", "provenance_preserved"), aliases)


def default_registry() -> AgentRegistry:
    """Roles are registered here; live model connectivity is not implied."""
    specs = [
        # VX Research Intelligence
        _spec("VX-RES-COORD", "Research Team Coordinator", "research", ("research", "decomposition", "routing"), ("goal",), ("research_plan",), "planning"),
        _spec("VX-RES-SOURCE", "Source Quality Analyst", "research", ("source_quality", "citations", "provenance"), ("claims",), ("evidence_map",), "research"),
        _spec("VX-RES-LITERATURE", "Literature & Patent Scout", "research", ("literature_review", "patent_discovery"), ("question",), ("literature_map",), "research"),
        _spec("VX-RES-REPO", "Repository Archaeologist", "research", ("repository_analysis", "code_search", "lineage"), ("repository_refs",), ("repository_findings",), "read-only"),
        _spec("VX-RES-REPRO", "Reproducibility Analyst", "research", ("reproduction", "benchmarking"), ("hypothesis", "method"), ("reproduction_plan",), "analysis"),
        _spec("VX-RES-CONTRA", "Contradiction & Claim Auditor", "research", ("contradiction_detection", "claim_audit"), ("claims", "evidence"), ("conflict_report",), "analysis"),
        _spec("VX-RES-SYNTH", "Evidence Synthesis Agent", "research", ("synthesis", "uncertainty"), ("evidence_records",), ("synthesis_report",), "analysis"),
        # VX Financial Intelligence: analytical authority only
        _spec("VX-FIN-COORD", "Financial Intelligence Coordinator", "finance", ("financial_analysis", "budgeting", "routing"), ("business_goal",), ("financial_workplan",), "analysis"),
        _spec("VX-FIN-MARKET", "Market & Opportunity Analyst", "finance", ("market_sizing", "competitive_research"), ("product_concept",), ("market_model",), "research"),
        _spec("VX-FIN-UNIT", "Unit Economics Analyst", "finance", ("unit_economics", "scenario_analysis"), ("costs", "revenue_assumptions"), ("unit_economics_model",), "analysis"),
        _spec("VX-FIN-COST", "Compute & Engineering Cost Analyst", "finance", ("compute_budget", "cost_model"), ("architecture", "resource_limits"), ("cost_scenarios",), "analysis"),
        _spec("VX-FIN-PRICE", "Pricing & Value Analyst", "finance", ("pricing", "value_capture"), ("market_model", "unit_economics_model"), ("pricing_proposal",), "proposal"),
        _spec("VX-FIN-RISK", "Financial Risk Analyst", "finance", ("risk_analysis", "sensitivity"), ("financial_model",), ("risk_report",), "analysis"),
        _spec("VX-FIN-COMP", "Financial Compliance Screener", "finance", ("compliance_screening", "regulatory_questions"), ("business_model", "jurisdiction"), ("compliance_questions",), "analysis"),
        _spec("VX-FIN-PORT", "Portfolio Prioritization Agent", "finance", ("portfolio_prioritization", "capital_allocation_scenarios"), ("candidate_projects",), ("prioritization_proposal",), "proposal"),
        # VX Engineering Intelligence
        _spec("VX-ENG-COORD", "Engineering Workflow Coordinator", "engineering", ("engineering_orchestration", "task_graph"), ("goal",), ("engineering_plan",), "planning"),
        _spec("VX-ENG-REQ", "Requirements & Constraint Engineer", "engineering", ("requirements", "acceptance_criteria"), ("goal", "research"), ("requirements_spec",), "analysis"),
        _spec("VX-ENG-ARCH", "Systems Architecture Engineer", "engineering", ("architecture", "interface_contracts", "impact_analysis"), ("requirements_spec",), ("architecture_candidate",), "proposal"),
        _spec("VX-ENG-INNOV", "Innovation & Design-Space Agent", "engineering", ("innovation", "novelty_search", "alternatives"), ("research", "architecture_candidate"), ("innovation_candidates",), "proposal"),
        _spec("VX-ENG-BUILD", "Implementation Planner/Builder", "engineering", ("implementation", "code_generation", "patch_planning"), ("architecture_candidate", "contracts"), ("implementation_artifacts",), "sandbox-write"),
        _spec("VX-ENG-TEST", "Test & Reproducibility Engineer", "engineering", ("testing", "regression", "benchmarks"), ("implementation_artifacts",), ("test_report",), "sandbox"),
        _spec("VX-ENG-RED", "Adversarial & Security Engineer", "engineering", ("red_team", "threat_model", "negative_testing"), ("architecture_candidate", "implementation_artifacts"), ("adversarial_report",), "analysis"),
        _spec("VX-ENG-PROOF", "Proof & Assurance Engineer", "engineering", ("proof_package", "invariant_checks", "evidence"), ("test_report", "adversarial_report"), ("proof_package",), "verification"),
        _spec("VX-ENG-OPS", "Operations & Recovery Engineer", "engineering", ("observability", "recovery", "replay"), ("workflow_events",), ("recovery_plan",), "sandbox"),
        _spec("VX-ENG-LEARN", "Engineering Knowledge/Failure Learner", "engineering", ("failure_learning", "lineage", "knowledge_capture"), ("test_report", "recovery_plan"), ("lessons_record",), "analysis"),
        _spec("VX-PARENT-COORD", "Ω Parent Engineering Coordinator", "governance", ("multi_mind_coordination", "decision_synthesis"), ("all_reports",), ("engineering_decision",), "decision-proposal"),
    ]
    registry = AgentRegistry()
    registry.add_many(specs)
    minds = (
        MindSpec("MIND-SYS-ARCH", "Independent systems architecture review", "UNBOUND", "unconfigured", ("VX-ENG-ARCH", "VX-ENG-COORD")),
        MindSpec("MIND-RESEARCH", "Evidence quality and uncertainty review", "UNBOUND", "unconfigured", ("VX-RES-SOURCE", "VX-RES-CONTRA", "VX-RES-SYNTH")),
        MindSpec("MIND-FINANCE", "Economic viability and downside scenarios", "UNBOUND", "unconfigured", ("VX-FIN-UNIT", "VX-FIN-COST", "VX-FIN-RISK")),
        MindSpec("MIND-SECURITY", "Independent threat and failure review", "UNBOUND", "unconfigured", ("VX-ENG-RED", "VX-ENG-TEST")),
        MindSpec("MIND-PROOF", "Proof obligations and reproducibility", "UNBOUND", "unconfigured", ("VX-ENG-PROOF", "VX-RES-REPRO")),
    )
    for mind in minds:
        registry.register_mind(mind)
    return registry
