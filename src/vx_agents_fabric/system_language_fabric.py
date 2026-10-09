"""Registry and safe syntax-analysis boundary for VAIXLNS/VX system languages."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "1.0.0"
MAX_SOURCE_BYTES = 262_144
MAX_JSON_NODES = 50_000
MAX_JSON_DEPTH = 64
MAX_AST_NODES = 10_000
VALID_EVIDENCE_STATES = {"VERIFIED", "SPECIFIED", "PARTIAL", "MISSING", "CONFLICT", "PROPOSAL"}
VALID_GRAMMARS = {"json", "python_ast", "math_expression", "markdown", "yaml", "unresolved"}
BUILTIN_PARSERS = {
    "json": "builtin.json.v1",
    "python_ast": "builtin.python-ast.v1",
    "math_expression": "builtin.math-expression.v1",
}
SAFE_MATH_FUNCTIONS = {"sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "log", "log10", "exp", "fabs"}
SAFE_MATH_CONSTANTS = {"pi", "e", "tau"}
SAFE_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
SAFE_UNARYOPS = (ast.UAdd, ast.USub)


class RegistryError(ValueError):
    """The declared language registry is structurally invalid."""


class LanguageInputError(ValueError):
    """A source input is malformed, unsafe, or exceeds bounded analysis limits."""

    def __init__(self, error_code: str, detail: str = "") -> None:
        super().__init__(error_code)
        self.error_code = error_code
        self.detail = detail


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LanguageSpec:
    language_id: str
    version: str
    display_name: str
    grammar: str
    source_status: str
    canonical_ref: str
    reference_state: str
    parser_adapter: str | None
    semantic_adapter: str | None
    compiler_adapter: str | None
    required_root_keys: tuple[str, ...]
    capabilities: tuple[str, ...]
    allowed_targets: tuple[str, ...]
    notes: str

    @property
    def key(self) -> str:
        return f"{self.language_id}@{self.version}"


class SystemLanguageFabric:
    """Read-only registry and bounded parser boundary; it never runs source code."""

    def __init__(self, registry: Mapping[str, Any]) -> None:
        if not isinstance(registry, Mapping):
            raise RegistryError("registry_must_be_object")
        self.registry_document = dict(registry)
        self._validate_registry()
        self._specs: dict[str, LanguageSpec] = {}
        for raw in self.registry_document["languages"]:
            spec = LanguageSpec(
                language_id=raw["language_id"], version=raw["version"],
                display_name=raw["display_name"], grammar=raw["grammar"],
                source_status=raw["source_status"], canonical_ref=raw["canonical_ref"],
                reference_state=raw["reference_state"], parser_adapter=raw["parser_adapter"],
                semantic_adapter=raw["semantic_adapter"], compiler_adapter=raw["compiler_adapter"],
                required_root_keys=tuple(raw["required_root_keys"]),
                capabilities=tuple(raw["capabilities"]), allowed_targets=tuple(raw["allowed_targets"]),
                notes=raw["notes"],
            )
            self._specs[spec.key] = spec

    @classmethod
    def from_file(cls, path: str | Path) -> "SystemLanguageFabric":
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except OSError as exc:
            raise RegistryError("registry_file_read_failed") from exc
        except json.JSONDecodeError as exc:
            raise RegistryError("registry_json_invalid") from exc
        return cls(payload)

    def _validate_registry(self) -> None:
        root = self.registry_document
        required = {
            "schema_version", "artifact_id", "status", "canonical_authority", "orchestrator",
            "assurance_gate", "canonical_source_rule", "policy", "languages",
        }
        missing = sorted(required - set(root))
        if missing:
            raise RegistryError("registry_missing_fields:" + ",".join(missing))
        if root["schema_version"] != SCHEMA_VERSION:
            raise RegistryError("registry_schema_version_unsupported")
        if root["canonical_authority"] != "VAIXLNS" or root["orchestrator"] != "VX" or root["assurance_gate"] != "ARC-X":
            raise RegistryError("system_authority_boundary_mismatch")
        if root["status"] not in VALID_EVIDENCE_STATES:
            raise RegistryError("registry_status_invalid")
        if not isinstance(root["languages"], list) or not root["languages"] or len(root["languages"]) > 250:
            raise RegistryError("registry_languages_shape_invalid")
        seen: set[str] = set()
        language_fields = {
            "language_id", "version", "display_name", "grammar", "source_status",
            "canonical_ref", "reference_state", "parser_adapter", "semantic_adapter",
            "compiler_adapter", "required_root_keys", "capabilities", "allowed_targets", "notes",
        }
        for item in root["languages"]:
            if not isinstance(item, dict):
                raise RegistryError("language_entry_must_be_object")
            missing_item = sorted(language_fields - set(item))
            if missing_item:
                raise RegistryError("language_entry_missing_fields:" + ",".join(missing_item))
            language_id, version = item["language_id"], item["version"]
            if not isinstance(language_id, str) or not re.fullmatch(r"[a-z][a-z0-9_.-]{2,95}", language_id):
                raise RegistryError("language_id_invalid")
            if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version):
                raise RegistryError("language_version_invalid")
            key = f"{language_id}@{version}"
            if key in seen:
                raise RegistryError("language_version_collision:" + key)
            seen.add(key)
            if item["grammar"] not in VALID_GRAMMARS:
                raise RegistryError("language_grammar_invalid:" + key)
            if item["source_status"] not in VALID_EVIDENCE_STATES:
                raise RegistryError("language_source_status_invalid:" + key)
            if not all(isinstance(item[name], str) and item[name].strip()
                       for name in ("display_name", "canonical_ref", "reference_state", "notes")):
                raise RegistryError("language_text_field_invalid:" + key)
            for name in ("parser_adapter", "semantic_adapter", "compiler_adapter"):
                if item[name] is not None and (not isinstance(item[name], str) or not item[name].strip()):
                    raise RegistryError("language_adapter_field_invalid:" + key)
            if item["parser_adapter"] is not None and item["parser_adapter"] != BUILTIN_PARSERS.get(item["grammar"]):
                raise RegistryError("unrecognized_parser_adapter:" + key)
            for name in ("required_root_keys", "capabilities", "allowed_targets"):
                values = item[name]
                if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
                    raise RegistryError("language_list_field_invalid:" + name + ":" + key)
                if len(values) != len(set(values)):
                    raise RegistryError("language_list_field_duplicate:" + name + ":" + key)
        known = {item["language_id"] for item in root["languages"]}
        for item in root["languages"]:
            for target in item["allowed_targets"]:
                if target not in known:
                    raise RegistryError("language_target_not_registered:" + item["language_id"] + ":" + target)

    def languages(self) -> list[dict[str, Any]]:
        return [
            {
                "language_id": spec.language_id, "version": spec.version,
                "display_name": spec.display_name, "grammar": spec.grammar,
                "source_status": spec.source_status, "canonical_ref": spec.canonical_ref,
                "reference_state": spec.reference_state, "parser_adapter": spec.parser_adapter,
                "semantic_adapter": spec.semantic_adapter, "compiler_adapter": spec.compiler_adapter,
                "capabilities": list(spec.capabilities), "allowed_targets": list(spec.allowed_targets),
            }
            for spec in sorted(self._specs.values(), key=lambda value: (value.language_id, value.version))
        ]

    def resolve(self, language_id: str, version: str | None = None) -> LanguageSpec:
        candidates = [spec for spec in self._specs.values() if spec.language_id == language_id]
        if version is not None:
            candidates = [spec for spec in candidates if spec.version == version]
        if not candidates:
            raise KeyError("language_not_registered:" + language_id)
        return max(candidates, key=lambda spec: tuple(int(part) for part in spec.version.split("-", 1)[0].split(".")))

    def analyze(self, language_id: str, source: str, version: str | None = None) -> dict[str, Any]:
        spec = self.resolve(language_id, version)
        if not isinstance(source, str):
            raise LanguageInputError("source_must_be_text")
        try:
            source_bytes = source.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise LanguageInputError("source_utf8_invalid") from exc
        source_digest = hashlib.sha256(source_bytes).hexdigest()
        if len(source_bytes) > MAX_SOURCE_BYTES:
            return self._analysis_result(spec, source_digest, "PARSE_FAILED", "source_byte_limit_exceeded")
        if spec.parser_adapter is None or spec.grammar not in BUILTIN_PARSERS:
            return self._analysis_result(spec, source_digest, "HOLD_ADAPTER_NOT_CONFIGURED", "parser_adapter_not_configured")
        try:
            summary = self._parse(spec.grammar, source)
        except LanguageInputError as exc:
            return self._analysis_result(spec, source_digest, "PARSE_FAILED", exc.error_code, detail=exc.detail)
        if spec.required_root_keys:
            missing = list(spec.required_root_keys) if summary.get("root_type") != "object" else [
                key for key in spec.required_root_keys if key not in summary.get("root_keys", [])
            ]
        else:
            missing = []
        return {
            "schema_version": SCHEMA_VERSION, "language_id": spec.language_id,
            "language_version": spec.version, "status": "INCOMPLETE" if missing else "PARSE_PASS",
            "source_sha256": source_digest, "grammar": spec.grammar,
            "parser_adapter": spec.parser_adapter, "parsed_summary": summary,
            "structural_state": "INCOMPLETE" if missing else "PASS",
            "missing_required_root_keys": missing, "semantic_state": "NOT_CONFIGURED",
            "execution_state": "NOT_EXECUTED", "proof_level": "SYNTAX_ONLY",
            "limitations": [
                "Parsing is not semantic correctness or runtime verification.",
                "No code is executed and no canonical or external state is changed.",
            ],
        }

    @staticmethod
    def _analysis_result(spec: LanguageSpec, source_digest: str, status: str,
                         error_code: str, detail: str = "") -> dict[str, Any]:
        result = {
            "schema_version": SCHEMA_VERSION, "language_id": spec.language_id,
            "language_version": spec.version, "status": status,
            "source_sha256": source_digest, "grammar": spec.grammar,
            "parser_adapter": spec.parser_adapter, "error_code": error_code,
            "semantic_state": "NOT_CONFIGURED", "execution_state": "NOT_EXECUTED",
            "proof_level": "NONE",
            "limitations": ["No code is executed and no canonical or external state is changed."],
        }
        if detail:
            result["detail"] = detail[:160]
        return result

    @staticmethod
    def _parse(grammar: str, source: str) -> dict[str, Any]:
        if grammar == "json":
            try:
                parsed = json.loads(source, object_pairs_hook=_unique_object, parse_constant=_reject_json_constant)
            except LanguageInputError:
                raise
            except (json.JSONDecodeError, RecursionError) as exc:
                raise LanguageInputError("json_syntax_error") from exc
            count, depth = _measure_json(parsed)
            if count > MAX_JSON_NODES:
                raise LanguageInputError("json_node_limit_exceeded")
            if depth > MAX_JSON_DEPTH:
                raise LanguageInputError("json_depth_limit_exceeded")
            if isinstance(parsed, dict):
                root_type, root_keys = "object", sorted(parsed)
            elif isinstance(parsed, list):
                root_type, root_keys = "array", []
            else:
                root_type, root_keys = "scalar", []
            return {"root_type": root_type, "root_keys": root_keys, "node_count": count, "max_depth": depth}
        if grammar == "python_ast":
            try:
                tree = ast.parse(source, mode="exec", type_comments=False)
            except (SyntaxError, ValueError, RecursionError) as exc:
                raise LanguageInputError("python_syntax_error") from exc
            nodes = list(ast.walk(tree))
            if len(nodes) > MAX_AST_NODES:
                raise LanguageInputError("python_ast_node_limit_exceeded")
            return {"root_type": "module", "node_count": len(nodes),
                    "top_level_node_types": [type(node).__name__ for node in tree.body[:100]]}
        if grammar == "math_expression":
            try:
                tree = ast.parse(source, mode="eval")
            except (SyntaxError, ValueError, RecursionError) as exc:
                raise LanguageInputError("math_expression_syntax_error") from exc
            nodes = list(ast.walk(tree))
            if len(nodes) > 128:
                raise LanguageInputError("math_expression_node_limit_exceeded")
            _validate_math_node(tree)
            return {"root_type": "expression", "node_count": len(nodes), "evaluation": "NOT_PERFORMED"}
        raise LanguageInputError("parser_adapter_not_configured")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LanguageInputError("json_duplicate_key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise LanguageInputError("json_nonstandard_numeric_constant:" + value)


def _measure_json(root: Any) -> tuple[int, int]:
    stack: list[tuple[Any, int]] = [(root, 1)]
    count, max_depth = 0, 0
    while stack:
        value, depth = stack.pop()
        count += 1
        max_depth = max(max_depth, depth)
        if count > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            return count, depth
        if isinstance(value, dict):
            stack.extend((child, depth + 1) for child in value.values())
        elif isinstance(value, list):
            stack.extend((child, depth + 1) for child in value)
        elif isinstance(value, float) and not math.isfinite(value):
            raise LanguageInputError("json_non_finite_number")
    return count, max_depth


def _validate_math_node(node: ast.AST, depth: int = 0) -> None:
    if depth > 32:
        raise LanguageInputError("math_expression_depth_limit_exceeded")
    if isinstance(node, ast.Expression):
        _validate_math_node(node.body, depth + 1)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise LanguageInputError("math_constant_type_not_allowed")
        if abs(float(node.value)) > 1e100 or not math.isfinite(float(node.value)):
            raise LanguageInputError("math_constant_out_of_bounds")
    elif isinstance(node, ast.Name):
        if node.id not in SAFE_MATH_CONSTANTS:
            raise LanguageInputError("math_name_not_allowed")
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, SAFE_UNARYOPS):
        _validate_math_node(node.operand, depth + 1)
    elif isinstance(node, ast.BinOp) and isinstance(node.op, SAFE_BINOPS):
        if isinstance(node.op, ast.Pow) and isinstance(node.right, ast.Constant):
            if isinstance(node.right.value, bool) or not isinstance(node.right.value, (int, float)) or abs(node.right.value) > 100:
                raise LanguageInputError("math_exponent_limit_exceeded")
        _validate_math_node(node.left, depth + 1)
        _validate_math_node(node.right, depth + 1)
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in SAFE_MATH_FUNCTIONS and not node.keywords:
        for argument in node.args:
            _validate_math_node(argument, depth + 1)
    else:
        raise LanguageInputError("math_operation_not_allowed")


def plan_translation(fabric: SystemLanguageFabric, source_language: str, target_language: str,
                     source: str, source_version: str | None = None,
                     target_version: str | None = None) -> dict[str, Any]:
    source_spec = fabric.resolve(source_language, source_version)
    target_spec = fabric.resolve(target_language, target_version)
    analysis = fabric.analyze(source_language, source, source_version)
    gates = [
        {"gate": "SOURCE_SYNTAX", "state": analysis["status"]},
        {"gate": "SOURCE_SEMANTICS", "state": "NOT_CONFIGURED" if source_spec.semantic_adapter is None else "DECLARED_NOT_EXECUTED"},
        {"gate": "TARGET_COMPILER", "state": "NOT_CONFIGURED" if target_spec.compiler_adapter is None else "DECLARED_NOT_EXECUTED"},
        {"gate": "DIFFERENTIAL_TESTS", "state": "NOT_CONFIGURED"},
        {"gate": "ARC_X_PROOF_REVIEW", "state": "NOT_CONFIGURED"},
        {"gate": "VAIXLNS_CANONICAL_ADMISSION", "state": "REQUIRES_SEPARATE_APPROVAL"},
    ]
    if analysis["status"] != "PARSE_PASS":
        status = "HOLD_SOURCE_ANALYSIS_INCOMPLETE"
    elif target_language not in source_spec.allowed_targets:
        status = "HOLD_TARGET_NOT_ALLOWLISTED"
    elif source_spec.semantic_adapter is None or target_spec.compiler_adapter is None:
        status = "HOLD_ADAPTER_NOT_CONFIGURED"
    else:
        status = "HOLD_VERIFICATION_GATES_REQUIRED"
    material = {
        "schema_version": SCHEMA_VERSION, "operation": "TRANSLATE",
        "source_language": source_spec.key, "target_language": target_spec.key,
        "source_sha256": analysis["source_sha256"], "status": status, "gates": gates,
    }
    material["plan_id"] = "VX-LANG-PLAN-" + sha256_text(canonical_json(material))[:20]
    material["generated_source"] = None
    material["execution_performed"] = False
    material["canonical_mutation_allowed"] = False
    return material


def plan_innovation(fabric: SystemLanguageFabric, language_id: str, goal: str,
                    version: str | None = None) -> dict[str, Any]:
    spec = fabric.resolve(language_id, version)
    if not isinstance(goal, str) or not goal.strip():
        raise LanguageInputError("innovation_goal_required")
    if len(goal.encode("utf-8")) > 16_000:
        raise LanguageInputError("innovation_goal_byte_limit_exceeded")
    stages = [
        ("DISCOVER_EXISTING_CANON", "Resolve original and derived specifications; preserve history."),
        ("FORMALIZE_GRAMMAR", "Define grammar, types, namespaces, versions and ambiguity rules."),
        ("MODEL_SEMANTICS", "Specify state transitions, determinism, errors and effect boundaries."),
        ("DESIGN_COMPILER_IR", "Define a versioned intermediate representation with source maps and provenance."),
        ("GENERATE_CONFORMANCE_TESTS", "Create positive, negative, boundary, fuzz and round-trip tests."),
        ("ADVERSARIAL_REVIEW", "Test injection, ambiguity, resource exhaustion and cross-language confusion."),
        ("ARC_X_EVIDENCE", "Bind claims to reproducible test output and independent proof review."),
        ("VAIXLNS_ADMISSION", "Propose canonical adoption without mutating project.genome."),
    ]
    material = {
        "schema_version": SCHEMA_VERSION, "artifact_type": "SYSTEM_LANGUAGE_INNOVATION_PACKET",
        "status": "PROPOSAL", "language_id": spec.language_id, "language_version": spec.version,
        "source_status": spec.source_status, "goal_sha256": sha256_text(goal),
        "language_reference": spec.canonical_ref,
        "stages": [{"stage": name, "purpose": purpose, "state": "NOT_RUN"} for name, purpose in stages],
        "unconfigured_gates": [
            name for name, configured in (
                ("SEMANTIC_ADAPTER", spec.semantic_adapter is not None),
                ("COMPILER_ADAPTER", spec.compiler_adapter is not None),
                ("CONFORMANCE_TEST_ORACLE", False), ("ARC_X_PROOF_VERIFIER", False),
                ("CANONICAL_ADMISSION_INTERFACE", False),
            ) if not configured
        ],
        "deliverables": [
            "versioned_grammar_spec", "typed_intermediate_representation", "source_map_and_provenance",
            "deterministic_translator", "conformance_test_suite", "performance_and_resource_limits",
            "security_review", "reproducible_proof_bundle",
        ],
        "canonical_mutation_allowed": False, "execution_performed": False,
        "limitations": [
            "This packet plans innovation; it does not claim the language is canonical or implemented.",
            "Missing adapters and proof gates require HOLD; success cannot be inferred from names or descriptions.",
        ],
    }
    material["packet_id"] = "VX-LANG-INNOV-" + sha256_text(canonical_json(material))[:20]
    material["status"] = "HOLD_ADAPTER_NOT_CONFIGURED" if material["unconfigured_gates"] else "PROPOSAL"
    return material


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only VAIXLNS/VX system-language registry and syntax analyzer")
    parser.add_argument("--config", default="config/system_language_registry.v1.json")
    parser.add_argument("--list", action="store_true", help="list declared language entries")
    parser.add_argument("--analyze-language", help="registered language ID to parse safely")
    parser.add_argument("--source-file", help="UTF-8 source file for analysis or translation planning")
    parser.add_argument("--from-language", help="source language ID for a translation plan")
    parser.add_argument("--to-language", help="target language ID for a translation plan")
    parser.add_argument("--innovation-goal", help="create an innovation plan for the selected language ID")
    args = parser.parse_args(argv)
    try:
        fabric = SystemLanguageFabric.from_file(args.config)
        if args.list:
            result = {"schema_version": SCHEMA_VERSION, "status": "DECLARED_ONLY", "languages": fabric.languages()}
        elif args.innovation_goal and args.analyze_language:
            result = plan_innovation(fabric, args.analyze_language, args.innovation_goal)
        elif args.analyze_language:
            if not args.source_file:
                parser.error("--analyze-language requires --source-file")
            result = fabric.analyze(args.analyze_language, Path(args.source_file).read_text(encoding="utf-8"))
        elif args.from_language and args.to_language:
            if not args.source_file:
                parser.error("translation planning requires --source-file")
            result = plan_translation(fabric, args.from_language, args.to_language, Path(args.source_file).read_text(encoding="utf-8"))
        else:
            parser.error("choose --list, --analyze-language with --source-file, both translation flags, or --innovation-goal with --analyze-language")
            return 4
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0 if result.get("status") in {"DECLARED_ONLY", "PARSE_PASS"} else 2
    except (OSError, RegistryError, LanguageInputError, KeyError) as exc:
        print(json.dumps({"status": "INPUT_ERROR", "error": str(exc)}, ensure_ascii=False))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
