"""Local, read-only adapter for routing system-language requests through VX."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .system_language_fabric import (
    LanguageInputError,
    RegistryError,
    SystemLanguageFabric,
    plan_innovation,
    plan_translation,
)


def build_orchestrator_adapter(registry_path: str | Path):
    """Build an opt-in adapter. Submitted source is analyzed, never executed or archived."""
    def adapter(envelope: Any) -> Mapping[str, Any]:
        payload = getattr(envelope, "payload", {})
        context = payload.get("context", {}) if isinstance(payload, Mapping) else {}
        engineering = context.get("engineering", {}) if isinstance(context, Mapping) else {}
        request = engineering.get("system_language_request") if isinstance(engineering, Mapping) else None
        task_id = str(getattr(envelope, "task_id", "VX-LANG-TASK"))
        if not isinstance(request, Mapping):
            result = {"status": "HOLD", "error_code": "language_request_missing"}
        else:
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
        return {
            "artifact_id": task_id + ":language-fabric",
            "kind": "language_fabric_report",
            "status": str(result.get("status", "HOLD")),
            "content": {
                "operation": str(request.get("operation", "UNKNOWN")).upper() if isinstance(request, Mapping) else "UNKNOWN",
                "result": result,
                "source_text_persisted": False,
                "adapter_mode": "LOCAL_READ_ONLY"
            },
            "evidence_refs": [],
            "limitations": ["Syntax pass is not semantic or runtime proof.",
                            "Missing parser/compiler/proof adapters must remain HOLD."]
        }
    return adapter
