# Prompt Office Runtime Preflight — Signed Integration Evidence v1

**Status:** IMPLEMENTED LOCALLY IN REPOSITORY / LIVE PROVIDER STATUS NOT YET ATTESTED  
**Owner:** VAIXLNS  
**Runtime authority:** VX  
**Verification policy:** default-deny  
**Module:** `src/vx_agents_fabric/integration_preflight.py`

## 1. Purpose

Routing declarations tell the orchestrator which integrations are intended. They do not prove a skill is installed, a remote MCP server is reachable, an API credential is valid, a WhatsApp webhook has been verified, or a paid media job succeeded.

The preflight command checks fresh, signed host-side evidence for six integrations:
- `SUPERPOWERS` — agent-host software-development skills.
- `UI_UX_PRO_MAX` — design-system skill.
- `HIGGSFIELD` — official remote MCP for image/video generation.
- `WHATSAPP_BUSINESS_CLOUD_API` — official Meta business messaging API.
- `PINTEREST_API` — optional OAuth-authorized, read-only visual-reference API route.
- `DRIBBBLE_API` — optional OAuth-authorized, read-only visual-reference API route.

It never makes an external network call, sends a message, generates media, charges credits, changes a repository, or mutates canonical data.

## 2. Runtime evidence directory

Attestation files are named by stable provider identity:

```text
runtime/integration-attestations/
  superpowers.json
  ui_ux_pro_max.json
  higgsfield.json
  whatsapp_business_cloud_api.json
  pinterest_api.json
  dribbble_api.json
```

Do not commit signed production attestations or real account metadata. Use a deployment-owned private path and restrictive filesystem permissions. Evidence files contain identifiers, timestamps, capability names and hashes only; never put tokens, app secrets, phone numbers or private message bodies in the envelope.

## 3. Trusted attestation contract

Each runtime envelope contains:
- `schema_version`, `provider_id`, and `integration_type`;
- the host/endpoint actually probed and timezone-aware `observed_at` / `expires_at`;
- `probe_result` and normalized `capabilities`;
- exact tool/skill identifiers in `available_operations`;
- evidence records (`kind`, SHA-256, optional evidence URI);
- `signature_hmac_sha256`.

The signature is HMAC-SHA256 over canonical JSON without the signature field. The key is read only by a trusted deployment-side probe and the runtime auditor through `VX_INTEGRATION_ATTESTATION_HMAC_KEY`; it must be at least 32 bytes. Never expose this key to a language model, end-user input, normal tool context, or repository.

A model must not create its own attestation. Only a trusted host probe should sign after inspecting the actual installed skill manifest, the remote MCP `initialize` / `tools/list` result, or real WhatsApp API/webhook test receipts. A valid signature proves that the trusted probe's record has not changed; it does not independently prove that the probe itself was honest or that generated content is good.

## 4. Provider-specific gates

### Superpowers
Requires the actual skill manifest and these normalized capabilities: brainstorming, writing plans, test-driven development, systematic debugging, verification before completion. Operational status also requires a recorded invocation receipt.

### UI/UX Pro Max
Requires the actual manifest and version metadata. Operational status requires a sample design output that can be reviewed. A version recorded in the routing JSON is not installation evidence.

### Higgsfield
Only accepts the official endpoint `https://mcp.higgsfield.ai/mcp`. Connected status requires a real MCP initialization receipt, tools-list receipt, and discovered image/video capabilities. Operational status additionally requires both image and video job receipts and separate approval/cost-ceiling evidence for each paid generation. Since generation through MCP consumes credits, any sample job must carry explicit user approval and a cost ceiling before it is submitted; the preflight auditor does not submit it.

Official setup and billing information: https://higgsfield.ai/mcp and https://higgsfield.ai/creator-hub/help-center/integrations/what-is-higgsfield-mcp

### WhatsApp Business Cloud API
Only accepts HTTPS endpoints at `graph.facebook.com` with an explicit versioned API path. Connected status requires a business-account check and verified webhook receipt, plus outbound, inbound and delivery-status capabilities. Operational status additionally requires inbound/outbound test receipts, a delivery-status webhook receipt, a negative test proving invalid webhook signatures are rejected, and a negative test proving an outbound message without required consent is blocked.

Use the official API docs: https://developers.facebook.com/docs/whatsapp/cloud-api/overview

## 4.1 Pinterest API

Only accepts HTTPS on `api.pinterest.com` with a v5 path. Connected status requires OAuth scope evidence and an authenticated identity probe. Operational status also requires a permitted reference sample and an attribution record. Pinterest API authorization and scope availability depend on the registered app and provider approval; this preflight does not scrape boards or fetch references itself.

Official authentication and API reference:
- https://developers.pinterest.com/docs/getting-started/set-up-authentication-and-authorization/
- https://developers.pinterest.com/docs/api/v5/pinterst/

Do not use Pinterest materials for AI/ML training or improvement without express permission. Keep source/attribution data and do not store raw media unless authorized.

## 4.2 Dribbble API

Only accepts HTTPS on `api.dribbble.com` with a v2 path. Connected status requires OAuth scope evidence and an authenticated identity probe. Operational status also requires a permitted reference sample and an attribution record. Confirm that your registered application and account still have the desired API access before enabling the route; public browsing and API authorization are different access paths.

Official API and OAuth documentation:
- https://developer.dribbble.com/v2/
- https://developer.dribbble.com/v2/oauth/

Use read-only public scopes for visual research. Never request upload/write scopes for discovery-only tasks. Respect creator rights; capture source links and learn abstract principles rather than copying a creator's complete work.

## 5. States

- `NOT_CONFIGURED`: no runtime attestation exists.
- `ATTESTATION_KEY_NOT_CONFIGURED`: attestation exists but the trusted signing key is absent.
- `INVALID_ATTESTATION`: schema, signature, endpoint or timestamps are invalid.
- `EXPIRED`: attestation is expired or older than the 24-hour freshness window.
- `PROBE_FAILED`: the trusted probe reported failure.
- `INCOMPLETE`: connection requirements/capabilities are missing.
- `CONNECTED_NOT_OPERATIONAL`: connection and base evidence pass but one or more required acceptance receipts are missing.
- `OPERATIONAL`: fresh signed evidence satisfies all integration-specific operational gates.
- `NOT_DECLARED`: the canonical routing registry does not declare the integration.

No state is promoted by prose or by the integration's own status flag alone.

## 6. Run a read-only preflight

With the package available on `PYTHONPATH`:

```bash
PYTHONPATH=src python -m vx_agents_fabric.integration_preflight \
  --config config/office_skill_routing.v1.json \
  --attestation-dir runtime/integration-attestations
```

The report is JSON. Exit code `0` means all declared integrations passed operational preflight; exit code `2` means a missing/incomplete/expired/failed integration remains; exit code `4` indicates input or output configuration error. Missing integration receipts are expected to produce `PARTIAL`, not failure masquerading as success.

The default freshness window is 24 hours. Refresh probes after a provider change, plugin update, credential rotation, webhook/configuration change or host update.

## 7. Implementation boundaries

The included module is a read-only auditor and HMAC verifier, not an installer, OAuth client, MCP client, WhatsApp server or media-generation adapter. Its job is to make unverified integrations visible and fail closed. Provider-specific host probes, credential setup, account authorization and real sample operations must be connected separately.

## 8. Required tests

Tests verify:
- missing attestations never claim connectivity;
- a signature mismatch or wrong endpoint is rejected;
- stale or timezone-invalid envelopes fail closed;
- Higgsfield remains connected-but-not-operational without actual image and video receipts;
- WhatsApp remains connected-but-not-operational without inbound, approved outbound and status-webhook receipts;
- a missing skill capability prevents the connected state;
- preflight makes no external calls and cannot send messages, charge credits or mutate canonical state.
