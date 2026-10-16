# Governance application
The declaration is not active until applied remotely by a repository administrator. Seed CodeQL results on main and the proposal first, then run tools/apply_github_governance.py from a trusted maintainer environment and verify the installed ruleset through GitHub's API.

This maintainer workflow uses deterministic CI, CodeQL merge protection, and a separate local read-only evaluator. PRs and resolved conversations are required; human approvals are optional to honor autonomous operation. No token is available to sandbox workers. Existing upstream CODEOWNERS entries lack write access on this fork and therefore do not provide enforcement.

Auto-merge remains subject to required checks. The dependency workflow requests auto-merge only for Dependabot PRs in this repository after successful Governance CI; it never executes proposed code with a write token. Any model endpoint outage leaves goals incomplete. GH_TOKEN/GITHUB_TOKEN with administration permission is needed only for applying server settings, not OpenCode free-model authentication. Never pass that token into a goal worker.
