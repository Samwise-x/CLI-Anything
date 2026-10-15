# Adversarial pressure-test ledger
Date: 2026-10-15

## Red-green findings
- CC Switch: .codex symlink escaped explicit live-home and modified outside fixture. Reject symlink components. Final: 56 passed, 18 skipped.
- MacroCLI: 10ms timeout plus 1s backoff ran backend 3 times over ~2.14s. Bound retries/backoff by monotonic deadline. Final: 92 passed, 4 skipped.
- n8n: server workflow ID ../escaped wrote outside backup root. Sanitize ID and name before joining paths. Final: 126 passed, 6 skipped.
- NotebookLM: Windows auth path with single backslashes failed to sanitize username. Correct regex. Final: 26 passed.
- Obsidian: 401 body echoed bearer secret into RuntimeError. Redact exact key from HTTP errors across five methods. Final: 60 passed, 7 skipped.

Each regression was observed failing before its fix; complete logs and JUnit XML are included beside this ledger. git diff --check passed.

## Test artifacts
cc-switch/cc-switch-final.log and XML; macrocli/macrocli-final.log and XML; n8n/n8n-final.log and XML; notebooklm/notebooklm-final.log and XML; obsidian/obsidian-final.log and XML.

## Limits
- Early MacroCLI lab errors (8) came from PATH lacking python and copied bytecode naming the source checkout. Removed generated pycache and set the isolated venv PATH; final suite passed.
- Live n8n cases skipped because WSL has no N8N_API_KEY or N8N_BASE_URL. Existing browser key is masked.
- NotebookLM is not installed/authenticated in WSL; upstream login launches Windows host browser. See notebooklm-install-auth-research.md.
- Obsidian live API tests skipped; WSL has no executable/listener or API key.
- No live account mutations performed. Fresh approval to create a temporary n8n key is pending.