# Adversarial pressure-test ledger
Date: 2026-10-15

## Red-green findings
- CC Switch: .codex symlink escaped explicit live-home and modified outside fixture. Reject symlink components. Final: 56 passed, 18 skipped.
- MacroCLI: 10ms timeout plus 1s backoff ran backend 3 times over ~2.14s. Bound retries/backoff by monotonic deadline. Final: 92 passed, 4 skipped.
- n8n: server workflow ID ../escaped wrote outside backup root. Sanitize ID and name before joining paths. Offline final: 126 passed, 6 skipped. Live full E2E: 36 passed, 1 skipped (variables endpoint requires Enterprise).
- NotebookLM: Windows auth path with single backslashes failed to sanitize username. Correct regex. Final: 26 passed.
- Obsidian: 401 body echoed bearer secret into RuntimeError. Redact exact key from HTTP errors across five methods. Final: 60 passed, 7 skipped.

Each regression was observed failing before its fix; full logs and JUnit XML are included beside this ledger. git diff --check passed.

## n8n live validation
Created the temporary full-scope key codex-pressure-test-temporary after the user's confirmation. Ran the full E2E suite against the burner Render instance. Workflow CRUD and tag lifecycle fixtures were cleaned up; follow-up API list checks found zero matching leftover fixtures. Revoked the key in the UI. A subsequent request with that key returned HTTP 401. The temporary clipboard copy was cleared. The full live test log is n8n/n8n-live-e2e.log.

## Final test artifacts
cc-switch/cc-switch-final.log and XML; macrocli/macrocli-final.log and XML; n8n/n8n-final.log and XML plus n8n-live-e2e.log; notebooklm/notebooklm-final.log and XML; obsidian/obsidian-final.log and XML.

## Other limits
- Early MacroCLI lab errors (8) came from PATH lacking python and copied bytecode naming the source checkout. Removed generated pycache and set the isolated venv PATH; final suite passed.
- NotebookLM is not installed/authenticated in WSL; upstream login launches Windows host browser. See notebooklm-install-auth-research.md.
- Obsidian live API tests skipped; WSL has no executable/listener or API key.
- No active test credentials remain.
