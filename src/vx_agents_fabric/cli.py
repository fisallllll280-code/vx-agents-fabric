"""Command-line runner for the VX Agents Fabric."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Mapping, Sequence

from .orchestrator import EngineeringOrchestrator
from .providers import build_from_env
from .registry import AgentRegistry, default_registry


def _env_fragment(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()


def version_pins_from_env(registry: AgentRegistry,
                          environ: Mapping[str, str] | None = None) -> dict[str, str]:
    env = environ if environ is not None else os.environ
    pins: dict[str, str] = {}
    for spec in registry.all_agents():
        key = "VX_AGENT_VERSION_PIN_" + _env_fragment(spec.role_id)
        requested = env.get(key, "").strip()
        if requested:
            previous = pins.get(spec.role_id)
            if previous and previous != requested:
                raise ValueError("conflicting_agent_version_pins:" + spec.role_id)
            pins[spec.role_id] = requested
    # Fail early on an unknown version rather than silently routing elsewhere.
    for role_id, version in pins.items():
        registry.resolve(role_id, version)
    return pins


def report_payload(report: Any, orchestrator: EngineeringOrchestrator,
                   provider_bindings: Any) -> dict[str, Any]:
    return {
        "report": report.summary(),
        "results": [asdict(item) for item in report.results],
        "artifacts": [asdict(item) for item in report.artifacts],
        "parent_mind_reviews": [asdict(item) for item in report.mind_reviews],
        "provider_bindings": {
            "endpoint_configured": provider_bindings.enabled,
            "configured_agent_versions": sorted(provider_bindings.agent_adapters),
            "unconfigured_agent_versions": list(provider_bindings.unconfigured_agent_versions),
            "configured_parent_minds": sorted(provider_bindings.mind_adapters),
            "unconfigured_parent_minds": list(provider_bindings.unconfigured_minds),
            "model_ids": dict(provider_bindings.agent_models),
            "parent_mind_model_ids": dict(provider_bindings.mind_models),
        },
        "integrity": {
            "ledger_valid": orchestrator.ledger.verify(),
            "workflow_event_count": len(orchestrator.ledger.events(report.workflow_id)),
            "ledger_head": orchestrator.ledger.head,
            "archived_artifact_count": len(orchestrator.artifact_archive.replay(report.workflow_id)),
            "failure_memory_count": len(orchestrator.failure_memory.records()),
        },
        "safety_boundary": {
            "production_authorized": False,
            "canonical_mutation_performed": False,
            "financial_transactions_performed": False,
        },
    }


def _read_context(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("context_file_unreadable_or_invalid_json:" + type(exc).__name__) from exc
    if not isinstance(data, dict):
        raise ValueError("context_file_root_must_be_json_object")
    return data


def _write_atomically(path: str, content: str) -> None:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=str(target.parent),
            prefix=target.name + ".", suffix=".tmp", delete=False
        ) as stream:
            temp_name = stream.name
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
        temp_name = None
        try:
            directory_fd = os.open(str(target.parent), os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            # File contents are already fsync'd; directory fsync is platform-dependent.
            pass
    finally:
        if temp_name:
            try:
                os.unlink(temp_name)
            except OSError:
                pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vx-agents-fabric",
        description="Run the VAIXLNS/VX research, financial-analysis and engineering workflow."
    )
    goals = parser.add_mutually_exclusive_group(required=True)
    goals.add_argument("--goal", help="Engineering objective")
    goals.add_argument("--goal-file", help="UTF-8 text file containing the engineering objective")
    parser.add_argument("--workflow-id", default=None, help="Stable workflow identifier for replay")
    parser.add_argument("--context-file", help="JSON object with separately scoped shared/research/finance/engineering/governance keys")
    parser.add_argument("--output", help="Write the complete JSON report atomically to this file instead of stdout")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        goal = args.goal if args.goal is not None else Path(args.goal_file).read_text(encoding="utf-8").strip()
        if not goal.strip():
            raise ValueError("goal_required")
        context = _read_context(args.context_file)
        registry = default_registry()
        bindings = build_from_env(registry)
        pins = version_pins_from_env(registry)
        workflow_id = args.workflow_id or "WF-" + __import__("hashlib").sha256(
            (goal + "\0" + str(context)).encode("utf-8")
        ).hexdigest()[:16].upper()
        orchestrator = EngineeringOrchestrator(
            registry=registry,
            adapters=bindings.agent_adapters,
            mind_adapters=bindings.mind_adapters,
            version_pins=pins,
        )
        report = orchestrator.run(goal, workflow_id=workflow_id, context=context)
        document = report_payload(report, orchestrator, bindings)
        rendered = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n"
        if args.output:
            _write_atomically(args.output, rendered)
        else:
            sys.stdout.write(rendered)
        if report.status == "CANDIDATE_READY_FOR_GOVERNANCE":
            return 0
        if report.status == "REJECT":
            return 3
        return 2  # HOLD or incomplete proof/adapters is not a successful engineering release.
    except (OSError, ValueError) as exc:
        sys.stderr.write("vx_agents_fabric_cli_error:" + str(exc) + "\n")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
