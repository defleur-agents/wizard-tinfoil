---
wizard: 0.2
id: wizard-tinfoil
name: Tinfoil
type: external
category: system
version: 0.1.0
summary: Connect Tinfoil with a server-held API key and verified enclave transport.
license: GPL-3.0-only
source: https://github.com/oscarhenrycollins/wizard-tinfoil
runtime:
  kind: runtipi
  config: runtipi/config.json
  compose: runtipi/docker-compose.yml
api:
  port: 18804
  path: /api
  spec: openapi.json
mcp:
  path: /mcp
  port: 18804
  transport: streamable-http
skill: skill/SKILL.md
view:
  path: /
  port: 18804
  source:
    path: web
    build: python3 app/build_view.py
    dist: web
provides: [ai-connection, tinfoil-api-key]
system: true
uses: []
needs: []
health: /healthz
---

# Tinfoil
Owner-only installed app, not publicly listed. The source link identifies the official SDK dependency, not a published Wizard app repository. Connect / Test / Disconnect own one Tinfoil login. The API key is never returned. Read-only MCP uses wizard.ai-connection/1. Chat model registration is deliberately not performed.
