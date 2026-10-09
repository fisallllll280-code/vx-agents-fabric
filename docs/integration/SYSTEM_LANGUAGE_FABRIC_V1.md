# VAIXLNS/VX System Language Fabric v1

**Artifact:** VAIXLNS.SYSTEM_LANGUAGE_FABRIC.V1  
**Status:** PROPOSAL — implementation scaffold; canonical grammar adoption is not implied.  
**Canonical authority:** VAIXLNS / project.genome  
**Orchestrator:** VX  
**Independent assurance:** ARC-X

## Purpose

Connect the system's declared language surfaces to one governed development lifecycle. A language is not just a filename or prompt: it needs an explicit identity, version, grammar, semantics, authority boundary, compiler target, conformance tests, provenance and evidence of execution.

The fabric provides a versioned registry, safe built-in syntax analysis, a deterministic translation-plan contract, and an innovation packet. It does not assert that every listed surface is already a formal language, does not infer unseen historical specifications, and does not promote this proposed registry into the Golden Source.

## Authority and lifecycle

1. **Recover canon** — retrieve the original project.genome, Omega.000 index, historical artifacts and relevant repository references. Preserve Original, Derived, Superseded and Active lineage.
2. **Identify language** — resolve language ID/version, grammar and exact source bytes. A name or documentation link alone is not implementation evidence.
3. **Parse** — use a declared, bounded parser. Python inputs are parsed as AST only; math expressions use an allowlist; JSON rejects duplicate keys and non-standard NaN/Infinity values.
4. **Check structure and semantics** — separate syntax acceptance from schemas, typing, authority rules, determinism and runtime semantics. A missing semantic adapter returns HOLD.
5. **Lower to an intermediate representation** — future adapters must produce a versioned IR with source maps, source/target hashes, typed effects, event lineage and explicit failure states.
6. **Translate or generate** — requires an allowlisted target plus explicitly configured semantic and compiler adapters. Never run generated code inside the registry auditor.
7. **Conformance and adversarial testing** — grammar tests, malformed inputs, ambiguity cases, round-trip/differential tests, resource limits, determinism checks and provenance checks.
8. **ARC-X verification** — bind each claim to immutable inputs, tool/version fingerprints, reproducible test output and independent review. Syntax parsing alone is never VERIFIED.
9. **VAIXLNS admission** — submit a candidate with original/derived lineage and evidence for governance review. No fabric operation writes project.genome or changes canonical authority.

## Initial declared surfaces

| Language ID | What is evidenced here | Current boundary |
|---|---|---|
| vaixl.project-genome | Golden Source identity is referenced by project context | External bytes and grammar are not mounted; parser remains NOT_CONFIGURED |
| vx.intent-json | Candidate envelope is defined as a proposal | JSON syntax and candidate root fields only; not canonical VX semantics |
| vx.agent-contract-python | Agent/Workflow contracts exist in this repository | Python AST analysis only; no execution or translation |
| vx.integration-attestation-json | Signed preflight envelope is described in repository documentation | JSON structure checks do not validate signatures or live providers |
| omega.math-expression | Bounded math expression utility exists in source | Allowlisted syntax only; this fabric does not evaluate the expression |
| vsm.protocol-markdown | Protocol description surface proposed | Markdown parser and formal transition semantics are not configured |
| vx.schema-yaml | Schema declaration surface proposed | YAML parser/validator is not configured |

The initial rows are a **working inventory**, not a claim that these names are adopted in project.genome. Each external or proposed anchor is labeled accordingly. Update only after checking the actual source-of-truth bytes and preserving provenance.

## Deterministic API contract

The Python API offers:

- **SystemLanguageFabric.from_file(path)** — load and validate the registry, authority boundaries, unique language/version pairs and registered targets.
- **languages()** and **resolve(language_id, version)** — enumerate declared entries; declaration does not imply connection or readiness.
- **analyze(language_id, source)** — produce a content hash, parser summary, structural result, error code and proof level.
- **plan_translation(...)** — return required gates and a fail-closed decision; it emits no target source when semantic/compiler adapters are missing.
- **plan_innovation(...)** — make a stable innovation packet linking grammar, semantics, IR, conformance, adversarial review, ARC-X and VAIXLNS admission gates.

Local command examples:

~~~bash
PYTHONPATH=src python -m vx_agents_fabric.system_language_fabric --config config/system_language_registry.v1.json --list

PYTHONPATH=src python -m vx_agents_fabric.system_language_fabric --config config/system_language_registry.v1.json --analyze-language vx.intent-json --source-file examples/vx-intent.example.json
~~~

Use an example file whose root contains **intent_id** and **goal** for the second command. The command's successful exit means the bounded syntax/structural check passed; it does not mean the language is semantically correct or the system is operational.

## Adapter contract before real compilation

A future adapter must declare its ID and semantic version, supported grammar and targets, maximum input/output sizes, deterministic behavior, effect permissions, dependency fingerprints, source-map generation, structured errors and conformance suite. It must not gain network, repository-write, deployment, paid-media or messaging access by implementing a parser interface.

Translation admission gates:

- the source parses and passes structural checks;
- both language versions are registered and compatible;
- the requested target is allowlisted;
- semantic models and lowering rules are defined;
- compiler adapter is explicitly configured;
- output provenance and source map are complete;
- round-trip/differential and adversarial tests pass reproducibly;
- ARC-X independently validates the evidence;
- canonical adoption is separately approved by VAIXLNS.

A model-generated grammar or code snippet is a PROPOSAL until the pipeline supplies those proofs.

## Security and no-loss rules

- No dynamic evaluation, code execution, dynamic imports, shell execution, network calls, provider credentials or generated-code execution.
- Bounded source size, JSON depth/node counts, AST node counts and expression operators.
- Reject duplicate registry identities and unregistered target languages.
- Hash exact UTF-8 input; never log source secrets in the analysis summary.
- Missing parser/compiler/semantic providers produce HOLD rather than inferred success.
- Preserve historical ideas and artifacts; this proposal must not delete, silently supersede or mutate canon.
- Keep real credentials and runtime receipts outside the repository.
- Keep this feature in a draft PR until review, canonical source retrieval and CI evidence are complete.

## Evidence state

The source module and tests in this pull request are proposed implementation artifacts. They become verified only for the exact commit and test commands that CI actually executes. Provider integration, formal language adoption, compilation correctness and production readiness are separate claims and remain unverified by this module.
