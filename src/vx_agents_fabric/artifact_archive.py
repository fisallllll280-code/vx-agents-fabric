"""Immutable artifact archive with content verification and optional JSONL durability."""
from __future__ import annotations
from dataclasses import asdict
import json
import os
from pathlib import Path
from threading import RLock
from .contracts import Artifact, canonical_json


def _from_json(raw: dict) -> Artifact:
    raw = dict(raw)
    raw["input_artifact_ids"] = tuple(raw.get("input_artifact_ids", ()))
    raw["evidence_refs"] = tuple(raw.get("evidence_refs", ()))
    raw["limitations"] = tuple(raw.get("limitations", ()))
    return Artifact(**raw)


class ArtifactArchive:
    """Preserves full artifact content; conflicting ID reuse is rejected."""
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path).expanduser() if path else None
        self._records: dict[str, tuple[str, Artifact]] = {}
        self._order: list[str] = []
        self._lock = RLock()
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                self._load()

    def _load(self) -> None:
        assert self.path is not None
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    envelope = json.loads(line)
                    workflow_id = str(envelope["workflow_id"])
                    artifact = _from_json(envelope["artifact"])
                    if not artifact.sha256 or artifact.sha256 != artifact.with_digest().sha256:
                        raise ValueError("artifact_digest_mismatch")
                    existing = self._records.get(artifact.artifact_id)
                    if existing:
                        if existing[0] != workflow_id or existing[1].sha256 != artifact.sha256:
                            raise ValueError("artifact_identity_conflict_in_archive")
                        continue
                    self._records[artifact.artifact_id] = (workflow_id, artifact)
                    self._order.append(artifact.artifact_id)
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError("artifact_archive_load_failed:" + type(exc).__name__) from exc

    def store(self, workflow_id: str, artifact: Artifact) -> Artifact:
        if not artifact.sha256 or artifact.with_digest().sha256 != artifact.sha256:
            raise ValueError("artifact_digest_missing_or_invalid")
        with self._lock:
            old = self._records.get(artifact.artifact_id)
            if old:
                if old[0] != workflow_id or old[1].sha256 != artifact.sha256:
                    raise ValueError("artifact_identity_conflict")
                return old[1]
            envelope = {"workflow_id": workflow_id, "artifact": asdict(artifact)}
            if self.path:
                try:
                    with self.path.open("a", encoding="utf-8") as stream:
                        stream.write(canonical_json(envelope) + "\n")
                        stream.flush()
                        os.fsync(stream.fileno())
                except OSError as exc:
                    raise OSError("artifact_archive_durable_write_failed") from exc
            self._records[artifact.artifact_id] = (workflow_id, artifact)
            self._order.append(artifact.artifact_id)
            return artifact

    def get(self, artifact_id: str) -> Artifact | None:
        with self._lock:
            record = self._records.get(artifact_id)
            return record[1] if record else None

    def replay(self, workflow_id: str) -> tuple[Artifact, ...]:
        return tuple(self._records[item][1] for item in self._order
                     if self._records[item][0] == workflow_id)

    def all(self) -> tuple[Artifact, ...]:
        with self._lock:
            return tuple(self._records[item][1] for item in self._order)
