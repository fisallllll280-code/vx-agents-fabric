"""Bounded, offline importer for the version-pinned Unicode emoji-test data.

This produces a deterministic inventory and membership evidence only. It does
not infer meanings, render glyphs, compile NXL source, execute code, or mutate
canonical VAIXLNS records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

MAX_SOURCE_BYTES = 2_097_152
MAX_RECORDS = 100_000
VALID_STATUSES = {"fully-qualified", "minimally-qualified", "unqualified", "component"}
VERSION_RE = re.compile(r"^#\s*Version:\s*(\d+\.\d+)\s*$")


class SymbolDataError(ValueError):
    """The pinned source file cannot be accepted as a symbol inventory."""


def _sequence_id(codepoints: tuple[int, ...]) -> str:
    return "U+" + "-".join(f"{cp:04X}" for cp in codepoints)


def parse_emoji_test(
    payload: bytes,
    *,
    expected_version: str,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    if len(payload) > MAX_SOURCE_BYTES:
        raise SymbolDataError("source_byte_limit_exceeded")
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256.lower():
        raise SymbolDataError("source_hash_mismatch")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SymbolDataError("source_not_utf8") from exc

    observed_version: str | None = None
    rows: list[dict[str, Any]] = []
    seen: set[tuple[int, ...]] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        version_match = VERSION_RE.match(line.strip())
        if version_match:
            version = version_match.group(1)
            if observed_version is not None and observed_version != version:
                raise SymbolDataError("conflicting_version_headers")
            observed_version = version
            continue
        body, separator, comment = line.partition("#")
        if not separator or not body.strip():
            continue
        fields = body.split(";")
        if len(fields) != 2:
            raise SymbolDataError(f"invalid_record:{line_number}")
        raw_points, raw_status = fields[0].strip(), fields[1].strip()
        if raw_status not in VALID_STATUSES:
            raise SymbolDataError(f"unknown_status:{line_number}")
        try:
            codepoints = tuple(int(token, 16) for token in raw_points.split())
        except ValueError as exc:
            raise SymbolDataError(f"invalid_codepoint:{line_number}") from exc
        if not codepoints:
            raise SymbolDataError(f"empty_sequence:{line_number}")
        if any(cp > 0x10FFFF or 0xD800 <= cp <= 0xDFFF for cp in codepoints):
            raise SymbolDataError(f"invalid_unicode_scalar:{line_number}")
        if codepoints in seen:
            raise SymbolDataError(f"duplicate_sequence:{line_number}")
        seen.add(codepoints)
        name = comment.strip()
        rows.append({
            "sequence_id": _sequence_id(codepoints),
            "codepoints": [f"{cp:04X}" for cp in codepoints],
            "sequence": "".join(chr(cp) for cp in codepoints),
            "qualification_status": raw_status,
            "source_label": name or None,
            "source_line": line_number,
        })
        if len(rows) > MAX_RECORDS:
            raise SymbolDataError("record_limit_exceeded")

    if not rows:
        raise SymbolDataError("no_records_found")
    if observed_version is not None and observed_version != expected_version:
        raise SymbolDataError("version_mismatch")
    return {
        "schema_version": "1.0.0",
        "artifact_id": "VAIXLNS.OMEGA_SYMBOL_IR.V1",
        "status": "PARSE_PASS",
        "proof_level": "SOURCE_HASH_AND_DATASET_MEMBERSHIP_ONLY",
        "unicode_standard": "UTS #51",
        "expected_version": expected_version,
        "observed_source_version": observed_version or "NOT_DECLARED_IN_HEADER",
        "source_sha256": digest,
        "source_bytes": len(payload),
        "record_count": len(rows),
        "semantic_state": "NOT_CONFIGURED",
        "compiler_state": "NOT_CONFIGURED",
        "execution_state": "NOT_EXECUTED",
        "canonical_admission_state": "NOT_REQUESTED",
        "records": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--version", required=True, help="Pinned Emoji version, for example 18.0")
    parser.add_argument("--sha256", help="Optional independently pinned SHA-256")
    parser.add_argument("--output", help="Write deterministic JSON to this local path")
    args = parser.parse_args(argv)
    try:
        payload = Path(args.source_file).read_bytes()
        result = parse_emoji_test(
            payload, expected_version=args.version, expected_sha256=args.sha256
        )
        rendered = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, SymbolDataError) as exc:
        print(f"OMEGA_SYMBOL_HOLD: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
