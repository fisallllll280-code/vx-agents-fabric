# VAIXLNS Ω-SYMBOL Fabric v1

**Artifact:** `VAIXLNS.OMEGA_SYMBOL_FABRIC.V1`  
**Status:** PROPOSAL — bounded importer implemented; NXL grammar/compiler adapters remain unavailable  
**Authority:** VAIXLNS  
**Orchestrator:** VX  
**Independent assurance:** ARC-X

## Purpose

Provide one versioned symbol layer that offices can use in indexes, prompts, schemas, user interfaces, event records, and generated documentation without treating a displayed glyph as identity, meaning, proof, or permission.

The first source domain is Unicode Emoji. This feature is a bounded subsystem of the existing Prompt Office and System Language Fabric; it does not create another top-level VAIXLNS system.

## Authoritative source and version

The supplied full-list chart is an illustrative view. UTS #51 identifies the versioned emoji data files, especially `emoji-test.txt`, as the implementation data source. Unicode 18.0 is the version recorded for this proposal as of 2026-10-25.

- Chart reference: https://unicode.org/emoji/charts/full-emoji-list.html
- UTS #51: https://www.unicode.org/reports/tr51/
- Versioned data index: https://www.unicode.org/Public/UCD/latest/emoji/
- Emoji test data: https://www.unicode.org/Public/UCD/latest/emoji/emoji-test.txt

Runtime import is offline. A trusted maintainer supplies a locally obtained, version-pinned file; the importer records the exact SHA-256 and rejects malformed UTF-8, invalid scalar values, duplicate sequences, unknown qualification states, oversize input, and an observed version mismatch. No network client fetches data at runtime. A release must pin an immutable versioned URL and reviewed checksum before the corpus can be admitted.

Do not apply Unicode normalization to source sequences. Keep each exact code-point sequence. A family, flag, keycap, modifier, or ZWJ sequence is an ordered sequence, not an independent single code point.

## Implemented substrate

`src/vx_agents_fabric/omega_symbol_fabric.py` implements a read-only parser for the Unicode `emoji-test.txt` format. It emits deterministic JSON records with:

- version and SHA-256 of the exact UTF-8 source;
- stable code-point identity such as `U+1F469-200D-1F4BB`;
- original sequence, qualification status, source label, and source line;
- explicit `semantic_state=NOT_CONFIGURED`, `compiler_state=NOT_CONFIGURED`, and `execution_state=NOT_EXECUTED`.

Command:

~~~bash
PYTHONPATH=src python -m vx_agents_fabric.omega_symbol_fabric \
  --source-file /path/to/emoji-test.txt --version 18.0 \
  --sha256 <reviewed-sha256> --output artifacts/omega-symbol-ir.json
~~~

A parse pass establishes only that the supplied dataset was bounded, structurally parsed, and hashed. It does not establish official origin, semantic correctness of labels, font coverage, equivalence between vendors, or conformance of a custom language implementation.

## Candidate NXL crosswalk

The exact language names below were recovered from user project context. Their original grammar and semantics are not mounted in this repository. These are candidate responsibilities only; no syntax is invented, and every language adapter remains `HOLD` until its source specification is recovered and reviewed.

| Language | Candidate responsibility | Current gate |
|---|---|---|
| `NXL-S` | Exact symbol literal and escape surface | Grammar not mounted |
| `NXL-SYS` | Versioned symbol identity and registry contract | Semantics not configured |
| `NXL-ARCH` | Isolation boundaries between source, parser, IR, and renderers | Architecture mapping proposed |
| `NXL-CON` | Input, version, integrity, and authority constraints | Contract mapping proposed |
| `NXL-PROOF` | Source provenance, hash, parser evidence, and conformance claims | Proof rules not configured |
| `NXL-EXEC` | Read-only runtime lookup request/response contract | Runtime semantics not configured |
| `NXL-EVO` | Append-only Unicode version diff and deprecation lineage | Evolution rules not configured |
| `NXL-Q` | Typed search/filter query over the registry | Query grammar not mounted |
| `NXL-VIS` | Rendering, fallback glyph, accessibility label, and platform capability contract | Renderer not configured |

The bridge can generate a neutral Ω-SYMBOL IR from a pinned dataset. It must not emit NXL source until the source grammars, types, semantics, and compiler targets are recovered. Translation and canonical admission remain `HOLD`.

## Office workflow

1. **Research Office (`Ω.RES`)** identifies the applicable UTS #51, CLDR annotations, data release, and provenance.
2. **Symbol and Language Engineering (`Ω.SYMBOL`)** pins a local dataset, runs the bounded parser, and proposes code-point identity mappings.
3. **Deep Engineering (`Ω.ENG`)** reviews the IR, contracts, interoperability, and target NXL adapter requirements.
4. **Design Intelligence (`Ω.DESIGN`)** proposes accessible icon use, text labels, and platform fallback behavior. Rendering is checked separately on target platforms.
5. **Independent Parent-Mind Council (`Ω.PARENT`)** challenges ambiguity, backward compatibility, and evidence claims.
6. **ARC-X** reviews source hash, parser implementation, version diff, and conformance evidence before any VERIFIED claim.

No office may turn an emoji into authorization, agent identity, financial instruction, security state, or execution command solely from its visual appearance or a model-generated label.

## Semantic and visual layers

- Store Unicode code-point identity separately from CLDR short names, keywords, locale, and source version.
- Treat short names and keywords as localized search metadata, never as canonical meaning.
- Keep glyph rendering separate from Unicode membership. A platform may lack a glyph or render it differently.
- Provide a text equivalent for each product-level meaning and control. Never rely on color or glyph alone for accessibility.
- Disambiguate visually similar symbols in high-impact flows. Require explicit typed values for money, permissions, security, and execution.
- Preserve the original source record when labels change. Record derived translations and reviewer provenance separately.

## Evidence and release gates

| Claim | Required evidence |
|---|---|
| Dataset parsed | exact bytes, SHA-256, declared Unicode version, parser fingerprint, record count |
| Sequence is in release | exact code-point sequence matched to the pinned dataset |
| Label is localized | CLDR version, locale, annotation key, and translation provenance |
| NXL adapter works | recovered grammar, versioned compiler adapter, conformance vectors, round-trip and adversarial evidence |
| Product rendering works | target platform/device/browser, font/rendering result, fallback and accessibility review |
| Canonical adoption | independent ARC-X review and separate VAIXLNS admission approval |

Current result: parser implementation is committed to the isolated PR branch; no Unicode data file has been imported, no custom NXL compiler has run, no UI rendering has been evaluated, and no artifact is VERIFIED.
