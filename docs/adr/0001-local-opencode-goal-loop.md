# ADR 0001: Local OpenCode goal loop and remote verification
- Status: Accepted
- Date: 2026-10-15
## Context
The autonomous goal loop is for maintainers in WSL2, not public contributors. Self-hosted workstation runners expose a host to untrusted pull request code. Promotional models have separate data terms.
## Decision
Use OpenCode CLI v2 project configuration, local governance hooks, bounded goal/resume commands, durable evidence, and a read-only evaluator. Public CI runs on GitHub-hosted Ubuntu. Rulesets and auto-merge are remote administrator controls; committed files state intent but do not enforce settings.
## Consequences
Model responses are not deterministic verification. Keep sensitive data out of free endpoints. Local hooks provide early feedback. A Docker sandbox holds policy and evidence read-only, omits host credentials, isolates execution from the host, and runs verification without network access. CI and server-side rules govern integration. No Windows/macOS execution.
