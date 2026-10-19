# Tinfoil — owner-only Wizard connection

Installed from this private repository with `wam install oscarhenrycollins/wizard-tinfoil`. Not publicly listed. The app does not edit Hermes configuration; model registration is a separate owner-approved integration with the same agent.

## Owner workflow
Open Tinfoil in the Wizard launcher, create an inference API key at https://dash.tinfoil.sh, paste it in the masked field, and Connect. The field clears immediately. Test rechecks the enclave and model catalog without inference. Disconnect deletes the provider key; the independent box-only gateway bearer remains stable so reconnecting does not break the agent's registration. No page, GET or MCP returns either credential.

**Important tested limitation:** Tinfoil `/v1/models` accepts a synthetic invalid key. Connect and Test therefore **cannot authenticate the key**. They save it only after successful attestation and mark it `credentialStored: true`, `credentialVerified: false`, `status: not_connected`. Only a successful separately authorized inference request marks it connected. No paid request is made for key validation. Usage/billing stay null; no admin key is requested.

## Transport and security boundary
The sole upstream implementation is official Apache-2.0 `tinfoil==0.14.0` (tag commit `9f2fe2756b910e55ae895d3a4cf64e6d76600ef0`). Its verified transport authenticates the enclave before requests; no alternate OpenAI endpoint, measurement bypass or unverified fallback exists. Current default is attested EHBP. Dependencies have exact versions and hashes in requirements.lock; Python base is digest-pinned.

Provider key and local bearer use atomic replace, fsync and 0600 files beneath a 0700 app-owned `/data/private` directory. HOME and XDG caches also live there, allowing Sigstore verification with a read-only root filesystem. This is private app storage, not encryption at rest against host root. Upstream keys reach the SDK worker over stdin only, never argv, URLs, logs, exceptions, MCP, HTML, GET output or browser storage; worker stderr is discarded.

Host/Origin allowlists prevent DNS rebinding and cross-site writes. Browser mutations require an approved Origin and `X-Wizard-Request: 1`. `/api/status` is the sanitized browser route. MCP, `/api/connection` and inference are box-only and refuse forwarding/Cloudflare/Tailscale identity headers. Same-origin shell paths support framing and the shipped appearance handshake. The production listener binds only host loopback at 18804; staging at 18803 is independent.

## Same-agent integration
`/v1/models` and `/v1/chat/completions` are local OpenAI-compatible routes requiring `/data/private/gateway-token.json`. Provision this independent bearer process-to-process, without printing it or giving Hermes the provider key. A bearer can be registered before any provider key exists: inference then returns 409 without an upstream call. Model IDs must come from the attestation-verified catalog, never invented names. Caller-supplied URLs, credentials and headers are forbidden.

Streaming is currently **buffered SSE**, not real-time token streaming. Tool-call fields and non-streaming completions pass through the official SDK. No Responses, embedding or audio gateway is implemented. Disconnect blocks new requests; already admitted requests may finish. The `chatIntegration` status field is app-local and does not inspect external Hermes registration.

## Packaging and verification
Production uses a private owner-host loopback registry image plus the dependency-bearing inline recipe. Runtipi removes local-only tags during installation, so a registry-pullable reference is required. The recipe uses uid 1000, a read-only root filesystem, dropped capabilities, no-new-privileges, and only its own named private data volume. Runtipi recursively chmods bind-mounted app-data during lifecycle actions; the named volume keeps credential permissions outside that operation. Only amd64 has been exercised; no multi-architecture claim is made.

`wam check . --proposal` passes. Run the six unit tests in the actual image with the entire source mounted at `/qa`, then `python -m unittest discover -s /qa/tests -v`; these cover local auth, safe state, CSRF/DNS/forwarding guards, persistence, SDK use, and real SDK attestation rejection before HTTP. Doubles are application control-flow tests, not cryptographic proof.

Production checks exercised the actual Wizard launcher iframe at phone and desktop widths on all three owner shell ports: masked input, successful real free attestation/catalog read with an explicitly synthetic invalid key, pending authentication, Test, Disconnect, no page errors or horizontal overflow, and live hosted theme handshake. The synthetic key was removed. Restart preserved the independent bearer and left provider credentials absent. No paid inference was performed.

Official docs: https://docs.tinfoil.sh/sdk/python-sdk , https://docs.tinfoil.sh/sdk/overview , https://docs.tinfoil.sh/tutorials/coding-agents . Wizard contract: `humanitylabs-org/wizard-os` `spec/AI_CONNECTIONS.md`.
