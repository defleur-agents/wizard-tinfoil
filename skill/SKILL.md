---
name: wizard-tinfoil
description: Use when checking the Tinfoil private AI connection.
---
Call connection_status on this app's MCP to read Tinfoil status. It is read-only and never returns keys.
The owner connects or disconnects on the Tinfoil page; never ask for an API key in chat.
After Connect the app adds a private Tinfoil model to the agent's model list (`chatIntegration: registered`); the
owner picks it in the model picker. Not connected means the owner must use that page.

- `billing_summary` (read-only): Tinfoil spend and credit left, in USD minor units. If `adminKeyStored` is false, tell the owner to add a billing key on the Tinfoil app page. Never ask for keys in chat.
