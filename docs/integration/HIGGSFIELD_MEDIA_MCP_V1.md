# Higgsfield Media MCP — VAIXLNS/VX Integration Contract v1

**Status:** SPECIFIED / host connection and paid-generation tests pending  
**Canonical authority:** VAIXLNS  
**Orchestrator:** VX Agents Fabric  
**Target provider:** Higgsfield official MCP  
**Official MCP endpoint:** https://mcp.higgsfield.ai/mcp  
**Official setup page:** https://higgsfield.ai/mcp

## 1. Identity resolution

The requested name "Xfield" is treated here as a likely reference to **Higgsfield**, because the official Higgsfield website currently documents image/video generation and an official MCP connector. This interpretation is explicit and should be corrected if a different product was intended.

Use official Higgsfield surfaces only. Higgsfield identifies `higgsfield.ai`, `open.higgsfield.ai`, `docs.higgsfield.ai`, and `mcp.higgsfield.ai/mcp` as official surfaces. Avoid lookalike domains and third-party "Higgsfield" mirrors.

## 2. Connection shape

Higgsfield provides an official MCP intended to expose creative workflows to assistants including Claude. The documented connector endpoint is `https://mcp.higgsfield.ai/mcp`.

Claude Code remote MCP example (validate this shape against the installed Claude Code version before use):

```json
{
  "mcpServers": {
    "higgsfield": {
      "type": "http",
      "url": "https://mcp.higgsfield.ai/mcp"
    }
  }
}
```

Save the example as `.mcp.json` in the relevant project root only if the active host uses Claude Code's project MCP format. For Claude Desktop or another host, use its supported remote-MCP connection flow instead of assuming configuration formats are interchangeable.

This repository change does not install the connector into a user's local Claude environment, grant OAuth/session access, accept terms, or configure a paid account. After connection, inspect the tools actually exposed by the host and record the verified endpoint and status. Do not invent tool names or invoke undocumented methods.

## 3. Office routing

- **`Ω.MEDIA` — Creative Media Office:** translates a brief into a shot/image plan, composes a precise prompt, picks an appropriate provider/model from the connected catalog, manages generation jobs, and preserves output provenance.
- **`Ω.DESIGN` — Visual Design Intelligence Office:** analyses UX/design goals and permitted references; creates original visual directions rather than copying creators' finished work.
- **`Ω.ENG` — Engineering Office:** checks asset dimensions, formats, integration fit, accessibility and regression impact.
- **`Ω.PARENT` — independent review minds:** inspect goal compliance, source rights, consistency, safety and evidence.
- **VAIXLNS:** governs identity, brand rules, usage permissions, retention and promotion of approved assets to canonical project records.
- **VX:** routes the job and records states; a request to generate media is a paid external side effect, not a read-only tool call.
- **ARC-X:** checks the job receipt and generated artifacts; it cannot certify aesthetic excellence alone or claim a provider operation happened without a real receipt.

## 4. Supported workflow classes

Select from the actual tool/model catalog returned by the connected official MCP; these are workflow intents, not hard-coded method names:

1. **Text-to-image:** generate original concept art, UI moodboards, product scenes, illustrations or campaign frames.
2. **Image editing/variation:** edit or vary an asset only when the relevant official tool exists and the user is authorized to use the input.
3. **Text-to-video:** create a motion clip from a brief and directed shot specification.
4. **Image-to-video:** animate an authorized reference image; preserve the distinction between requested changes and elements that should remain stable.
5. **Story sequence:** design a shot list and generate candidate frames/clips with continuity notes; do not claim timeline editing or stitching unless the tools actually support it.
6. **Review/refine:** inspect framing, motion, temporal consistency, hands/faces/text, logos, unintended artifacts, and adherence to brand/accessibility constraints.

Higgsfield's Canvas is documented as a node-based environment in which prompts, images, and video generation can be connected as workflows. Use Canvas-specific workflow functionality only when the connected tools expose it.

## 5. Approval and cost gates

Before any paid generation request:

- Present the selected model/tool, expected quantity, duration/resolution/aspect ratio where applicable, known price/credit estimate, and a cost ceiling.
- Require explicit user approval for the cost ceiling and generation quantity unless a separate approved policy already covers that exact request.
- Do not enable automatic top-up, payment, publication, or external distribution through this routing contract.
- If exact price cannot be determined from the current provider catalog, return `HOLD_COST_UNKNOWN` and request a priced choice rather than guessing.
- Keep provider account credentials on the server/host secret store. Never commit them to the repository, prompt context, logs, or generated artifacts.
- Do not silently retry paid jobs after timeout. Check the real job/request status first to prevent duplicate billing.

The Higgsfield API documentation distinguishes API billing from website subscriptions/credits. The orchestration must report which billing surface is being used rather than assume website credits cover API requests.

## 6. Media task envelope

Each image/video request should record:

- `workflow_id`, `operation_id`, and idempotency key where supported;
- user intent, acceptance criteria and the approved maximum cost;
- source asset identifiers, permission/ownership basis and source hashes;
- provider endpoint identity, actual tool name, model ID/version and parameter schema;
- final prompt, negative prompt if the selected tool supports it, aspect ratio, duration, resolution, seed and reference inputs as applicable;
- approval reference and timestamp;
- provider request/job ID, status transitions, actual charge if exposed, and errors;
- output asset URL/ID, media type, dimensions/duration, content hash and retention classification;
- visual quality review, unresolved defects, user selection and promotion/adoption state.

Keep secrets out of the envelope. Limit access to sensitive or personal reference assets.

## 7. Lifecycle and fail-closed behaviour

`BRIEF → RIGHTS_CHECK → PROMPT_PLAN → MODEL_DISCOVERY → COST_ESTIMATE → USER_APPROVAL → GENERATE → FETCH_STATUS → INSPECT_OUTPUT → REVIEW → ACCEPT / REVISE / REJECT → ARCHIVE_EVIDENCE`

- Missing connection, missing tool, unclear license, unknown cost or missing approval => `HOLD`.
- Provider job failure => record the exact status/error; do not report success.
- A returned asset that fails brief or quality checks => `PARTIAL` or `REVISE`.
- The asset is `VERIFIED` only for specific verifiable properties (for example, file exists, media type parses, dimensions/duration match, content hash recorded, requested receipt exists). Visual quality approval is a separate review state.
- No automatic canonical adoption, publication, sharing or production deployment is allowed.
- Preserve failed generations and feedback as learning records according to retention policy; do not use provider assets to train internal models without an explicit rights basis.

## 8. Learning and prompt improvement

For each accepted, revised or rejected generation, capture a versioned record of:
- objective and use case;
- prompt-template version and model identifier;
- approved settings and known cost;
- scorecard across composition, subject fidelity, style coherence, technical correctness and brief adherence;
- human feedback and defect annotations;
- change made to the next prompt and the result of the next controlled attempt.

Compare alternatives under a fixed brief and explicit evaluation rubric. Do not label a prompt "best" from one unscored sample. Promote a prompt template only after repeatable evaluations and approval; retain previous versions and rollback links.

## 9. Acceptance tests

A live integration is not ready until tests demonstrate:
- the exact official MCP host is used;
- tool discovery reports the actual available tools;
- missing/unavailable generation tools cause HOLD;
- unknown costs and unapproved paid requests are blocked;
- secrets never appear in logs, prompts or repository content;
- job polling and retries do not duplicate paid submissions;
- returned image/video artifacts are checked and content-hashed;
- failed jobs and incomplete evidence cannot be marked successful;
- output rights and retention metadata are retained;
- generation does not publish, merge or modify canonical authority data.

## 10. Current status

This contract and example configuration do not prove that a local Claude session is connected, that credentials or provider billing are configured, or that an image/video has been generated. Those claims require host-side connection evidence and an actual provider job receipt.
