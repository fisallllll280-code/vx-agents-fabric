# Ω-SYMBOL Index v1

**Index ID:** `VAIXLNS.INDEX.OMEGA_SYMBOL.V1`  
**State:** PROPOSED  
**Parent workstream:** Prompt Office + System Language Fabric, PR #8  
**Canonical authority:** VAIXLNS  
**Protected references:** `project.genome` and `Ω.000` remain untouched

## Scope

Versioned Unicode Emoji data is indexed as exact code-point sequences. The official chart is a discovery/display reference; UTS #51 data files provide the versioned implementation source. The current proposal pins Emoji 18.0 as the target version at `https://www.unicode.org/Public/18.0.0/emoji/emoji-test.txt`. See [the specification](../integration/OMEGA_SYMBOL_FABRIC_V1.md).

## NXL source and current maturity

The NEXENT source at commit `f62cf5920174551f9a8f88deb420f9515bedc284` defines the nine language names and roles. Its current registry marks all nine PROPOSED and uses placeholder grammar/semantics fields; it does not provide formal grammars or executable compilers. Ω-SYMBOL records a candidate crosswalk for every language and keeps compilation on HOLD.

## Atomic inventory record

Every imported entry must retain:

- `sequence_id`: deterministic U+ code-point identity;
- exact `sequence` and `codepoints` in source order;
- Unicode/Emoji version and source URI;
- exact source SHA-256 and source line;
- qualification status from `emoji-test.txt`;
- localized label, locale, CLDR release, and provenance as separate derived fields;
- font/platform rendering observations as separate environment evidence;
- lifecycle state: `ORIGINAL`, `DERIVED`, `SUPERSEDED`, or `ACTIVE`;
- validation state: `NOT_RUN`, `PARSE_PASS`, `HOLD`, or `VERIFIED`.

## Office ownership and gates

| Office | Indexed responsibility | Admission gate |
|---|---|---|
| `Ω.RES` | UTS #51, CLDR and version provenance | Source URI/version/hash recorded |
| `Ω.SYMBOL` | Sequence parsing and stable identity | Bounded parse, uniqueness, version checks |
| `Ω.ENG` | IR and NXL adapter contracts | Grammar/semantics recovered before translation |
| `Ω.DESIGN` | Accessibility and platform rendering | Target-specific fallback evidence |
| `Ω.PARENT` | Independent challenge and contradiction review | Independent evidence, no self-approval |
| `ARC-X` | Assurance verdict | Claim-bound evidence and replayable checks |

## Status ledger

| Component | State | Evidence |
|---|---|---|
| Unicode 18.0 target identified | PROPOSED | UTS #51 current release page |
| Offline parser source added | IMPLEMENTED | `src/vx_agents_fabric/omega_symbol_fabric.py` on PR branch |
| Version-pinned Unicode corpus imported | NOT_RUN | No local corpus mounted |
| NXL grammars recovered | HOLD | Original language specifications unavailable in this repository |
| NXL compiler adapters | NOT_CONFIGURED | No compiler or semantic adapters |
| UI glyph support | NOT_RUN | No device/browser rendering evidence |
| ARC-X admission | NOT_RUN | Independent review not yet performed |

No record may become VERIFIED from the parser's syntax result alone.
