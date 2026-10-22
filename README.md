# Tinfoil: private AI for your Wizard

Install from the Wizard App Store (`wam install wizard-tinfoil`). Open Tinfoil, paste an API key from https://dash.tinfoil.sh and tap Connect. Your agent gets a private Tinfoil model in its model picker; your default model does not change. Disconnect removes the key and the model.

Image source and CI: `humanitylabs-org/wizard-app-store` `images/wizard-tinfoil` (published only after its tests pass, amd64 and arm64).

## Agent registration
On Connect (and on start, if a key is saved) the app adds itself to the agent through the stock Hermes dashboard API (`POST /api/providers/custom-endpoints`, `make_default: false`, one chat model: Kimi K3 when available). Hermes receives only this box's local gateway token, never the Tinfoil key. The dashboard login is filled in by the App Manager from the Hermes Agent app (fresh installs) or the host dashboard (alongside installs). If the agent can't be reached, the key is still saved and status shows `chatIntegration: unavailable`; it retries on the next Test or restart.

The gateway accepts the request fields agents send (reasoning effort, thinking, cache key) and maps Kimi K3's unsupported `medium` effort to `high`.

## Owner workflow
Open Tinfoil in the Wizard launcher, create an inference API key at https://dash.tinfoil.sh, paste it in the masked field, and Connect. The field clears immediately. Test rechecks the enclave and model catalog without inference. Disconnect deletes the provider key; the independent box-only gateway bearer remains stable so reconnecting does not break the agent's registration. No page, GET or MCP returns either credential.

**Important tested limitation:** Tinfoil `/v1/models` accepts a synthetic invalid key. Connect and Test therefore **cannot authenticate the key**. They save it only after successful attestation and mark it `credentialStored: true`, `credentialVerified: false`, `status: not_connected`. Only a successful separately authorized inference request marks it connected. No paid request is made for key validation. Usage stays null unless the owner adds the optional billing key below.

## Billing (optional admin key)
On the Tinfoil page, under Billing, the owner can paste a Tinfoil **admin key** (Dashboard → Admin Keys; unscoped, because Tinfoil refuses billing to scoped keys). It is checked against Tinfoil before it is saved, kept 0600 in this app's private volume, and only ever used for `GET /api/auth/context` and `GET /api/billing/{usage,transactions}`: never to create, change or delete keys. No route, MCP tool or log returns it. `/api/connection` then reports `usage.paid = {type:'credits', balanceMinor, limitMinor (last top-up), usedMinor (this period)}`, which Home draws as a fuel gauge. Balance = credit top-ups minus all-time spend; with no recognisable top-up only spend is reported. Remove billing key deletes it.

## Transport and security boundary
The sole upstream implementation is official Apache-2.0 `tinfoil==0.14.0` (tag commit `9f2fe2756b910e55ae895d3a4cf64e6d76600ef0`). Its verified transport authenticates the enclave before requests; no alternate OpenAI endpoint, measurement bypass or unverified fallback exists. Current default is attested EHBP. Dependencies have exact versions and hashes in requirements.lock; Python base is digest-pinned.

Provider key and local bearer use atomic replace, fsync and 0600 files beneath a 0700 app-owned `/data/private` directory. HOME and XDG caches also live there, allowing Sigstore verification with a read-only root filesystem. This is private app storage, not encryption at rest against host root. Upstream keys reach the SDK worker over stdin only, never argv, URLs, logs, exceptions, MCP, HTML, GET output or browser storage; worker stderr is discarded.

Host/Origin allowlists prevent DNS rebinding and cross-site writes. Browser mutations require an approved Origin and `X-Wizard-Request: 1`. `/api/status` is the sanitized browser route. MCP, `/api/connection` and inference are box-only and refuse forwarding/Cloudflare/Tailscale identity headers. Same-origin shell paths support framing and the shipped appearance handshake. The production listener binds only host loopback at 18804; staging at 18803 is independent.

## Same-agent integration
`/v1/models` and `/v1/chat/completions` are local OpenAI-compatible routes requiring `/data/private/gateway-token.json`. Provision this independent bearer process-to-process, without printing it or giving Hermes the provider key. A bearer can be registered before any provider key exists: inference then returns 409 without an upstream call. Model IDs must come from the attestation-verified catalog, never invented names. Caller-supplied URLs, credentials and headers are forbidden.

Streaming is currently **buffered SSE**, not real-time token streaming. Tool-call fields and non-streaming completions pass through the official SDK. No Responses, embedding or audio gateway is implemented. Disconnect blocks new requests; already admitted requests may finish. The `chatIntegration` status field is app-local and does not inspect external Hermes registration.

## Packaging and verification
The recipe uses uid 1000, a read-only root filesystem, dropped capabilities, no-new-privileges, and only its own named private data volume. Runtipi recursively chmods bind-mounted app-data during lifecycle actions; the named volume keeps credential permissions outside that operation. Images are published for amd64 and arm64.

`wam check . --proposal` passes. Run the six unit tests in the actual image with the entire source mounted at `/qa`, then `python -m unittest discover -s /qa/tests -v`; these cover local auth, safe state, CSRF/DNS/forwarding guards, persistence, SDK use, and real SDK attestation rejection before HTTP. Doubles are application control-flow tests, not cryptographic proof.

Production checks exercised the actual Wizard launcher iframe at phone and desktop widths on all three owner shell ports: masked input, successful real free attestation/catalog read with an explicitly synthetic invalid key, pending authentication, Test, Disconnect, no page errors or horizontal overflow, and live hosted theme handshake. The synthetic key was removed. Restart preserved the independent bearer and left provider credentials absent. No paid inference was performed.

Official docs: https://docs.tinfoil.sh/sdk/python-sdk , https://docs.tinfoil.sh/sdk/overview , https://docs.tinfoil.sh/tutorials/coding-agents . Wizard contract: `humanitylabs-org/wizard-os` `spec/AI_CONNECTIONS.md`.
