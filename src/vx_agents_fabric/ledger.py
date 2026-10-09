"""Append-only in-memory event chain; replace with durable VAIXLNS storage in deployment."""
from __future__ import annotations
from typing import Any
from .contracts import WorkflowEvent, content_hash


class IntegrityLedger:
    def __init__(self) -> None:
        self._events: list[WorkflowEvent] = []

    def append(self, workflow_id: str, event_type: str, subject_id: str, payload: Any) -> WorkflowEvent:
        previous = self._events[-1].event_hash if self._events else "GENESIS"
        payload_digest = content_hash(payload)
        material = {
            "sequence": len(self._events) + 1, "workflow_id": workflow_id,
            "event_type": event_type, "subject_id": subject_id,
            "payload_hash": payload_digest, "previous_hash": previous,
        }
        event = WorkflowEvent(
            sequence=material["sequence"], workflow_id=workflow_id, event_type=event_type,
            subject_id=subject_id, payload_hash=payload_digest, previous_hash=previous,
            event_hash=content_hash(material),
        )
        self._events.append(event)
        return event

    def events(self) -> tuple[WorkflowEvent, ...]:
        return tuple(self._events)

    @property
    def head(self) -> str:
        return self._events[-1].event_hash if self._events else "GENESIS"

    def verify(self) -> bool:
        previous = "GENESIS"
        for index, event in enumerate(self._events, start=1):
            material = {
                "sequence": index, "workflow_id": event.workflow_id, "event_type": event.event_type,
                "subject_id": event.subject_id, "payload_hash": event.payload_hash,
                "previous_hash": previous,
            }
            if event.sequence != index or event.previous_hash != previous:
                return False
            if event.event_hash != content_hash(material):
                return False
            previous = event.event_hash
        return True
