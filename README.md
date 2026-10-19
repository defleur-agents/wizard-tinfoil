# Tinfoil — private staged connection

This candidate is not published, installed in Wizard's apps registry, or registered as a chat model. No Hermes configuration is written.

## Owner workflow
Open the private page, create an inference API key at https://dash.tinfoil.sh, paste it in the masked field, and Connect. The field clears immediately. Test rechecks the enclave and model catalog without inference. Disconnect deletes the app's key and rotates its local gateway credential. No route or MCP returns either credential.

**Important tested limitation:** Tinfoil `/v1/models` returns 200 even for a synthetic invalid key. Therefore Connect and Test **cannot authenticate the key**. They save the key after successful attestation and mark it `credentialStored: true`, `credentialVerified: false`, `status: not_connected`. Only a successful, separately authorized inference request marks it connected. We do not make a paid request just to validate a key or silently claim it works. Usage/billing are null; no admin key is requested.

## Transport and security boundary
The sole upstream implementation is the official Apache-2.0 `tinfoil==0.14.0` SDK (tag commit `9f2fe2756b910e55ae895d3a4cf64e6d76600ef0`). Its default verified transport authenticates the enclave before requests; no alternate OpenAI endpoint, measurement bypass or unverified fallback exists. Current default is attested EHBP; do not describe this as direct TLS-only API access. All Python dependencies are exactly version-pinned with hashes in requirements.lock; the Python base is pinned by digest. Sigstore caches and SDK user-cache secret live under the app's private /data, needed with its read-only root filesystem.

API key file and gateway token file use atomic replace, fsync, permissions 0600 and a 0700 directory. Keys are subprocess stdin only, never argv, URLs, logs, exceptions, MCP, HTML, GET output or browser storage. Worker stderr is discarded. Cache files use umask 077. State survives restarts. This is private app storage, not encryption at rest against host root.

Host and Origin allowlists prevent rebinding/cross-site writes. Browser writes require trusted Origin plus X-Wizard-Request: 1. MCP, connection status and inference are box-only and refuse forwarding/Cloudflare/Tailscale identity headers. Trusted shell origins can frame the app; the shipped appearance client currently trusts same-origin shell messages (as does the builder kit). Parent deployment must use same-origin routing or explicitly evolve that contract; this staged app is not exposed on the tailnet.

## Future agent integration (not performed)
`/v1/models` and `/v1/chat/completions` are OpenAI-compatible local endpoints requiring the independent app-local bearer credential stored as `/data/gateway-token.json`. Never use or hand Hermes the provider key. Future installer integration must provision the local credential without exposing it to an LLM or user-visible command output. Model IDs come from Tinfoil's verified catalog, not hardcoded invented names. Caller-supplied URLs, credentials and headers are forbidden. Streaming responses are currently buffered SSE (not real-time token streaming); non-streaming completions and tool-call fields pass through the official SDK. No `/v1/responses`, embeddings or audio gateway is implemented. Disconnect prevents future requests and rotates the bearer; an already admitted request may finish.

## Local build and tests
Use the installed builder: `wam check .`, `wam check . --proposal`, `wam install-local . --stage-only --run --port 18803`. For the private portable inline recipe, first build the same Dockerfile as `wizard-tinfoil-private:0.1.0`; it is deliberately not a public pullable image. `wam package-inline` resets port/image/memory to scaffold defaults: after regeneration reapply 18803, `wizard-tinfoil-private:0.1.0` and 512m. Do not use unmodified generated packaging.

`python -m unittest discover -s tests -v` exercises sanitized state, local authentication, forwarding/CSRF/DNS guards, persistence, disconnect, and injected SDK fail-closed behavior. Doubles prove application control flow, not Tinfoil cryptography. `tests/browser_qa.py` uses Playwright 1.63.0 and the real private stage. It uses only a synthetic key and free enclave/catalog reads, never paid inference. Its iframe is a test-only same-origin fixture, not an installed-shell launcher test. Captures and JSON are in the scratch tinfoil-evidence folder.

Official docs: https://docs.tinfoil.sh/sdk/python-sdk , https://docs.tinfoil.sh/sdk/overview , https://docs.tinfoil.sh/tutorials/coding-agents . Wizard contract: humanitylabs-org/wizard-os spec/AI_CONNECTIONS.md (read from GitHub during this build).
