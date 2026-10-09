"""Append-only failure memory for safe retry hints and cross-run operational learning."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
from threading import RLock
from typing import Any, Mapping
from .contracts import AgentRunResult, canonical_json, content_hash


def _redact(message: str) -> str:
    value = re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", message)
    value = re.sub(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*\S+", r"\1=[REDACTED]", value)
    return value[:400]


class FailureMemory:
    """Stores compact failure patterns, not prompts or complete artifact contents."""
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path).expanduser() if path else None
        self._records: list[dict[str, Any]] = []
        self._seen_task_ids: set[str] = set()
        self._lock = RLock()
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                self._load()

    @staticmethod
    def _material(record: Mapping[str, Any]) -> dict[str, Any]:
        keys = ("sequence", "workflow_id", "task_id", "agent_id", "agent_version",
                "stage", "status", "error_code", "message", "lesson", "previous_hash")
        return {key: record[key] for key in keys}

    def _load(self) -> None:
        assert self.path is not None
        previous = "GENESIS"
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    if record.get("sequence") != len(self._records) + 1:
                        raise ValueError("failure_memory_sequence_invalid")
                    if record.get("previous_hash") != previous:
                        raise ValueError("failure_memory_chain_invalid")
                    if record.get("record_hash") != content_hash(self._material(record)):
                        raise ValueError("failure_memory_record_hash_invalid")
                    self._records.append(record)
                    self._seen_task_ids.add(str(record["task_id"]))
                    previous = str(record["record_hash"])
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError("failure_memory_load_failed:" + type(exc).__name__) from exc

    def observe(self, workflow_id: str, result: AgentRunResult) -> dict[str, Any] | None:
        if result.status not in {"FAIL", "BLOCKED"}:
            return None
        with self._lock:
            if result.task_id in self._seen_task_ids:
                return next(item for item in self._records if item["task_id"] == result.task_id)
            previous = self._records[-1]["record_hash"] if self._records else "GENESIS"
            record: dict[str, Any] = {
                "sequence": len(self._records) + 1, "workflow_id": workflow_id,
                "task_id": result.task_id, "agent_id": result.agent_id,
                "agent_version": result.agent_version, "stage": result.stage,
                "status": result.status, "error_code": result.error_code or "UNCLASSIFIED_FAILURE",
                "message": _redact(result.message),
                "lesson": "Keep the failed task quarantined; inspect the recorded cause and evidence, correct the root cause, then replay regression tests before retrying.",
                "previous_hash": previous,
            }
            record["record_hash"] = content_hash(self._material(record))
            if self.path:
                try:
                    with self.path.open("a", encoding="utf-8") as stream:
                        stream.write(canonical_json(record) + "\n")
                        stream.flush()
                        os.fsync(stream.fileno())
                except OSError as exc:
                    raise OSError("failure_memory_durable_write_failed") from exc
            self._records.append(record)
            self._seen_task_ids.add(result.task_id)
            return dict(record)

    def lookup(self, agent_id: str, stage: str, limit: int = 5) -> tuple[dict[str, Any], ...]:
        if limit <= 0:
            return ()
        with self._lock:
            matched = [record for record in self._records
                       if record["agent_id"] == agent_id and record["stage"] == stage]
            fields = ("workflow_id", "agent_id", "agent_version", "stage", "status",
                      "error_code", "message", "lesson", "record_hash")
            return tuple({key: item[key] for key in fields} for item in matched[-limit:])

    def verify(self) -> bool:
        previous = "GENESIS"
        for index, record in enumerate(self._records, start=1):
            if record.get("sequence") != index or record.get("previous_hash") != previous:
                return False
            if record.get("record_hash") != content_hash(self._material(record)):
                return False
            previous = str(record["record_hash"])
        return True

    def records(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(dict(item) for item in self._records)
