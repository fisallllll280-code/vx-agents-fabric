"""Opt-in environment binding for roles, exact role versions and parent minds."""
from __future__ import annotations
from dataclasses import dataclass
import os
import re
from typing import Mapping
from ..registry import AgentRegistry, default_registry
from ..vlns_activation import (
    VLNSActivationGate,
    VLNSGateConfig,
    VLNSGuardedAgentAdapter,
    VLNSGuardedMindAdapter,
)
from .openai_compatible import OpenAICompatibleProvider


def _fragment(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()


@dataclass(frozen=True)
class ProviderBindings:
    enabled: bool
    base_url: str | None
    agent_adapters: Mapping[str, object]
    mind_adapters: Mapping[str, object]
    agent_models: Mapping[str, str]
    mind_models: Mapping[str, str]
    unconfigured_agent_versions: tuple[str, ...]
    unconfigured_minds: tuple[str, ...]
    vlns_activation_required: bool = False
    vlns_gate_configured: bool = False


def build_from_env(registry: AgentRegistry | None = None,
                   environ: Mapping[str, str] | None = None) -> ProviderBindings:
    registry = registry or default_registry()
    env = environ if environ is not None else os.environ
    base_url = env.get("VX_OPENAI_COMPAT_BASE_URL", "").strip()
    vlns_required = env.get("VX_VLNS_ACTIVATION_REQUIRED", "false").strip().lower() in {"1", "true", "yes"}
    gate_config = VLNSGateConfig.from_env(env) if vlns_required else None
    gate = VLNSActivationGate(gate_config) if gate_config is not None else None
    gate_configured = bool(
        gate_config
        and gate_config.base_url
        and len(gate_config.signing_key) >= 32
        and gate_config.provider in gate_config.allowed_providers
    )
    if not base_url:
        return ProviderBindings(
            False, None, {}, {}, {}, {},
            tuple(spec.key for spec in registry.all_agents()), tuple(sorted(registry.minds)),
            vlns_required, gate_configured,
        )
    api_key = env.get("VX_OPENAI_COMPAT_API_KEY") or None
    try:
        timeout = float(env.get("VX_PROVIDER_TIMEOUT_SECONDS", "45"))
    except ValueError as exc:
        raise ValueError("VX_PROVIDER_TIMEOUT_SECONDS_must_be_numeric") from exc
    family_vars = {
        "research": "VX_RESEARCH_MODEL",
        "finance": "VX_FINANCE_MODEL",
        "engineering": "VX_ENGINEERING_MODEL",
        "governance": "VX_GOVERNANCE_MODEL",
    }
    agents: dict[str, object] = {}
    agent_models: dict[str, str] = {}
    missing_agents: list[str] = []
    for spec in registry.all_agents():
        exact = env.get("VX_AGENT_MODEL_" + _fragment(spec.key), "").strip()
        role = env.get("VX_AGENT_MODEL_" + _fragment(spec.role_id), "").strip()
        family = env.get(family_vars.get(spec.family, ""), "").strip()
        model = exact or role or family
        if not model:
            missing_agents.append(spec.key)
            continue
        provider = OpenAICompatibleProvider(base_url, model, api_key, timeout)
        adapter = provider.agent_adapter
        if gate is not None:
            version = (
                env.get("VX_VLNS_MODEL_VERSION_" + _fragment(spec.key), "").strip()
                or env.get("VX_VLNS_MODEL_VERSION", "").strip()
                or model
            )
            adapter = VLNSGuardedAgentAdapter(adapter, gate, model, version)
        agents[spec.key] = adapter
        agent_models[spec.key] = model

    minds: dict[str, object] = {}
    mind_models: dict[str, str] = {}
    missing_minds: list[str] = []
    for mind_id, mind in sorted(registry.minds.items()):
        model = env.get("VX_MIND_MODEL_" + _fragment(mind_id), "").strip()
        if not model:
            missing_minds.append(mind_id)
            continue
        provider = OpenAICompatibleProvider(base_url, model, api_key, timeout)
        adapter = provider.mind_adapter(mind_id, mind.purpose)
        if gate is not None:
            version = (
                env.get("VX_VLNS_MODEL_VERSION_" + _fragment(mind_id), "").strip()
                or env.get("VX_VLNS_MODEL_VERSION", "").strip()
                or model
            )
            adapter = VLNSGuardedMindAdapter(adapter, gate, mind_id, model, version)
        minds[mind_id] = adapter
        mind_models[mind_id] = model
    return ProviderBindings(
        True, base_url, agents, minds, agent_models, mind_models,
        tuple(missing_agents), tuple(missing_minds), vlns_required, gate_configured,
    )
