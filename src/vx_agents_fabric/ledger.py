"""Append-only hash-chained workflow ledger with optional fsync-backed JSONL persistence."""
from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any

from .contracts import WorkflowEvent, canonical_json, content_hash


class IntegrityLedger:
    """Stores complete event payloads; configured paths survive process restarts.

    Without a path this is an in-memory development ledger. With a path, appends
    are flushed and fsync'd before acknowledgement.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path).expanduser() if path else None
        self._events: list[WorkflowEvent] = []
        self._lock = RLock()
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                self._load()

    def _load(self) -> None:
        assert self.path is not None
        loaded: list[WorkflowEvent] = []
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    raw = json.loads(line)
                    raw["payload"] = raw.get("payload", {})
                    loaded.append(WorkflowEvent(**raw))
        except (OSError, json.JSONDecodeError, TypeError, KeyError) as exc:
            raise ValueError("ledger_load_failed:" + type(exc).__name__) from exc
        self._events = loaded
        if not self.verify():
            raise ValueError("ledger_integrity_failed_on_load")

    def append(self, workflow_id: str, event_type: str, subject_id: str, payload: Any) -> WorkflowEvent:
        payload_snapshot = json.loads(canonical_json(payload))
        if not isinstance(payload_snapshot, dict):
            payload_snapshot = {"value": payload_snapshot}
        with self._lock:
            previous = self._events[-1].event_hash if self._events else "GENESIS"
            payload_digest = content_hash(payload_snapshot)
            material = {
                "sequence": len(self._events) + 1,
                "workflow_id": workflow_id,
                "event_type": event_type,
                "subject_id": subject_id,
                "payload_hash": payload_digest,
                "previous_hash": previous,
            }
            event = WorkflowEvent(
                sequence=material["sequence"],
                workflow_id=workflow_id,
                event_type=event_type,
                subject_id=subject_id,
                payload_hash=payload_digest,
                previous_hash=previous,
                event_hash=content_hash(material),
                payload=payload_snapshot,
            )
            if self.path:
                try:
                    with self.path.open("a", encoding="utf-8") as stream:
                        stream.write(canonical_json(asdict(event)) + "\n")
                        stream.flush()
                        os.fsync(stream.fileno())
                except OSError as exc:
                    raise OSError("ledger_durable_append_failed") from exc
            self._events.append(event)
            return event

    def events(self, workflow_id: str | None = None) -> tuple[WorkflowEvent, ...]:
        with self._lock:
            if workflow_id is None:
                return tuple(self._events)
            return tuple(event for event in self._events if event.workflow_id == workflow_id)

    def replay(self, workflow_id: str) -> tuple[WorkflowEvent, ...]:
        if not self.verify():
            raise ValueError("ledger_integrity_failed")
        return self.events(workflow_id)

    @property
    def head(self) -> str:
        with self._lock:
            return self._events[-1].event_hash if self._events else "GENESIS"

    def verify(self) -> bool:
        previous = "GENESIS"
        for index, event in enumerate(self._events, start=1):
            if content_hash(event.payload) != event.payload_hash:
                return False
            material = {
                "sequence": index,
                "workflow_id": event.workflow_id,
                "event_type": event.event_type,
                "subject_id": event.subject_id,
                "payload_hash": event.payload_hash,
                "previous_hash": previous,
            }
            if event.sequence != index or event.previous_hash != previous:
                return False
            if event.event_hash != content_hash(material):
                return False
            previous = event.event_hash
        return True
