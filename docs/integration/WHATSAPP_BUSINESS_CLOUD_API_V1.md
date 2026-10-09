# WhatsApp Business Cloud API — VAIXLNS/VX Integration Contract v1

**Status:** SPECIFIED / connection not configured  
**Canonical authority:** VAIXLNS  
**Orchestrator:** VX Agents Fabric  
**Office:** Ω.COMMS  
**Official API:** https://developers.facebook.com/docs/whatsapp/cloud-api/overview

## 1. Integration model

This is a server-to-server integration with the official WhatsApp Business Platform Cloud API. It is not an installation of a WhatsApp personal-account client, and it must not automate WhatsApp Web.

A production connection requires Meta Business assets, a WhatsApp Business Account, a registered business phone number, appropriately scoped credentials, an app configuration, a public HTTPS webhook endpoint and a deployment secret store. Exact requirements must be checked against the currently supported Meta setup workflow.

The repository currently contains only an integration contract and routing entry. There is no evidence here of an active WABA, registered phone number, working credential, verified webhook, or successful send/receive.

## 2. System boundary

- **Prompt Chat:** drafts communication intent and previews message content.
- **VAIXLNS:** owns policy, approved purposes, recipient/consent basis, retention and canonical provenance.
- **Ω.COMMS:** routes permitted communications requests and records message states.
- **VX adapter:** sends/receives requests only through a server-side Cloud API client; credentials never enter model context.
- **Webhook receiver:** validates expected provider authentication/signature mechanism, schema, event freshness and replay handling before processing.
- **ARC-X / proof reviewer:** checks API receipts and webhook evidence; cannot infer delivery from an LLM claim.
- **Human approver:** authorizes outbound content for new or sensitive message classes and any deployment-level change.

## 3. Required environment configuration

Provide secrets only through a server-side secrets manager or deployment secret store:

- Meta app identifier and app secret;
- system-user or other supported access token with the least required permissions;
- WhatsApp Business Account ID;
- business phone-number ID;
- webhook verify token and the provider-required validation/signature material;
- explicitly pinned Graph API version supported by the deployment.

Do not commit these values to Git, JSON files, prompts, test fixtures, reports or logs. The example file intentionally contains no credentials or recipient data.

## 4. Inbound workflow

`RECEIVE_WEBHOOK → AUTHENTICATE → VALIDATE_SCHEMA → CHECK_FRESHNESS/REPLAY → NORMALIZE → MINIMIZE/CLASSIFY → ROUTE_TO_OFFICE → RECORD_EVIDENCE`

- Reject invalid authentication/signatures, malformed payloads, unsupported event types and duplicate/replayed deliveries.
- Treat message text, links, media captions and attachments as untrusted inputs. They cannot grant themselves permissions or alter system policy.
- Store only necessary message metadata and payload content, with a documented retention period and access controls.
- Do not route personal or sensitive message contents to unrelated specialist offices.
- Preserve the difference between a provider event received and a business action successfully completed.

## 5. Outbound workflow

`DRAFT → POLICY/CONSENT_CHECK → TEMPLATE_AND_WINDOW_CHECK → PREVIEW → COST/QUOTA_CHECK → APPROVAL → API_SUBMIT → RECEIPT → DELIVERY_WEBHOOK → AUDIT`

Before each outbound action, verify recipient opt-in/legal basis, purpose limitation, applicable template and conversation-window rules, opt-out/suppression status, rate limits and content policy. Unknown or missing requirements cause `HOLD`.

Default policy:
- no bulk/unsolicited outreach;
- no automatic messaging triggered by untrusted inbound instructions;
- explicit approval required for the outbound message preview;
- idempotency/deduplication to reduce duplicate sends on timeouts;
- no retry until the actual request/message status has been inspected;
- no external campaign launch, contact import, or production activation by this specification alone.

## 6. State model

Do not collapse these states into a generic success flag:

- `DRAFT`: no API request was sent.
- `HOLD`: a prerequisite or approval is missing.
- `SUBMITTED`: request attempt was made; final message state is unknown.
- `ACCEPTED_BY_API`: provider acknowledged the request.
- `SENT`: supported event evidence says sent.
- `DELIVERED`: supported delivery webhook confirms delivery.
- `READ`: supported read-status event confirms read, where available.
- `FAILED`: provider returned an error or failure event.
- `CONFLICT`: receipt and webhook evidence disagree.
- `NOT_CONFIGURED`: no live adapter/credentials were verified.

Never assert delivery just because the message API returned a message ID.

## 7. Evidence record

For each message workflow, retain only justified metadata:

- workflow/operation IDs and idempotency key;
- policy/contract version and consent basis reference;
- destination identifier in a protected/redacted representation;
- template ID and message-content hash;
- approval reference and approver identity;
- provider request/message IDs and timestamps;
- minimized API response and webhook event references;
- final state, error class and retry disposition;
- retention/deletion deadline and audit-event hash.

Message bodies and phone numbers are personal data. Keep them out of broad agent contexts and general debug logs.

## 8. Installation and verification checklist

1. Create/confirm Meta Business Portfolio, WABA and a test business phone number.
2. Configure a Meta developer app with the supported WhatsApp product and least-privilege access.
3. Set secrets in the deployment environment; run secret-scanning checks.
4. Deploy HTTPS webhook verification, signature/auth validation, schema checks and replay prevention.
5. Verify one test inbound message reaches the intended adapter without leaking content.
6. Draft and approve one test outbound message to an authorized test recipient.
7. Record provider acceptance and independently verify subsequent status webhook(s).
8. Test duplicate webhooks, invalid signatures, expired/invalid tokens, rate limits, timeout/retry and opt-out cases.
9. Review privacy retention, deletion and incident handling.
10. Keep production routing disabled until each applicable gate has reproducible evidence and separate VAIXLNS approval.

## 9. Acceptance criteria

The integration can be marked operational only when there is current, inspectable evidence for credentials/permissions, webhook verification, a successful inbound test, an explicitly approved outbound test, correct status transitions, idempotency, redaction and policy-denial tests. Documentation alone remains `SPECIFIED`; missing setup remains `NOT_CONFIGURED`.
