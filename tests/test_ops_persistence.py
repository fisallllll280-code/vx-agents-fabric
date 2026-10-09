import tempfile
import unittest
from pathlib import Path

from vx_agents_fabric.artifact_archive import ArtifactArchive
from vx_agents_fabric.contracts import AgentRunResult, Artifact
from vx_agents_fabric.failure_memory import FailureMemory
from vx_agents_fabric.ledger import IntegrityLedger


class DurableLedgerTests(unittest.TestCase):
    def test_event_payload_survives_restart_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            ledger = IntegrityLedger(path)
            ledger.append("WF-1", "FAILED", "VX-ENG-TEST", {
                "error_code": "TEST_FAILURE", "details": {"assertion": "expected X"}
            })
            self.assertTrue(ledger.verify())
            reopened = IntegrityLedger(path)
            self.assertTrue(reopened.verify())
            events = reopened.replay("WF-1")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].payload["error_code"], "TEST_FAILURE")
            self.assertEqual(events[0].payload["details"]["assertion"], "expected X")

    def test_tampered_event_payload_is_detected_on_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            ledger = IntegrityLedger(path)
            ledger.append("WF-1", "RESULT", "A", {"status": "PASS"})
            path.write_text(path.read_text(encoding="utf-8").replace('"PASS"', '"FAIL"'), encoding="utf-8")
            with self.assertRaises(ValueError):
                IntegrityLedger(path)


class ArtifactArchiveTests(unittest.TestCase):
    def test_full_artifact_is_durable_and_identity_is_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifacts.jsonl"
            artifact = Artifact(
                artifact_id="WF-1:research:artifact", kind="research_report", status="PROPOSED",
                content={"finding": "preserved", "assumptions": ["A"]},
                source_agent="VX-RES-SOURCE", source_version="1.0.0",
                input_artifact_ids=(), evidence_refs=("https://example.test/source",),
                limitations=("not independently verified",),
            ).with_digest()
            ArtifactArchive(path).store("WF-1", artifact)
            reopened = ArtifactArchive(path)
            replayed = reopened.replay("WF-1")
            self.assertEqual(len(replayed), 1)
            self.assertEqual(replayed[0].content["finding"], "preserved")
            self.assertEqual(replayed[0].sha256, artifact.sha256)
            conflicting = Artifact(
                artifact_id=artifact.artifact_id, kind=artifact.kind, status=artifact.status,
                content={"finding": "silently changed"}, source_agent=artifact.source_agent,
                source_version=artifact.source_version,
            ).with_digest()
            with self.assertRaises(ValueError):
                reopened.store("WF-1", conflicting)


class FailureMemoryTests(unittest.TestCase):
    def test_failure_pattern_is_durable_and_retrievable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "failures.jsonl"
            memory = FailureMemory(path)
            result = AgentRunResult(
                task_id="WF-1:RESEARCH:VX-RES-SOURCE@1.0.0",
                agent_id="VX-RES-SOURCE", agent_version="1.0.0", stage="RESEARCH",
                status="FAIL", artifact_id=None, error_code="SOURCE_FETCH_FAILED",
                message="ConnectionError: temporary failure",
            )
            memory.observe("WF-1", result)
            reopened = FailureMemory(path)
            self.assertTrue(reopened.verify())
            lessons = reopened.lookup("VX-RES-SOURCE", "RESEARCH")
            self.assertEqual(len(lessons), 1)
            self.assertEqual(lessons[0]["error_code"], "SOURCE_FETCH_FAILED")
            self.assertIn("root cause", lessons[0]["lesson"])
            self.assertEqual(lessons[0]["record_hash"], memory.records()[0]["record_hash"])

    def test_failure_memory_redacts_bearer_tokens(self):
        memory = FailureMemory()
        result = AgentRunResult("task", "AG", "1.0.0", "TEST", "FAIL", None,
                                "ERR", "Authorization: Bearer secret-value")
        memory.observe("WF-1", result)
        self.assertNotIn("secret-value", memory.records()[0]["message"])


if __name__ == "__main__":
    unittest.main()
