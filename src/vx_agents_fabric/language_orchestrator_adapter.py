"""Local, read-only adapter for routing language and symbol work through VX."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import time
from typing import Any

from .omega_symbol_fabric import SymbolDataError, parse_emoji_test
from .system_language_fabric import (
    LanguageInputError,
    RegistryError,
    SystemLanguageFabric,
    plan_innovation,
    plan_translation,
)


def _symbol_status(profile_path: Path | None, data_path: Path | None) -> dict[str, Any]:
    if profile_path is None or not profile_path.is_file():
        return {"status": "HOLD_PROFILE_NOT_CONFIGURED"}
    try:
        import json
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "HOLD_PROFILE_INVALID"}
    unicode_profile = profile.get("unicode", {})
    expected_hash = unicode_profile.get("expected_sha256")
    return {
        "status": "DECLARED_ONLY",
        "artifact_id": profile.get("artifact_id"),
        "unicode_version": unicode_profile.get("emoji_version"),
        "data_file_configured": data_path is not None and data_path.is_file(),
        "source_hash_state": "PINNED" if isinstance(expected_hash, str) and len(expected_hash) == 64 else "NOT_PINNED",
        "nxl_languages": [
            {"language_id": item.get("language_id"), "status": item.get("status"),
             "grammar_state": item.get("grammar_state"), "semantic_state": item.get("semantic_state"),
             "compiler_state": item.get("compiler_state")}
            for item in profile.get("target_languages", [])
        ],
        "execution_state": "NOT_EXECUTED",
        "canonical_mutation_allowed": False,
    }


def _import_symbol_data(
    request: Mapping[str, Any],
    profile_path: Path | None,
    data_path: Path | None,
) -> dict[str, Any]:
    if profile_path is None or not profile_path.is_file():
        return {"status": "HOLD_PROFILE_NOT_CONFIGURED"}
    if data_path is None or not data_path.is_file():
        return {"status": "HOLD_DATA_NOT_MOUNTED", "execution_state": "NOT_EXECUTED"}
    try:
        import json
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "HOLD_PROFILE_INVALID"}

    unicode_profile = profile.get("unicode", {})
    version = unicode_profile.get("emoji_version")
    requested_version = request.get("version", version)
    if requested_version != version:
        return {"status": "HOLD_VERSION_MISMATCH", "expected_version": version,
                "requested_version": requested_version}
    expected_hash = unicode_profile.get("expected_sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        return {"status": "HOLD_SOURCE_HASH_NOT_PINNED",
                "unicode_version": version, "execution_state": "NOT_EXECUTED"}
    requested_targets = request.get("target_languages", [])
    if not isinstance(requested_targets, list) or any(not isinstance(item, str) for item in requested_targets):
        return {"status": "HOLD_TARGET_LANGUAGE_LIST_INVALID"}
    allowed_targets = {item.get("language_id") for item in profile.get("target_languages", [])}
    unknown_targets = sorted(set(requested_targets) - allowed_targets)
    if unknown_targets:
        return {"status": "HOLD_TARGET_LANGUAGE_UNKNOWN", "unknown_targets": unknown_targets}

    try:
        source = data_path.read_bytes()
    except OSError as exc:
        return {"status": "HOLD_DATA_READ_FAILED", "error_code": type(exc).__name__}
    started = time.perf_counter_ns()
    try:
        result = parse_emoji_test(source, expected_version=version, expected_sha256=expected_hash)
    except SymbolDataError as exc:
        return {"status": "HOLD_SYMBOL_DATA_INVALID", "error_code": str(exc),
                "source_sha256": __import__("hashlib").sha256(source).hexdigest(),
                "execution_state": "NOT_EXECUTED"}
    elapsed_ns = max(1, time.perf_counter_ns() - started)
    result["performance"] = {
        "read_and_parse_elapsed_ns": elapsed_ns,
        "throughput_bytes_per_second": round(len(source) * 1_000_000_000 / elapsed_ns, 2),
        "throughput_records_per_second": round(result["record_count"] * 1_000_000_000 / elapsed_ns, 2),
        "baseline_comparison": "NOT_AVAILABLE",
        "target_speedup_claim": "NOT_VERIFIED",
    }
    result["nxl_target_bindings"] = [
        {
            "language_id": language_id,
            "status": "HOLD_GRAMMAR_SEMANTICS_COMPILER_NOT_FORMALIZED",
            "generated_source": None,
            "execution_performed": False,
        }
        for language_id in requested_targets
    ]
    result["canonical_mutation_allowed"] = False
    return result


def build_orchestrator_adapter(
    registry_path: str | Path,
    *,
    symbol_profile_path: str | Path | None = None,
    symbol_data_path: str | Path | None = None,
):
    """Build an opt-in local adapter. Source is analyzed, never executed or archived."""
    registry_path = Path(registry_path)
    profile_path = Path(symbol_profile_path) if symbol_profile_path is not None else None
    data_path = Path(symbol_data_path) if symbol_data_path is not None else None

    def adapter(envelope: Any) -> Mapping[str, Any]:
        payload = getattr(envelope, "payload", {})
        context = payload.get("context", {}) if isinstance(payload, Mapping) else {}
        engineering = context.get("engineering", {}) if isinstance(context, Mapping) else {}
        language_request = engineering.get("system_language_request") if isinstance(engineering, Mapping) else None
        symbol_request = engineering.get("omega_symbol_request") if isinstance(engineering, Mapping) else None
        task_id = str(getattr(envelope, "task_id", "VX-LANG-TASK"))

        if isinstance(language_request, Mapping) and isinstance(symbol_request, Mapping):
            result = {"status": "HOLD", "error_code": "multiple_language_requests_in_one_task"}
            request = None
            kind = "language_fabric_report"
        elif isinstance(symbol_request, Mapping):
            request = symbol_request
            operation = str(request.get("operation", "")).upper()
            kind = "omega_symbol_report"
            if operation == "STATUS":
                result = _symbol_status(profile_path, data_path)
            elif operation == "IMPORT":
                result = _import_symbol_data(request, profile_path, data_path)
            else:
                result = {"status": "HOLD", "error_code": "omega_symbol_operation_unsupported"}
        elif isinstance(language_request, Mapping):
            request = language_request
            kind = "language_fabric_report"
            try:
                fabric = SystemLanguageFabric.from_file(registry_path)
                operation = str(request.get("operation", "")).upper()
                language_id = str(request.get("language_id", ""))
                if operation == "LIST":
                    result = {"schema_version": "1.0.0", "status": "DECLARED_ONLY", "languages": fabric.languages()}
                elif operation == "ANALYZE":
                    result = fabric.analyze(language_id, request.get("source_text"), request.get("version"))
                elif operation == "TRANSLATE":
                    result = plan_translation(
                        fabric, str(request.get("source_language", "")),
                        str(request.get("target_language", "")), request.get("source_text"),
                        request.get("source_version"), request.get("target_version")
                    )
                elif operation == "INNOVATE":
                    result = plan_innovation(fabric, language_id, request.get("goal"), request.get("version"))
                else:
                    result = {"status": "HOLD", "error_code": "language_operation_unsupported"}
            except (OSError, RegistryError, LanguageInputError, KeyError) as exc:
                result = {"status": "HOLD", "error_code": str(exc)[:160]}
        else:
            request = None
            kind = "language_fabric_report"
            result = {"status": "HOLD", "error_code": "language_request_missing"}

        operation_name = str(request.get("operation", "UNKNOWN")).upper() if isinstance(request, Mapping) else "UNKNOWN"
        evidence_refs = []
        source_hash = result.get("source_sha256")
        if isinstance(source_hash, str):
            evidence_refs.append("unicode:emoji:" + str(result.get("expected_version", "unknown")) + ":sha256:" + source_hash)
        return {
            "artifact_id": task_id + (":omega-symbol" if kind == "omega_symbol_report" else ":language-fabric"),
            "kind": kind,
            "status": str(result.get("status", "HOLD")),
            "content": {
                "operation": operation_name,
                "result": result,
                "submitted_source_persisted": False,
                "adapter_mode": "LOCAL_READ_ONLY",
            },
            "evidence_refs": evidence_refs,
            "limitations": [
                "A parser result does not verify Unicode source origin, symbol meaning, rendering coverage, or NXL compilation.",
                "Missing corpus hash, grammar, compiler, or proof adapter remains HOLD.",
            ],
        }
    return adapter
