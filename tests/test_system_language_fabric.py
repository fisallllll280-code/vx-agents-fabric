"""Tests for the non-executing VAIXLNS/VX system-language fabric."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from vx_agents_fabric.system_language_fabric import (
    LanguageInputError,
    RegistryError,
    SystemLanguageFabric,
    plan_innovation,
    plan_translation,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "system_language_registry.v1.json"


class SystemLanguageFabricTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.fabric = SystemLanguageFabric(self.document)

    def test_registry_loads_with_authority_boundaries(self) -> None:
        self.assertEqual(self.document["canonical_authority"], "VAIXLNS")
        self.assertEqual(self.document["orchestrator"], "VX")
        self.assertEqual(self.document["assurance_gate"], "ARC-X")
        self.assertGreaterEqual(len(self.fabric.languages()), 6)

    def test_unknown_canonical_grammar_is_not_invented(self) -> None:
        genome = self.fabric.resolve("vaixl.project-genome")
        self.assertIsNone(genome.parser_adapter)
        result = self.fabric.analyze("vaixl.project-genome", "anything")
        self.assertEqual(result["status"], "HOLD_ADAPTER_NOT_CONFIGURED")
        self.assertEqual(result["proof_level"], "NONE")

    def test_intent_json_parses_but_is_not_semantically_verified(self) -> None:
        result = self.fabric.analyze("vx.intent-json", '{"intent_id":"I-1","goal":"analyze"}')
        self.assertEqual(result["status"], "PARSE_PASS")
        self.assertEqual(result["proof_level"], "SYNTAX_ONLY")
        self.assertEqual(result["semantic_state"], "NOT_CONFIGURED")
        self.assertEqual(result["execution_state"], "NOT_EXECUTED")

    def test_required_root_keys_report_incomplete_structure(self) -> None:
        result = self.fabric.analyze("vx.intent-json", '{"goal":"missing intent id"}')
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["missing_required_root_keys"], ["intent_id"])

    def test_json_duplicate_keys_are_rejected(self) -> None:
        result = self.fabric.analyze("vx.intent-json", '{"intent_id":"A","intent_id":"B","goal":"x"}')
        self.assertEqual(result["status"], "PARSE_FAILED")
        self.assertEqual(result["error_code"], "json_duplicate_key")

    def test_nonstandard_json_nan_is_rejected(self) -> None:
        result = self.fabric.analyze("vx.intent-json", '{"intent_id":"A","goal":"x","value":NaN}')
        self.assertEqual(result["status"], "PARSE_FAILED")
        self.assertTrue(result["error_code"].startswith("json_nonstandard_numeric_constant"))

    def test_invalid_json_is_rejected(self) -> None:
        result = self.fabric.analyze("vx.intent-json", '{"intent_id":')
        self.assertEqual(result["status"], "PARSE_FAILED")
        self.assertEqual(result["error_code"], "json_syntax_error")

    def test_python_source_is_parsed_without_execution(self) -> None:
        result = self.fabric.analyze("vx.agent-contract-python", "raise RuntimeError('must not execute')")
        self.assertEqual(result["status"], "PARSE_PASS")
        self.assertEqual(result["parsed_summary"]["root_type"], "module")
        self.assertEqual(result["execution_state"], "NOT_EXECUTED")

    def test_python_syntax_error_is_rejected(self) -> None:
        result = self.fabric.analyze("vx.agent-contract-python", "def broken(:\n  pass")
        self.assertEqual(result["status"], "PARSE_FAILED")
        self.assertEqual(result["error_code"], "python_syntax_error")

    def test_math_expression_uses_an_allowlist_not_eval(self) -> None:
        result = self.fabric.analyze("omega.math-expression", "sqrt(9) + pi")
        self.assertEqual(result["status"], "PARSE_PASS")
        self.assertEqual(result["parsed_summary"]["evaluation"], "NOT_PERFORMED")
        blocked = self.fabric.analyze("omega.math-expression", "__import__('os').system('id')")
        self.assertEqual(blocked["status"], "PARSE_FAILED")
        self.assertEqual(blocked["error_code"], "math_operation_not_allowed")

    def test_translation_fails_closed_until_semantics_and_compiler_exist(self) -> None:
        result = plan_translation(
            self.fabric, "vx.intent-json", "vx.agent-contract-python",
            '{"intent_id":"I-2","goal":"translate"}',
        )
        self.assertEqual(result["status"], "HOLD_ADAPTER_NOT_CONFIGURED")
        self.assertIsNone(result["generated_source"])
        self.assertFalse(result["execution_performed"])
        self.assertFalse(result["canonical_mutation_allowed"])

    def test_translation_target_must_be_explicitly_allowlisted(self) -> None:
        result = plan_translation(
            self.fabric, "vx.integration-attestation-json", "vx.agent-contract-python",
            '{"schema_version":"1","provider_id":"p","integration_type":"mcp","observed_at":"x","expires_at":"y","probe_result":"ok","capabilities":[],"evidence":[]}',
        )
        self.assertEqual(result["status"], "HOLD_TARGET_NOT_ALLOWLISTED")

    def test_unconfigured_markdown_parser_returns_hold(self) -> None:
        result = self.fabric.analyze("vsm.protocol-markdown", "# Protocol")
        self.assertEqual(result["status"], "HOLD_ADAPTER_NOT_CONFIGURED")

    def test_innovation_packet_is_deterministic_and_not_canonical(self) -> None:
        first = plan_innovation(self.fabric, "vx.intent-json", "add typed error states")
        second = plan_innovation(self.fabric, "vx.intent-json", "add typed error states")
        self.assertEqual(first["packet_id"], second["packet_id"])
        self.assertEqual(first["status"], "HOLD_ADAPTER_NOT_CONFIGURED")
        self.assertFalse(first["canonical_mutation_allowed"])
        self.assertTrue(all(stage["state"] == "NOT_RUN" for stage in first["stages"]))

    def test_oversized_source_is_bounded(self) -> None:
        result = self.fabric.analyze("vx.intent-json", " " * 262_145)
        self.assertEqual(result["status"], "PARSE_FAILED")
        self.assertEqual(result["error_code"], "source_byte_limit_exceeded")

    def test_duplicate_language_version_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.document)
        invalid["languages"].append(copy.deepcopy(invalid["languages"][0]))
        with self.assertRaisesRegex(RegistryError, "language_version_collision"):
            SystemLanguageFabric(invalid)

    def test_authority_cannot_be_overridden_by_registry_data(self) -> None:
        invalid = copy.deepcopy(self.document)
        invalid["canonical_authority"] = "VX"
        with self.assertRaisesRegex(RegistryError, "system_authority_boundary_mismatch"):
            SystemLanguageFabric(invalid)

    def test_registry_targets_must_be_registered(self) -> None:
        invalid = copy.deepcopy(self.document)
        invalid["languages"][1]["allowed_targets"] = ["ghost.language"]
        with self.assertRaisesRegex(RegistryError, "language_target_not_registered"):
            SystemLanguageFabric(invalid)

    def test_invalid_source_type_is_rejected(self) -> None:
        with self.assertRaises(LanguageInputError):
            self.fabric.analyze("vx.intent-json", 123)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
