# CLI-Anything adversarial audit - batch A

Date: 2026-10-15
Checkout: `/home/master_j/work/cli-anything-audit-a`
Branch: `audit/remaining-a`
Commit: `d7dccb551dc560db418db0483b930dff8a68a82b`
Repo-local `AGENTS.md`: none found.
Method: CLI-Anything `references/HARNESS.md` and `references/commands/test.md`; Superpowers TDD for each fix. No live accounts, external services, or credentials used. All commands and dependency changes were WSL-only.

## Test matrix

Each harness was run with `python -m pytest -v --tb=short <harness>/agent-harness/cli_anything/<package>/tests` using `/home/master_j/work/cli-anything-hardened/.venv/bin/python`.

| Harness | Result | Backend gate / security review |
|---|---:|---|
| 3MF | 0 collected, 1 collection error | Missing SciPy import dependency. `trimesh`, `numpy`, and `mcp` were installed in the WSL venv; SciPy wheel download was stopped due to slow transfer. ZIP/XML/geometry handling reviewed but tests could not collect. |
| QGIS | 22 setup errors | PyQGIS and `qgis_process` absent in WSL. Project paths, sessions, and export overwrite/delete reviewed. `run_process_json` has no subprocess timeout. |
| adguardhome | 39 passed | No live service. Found stored Basic Auth password file had mode 0644; now saves at 0600. HTTP requests already have 10-second timeouts. |
| anygen | 47 passed, 6 skipped | Six live API tests skipped because `ANYGEN_API_KEY` is unset. Found response error token reflection, server filename traversal, and dangling symlink escape; fixed all three. |
| audacity | 161 passed, 7 failed | SoX is absent; failures are SoX availability or workflows requiring SoX. SoX commands use finite timeouts and argv. |
| blender | 226 passed, 13 failed | Blender executable absent; failed render, preview, and backend tests need it. Render commands have timeouts; detached live processes are lifecycle-managed. |
| browser | 196 passed, 11 skipped, 1 warning | DOMShell E2E disabled/unavailable. Found decimal IPv4 loopback bypass when opt-in private-network blocking is enabled; fixed. Blocking remains opt-in; hostname DNS/rebinding is not verified. |
| calibre | 41 passed, 21 skipped | `calibredb` absent; skipped E2E requires Calibre. Reviewed argv and finite subprocess timeouts. |
| chromadb | 39 passed, 14 skipped | ChromaDB server unavailable at `localhost:8000`; all live-server tests skipped. Added 30-second timeout to every REST call. |
| cloudanalyzer | 11 passed, 3 skipped | `ca` (CloudAnalyzer) absent for E2E. Local config/baseline changes and overwrite behavior are covered; no external cloud access. |
| cloudcompare | 57 passed, 29 failed, 2 errors | CloudCompare executable absent; backend checks and processing tests fail/setup-error on that gate. `run_cloudcompare` has no subprocess timeout. |
| comfyui | 73 passed | No live ComfyUI service. API requests have finite timeouts; error handling and queue mutations reviewed. |
| dify-workflow | 8 passed, 3 errors | Upstream `dify_workflow.cli` package/command absent; wrapper E2E cannot start. Wrapper uses argv, but subprocess call has no timeout. |
| drawio | 142 passed, 3 skipped | draw.io absent for export E2E. XML/session/export paths reviewed; export subprocess has caller-set timeout. |
| eez-studio | 14 passed, 1 skipped | Live test requires `EEZ_STUDIO_RUN_LIVE_BACKEND=1` and built `EEZ_STUDIO_SOURCE`. Node subprocesses have timeouts; project mutations reviewed. |
| eth2-quickstart | 18 passed, 3 skipped | E2E requires `ETH2QS_E2E_REPO_ROOT` real checkout. Config values shell-quoted; node install/exposure operations require `--confirm`. Wrapper subprocess has no timeout. |

Verbose per-harness logs are in `/home/master_j/work/cli-anything-pressure-lab/pressure-evidence/upstream/batch-a/verified/`. Any credential-looking values in test fixtures are synthetic only.

## Red/green evidence

| Finding | Regression and observed red | Fix and green verification |
|---|---|---|
| ChromaDB calls could wait indefinitely | `test_heartbeat_uses_finite_request_timeout`: expected timeout 10 (set to 30 after review); actual was `None`. Existing call assertions also failed when timeout was introduced. | Added timeout 30 to every GET/POST/DELETE endpoint. Full suite: 39 passed, 14 server skips. Latest log: `verified/chromadb.log`. |
| AnyGen API key could be reflected by server error | `test_create_http_error_redacts_reflected_auth_token`: raised error contained fixture `sk-secret-reflected` (fake test value). | Redact raw HTTP response, API-provided error, and task failure fields against raw and Bearer key forms. Full suite: 47 passed, 6 API-key skips. Latest log: `verified/anygen.log`. |
| AnyGen server filename traversal | `test_download_file_keeps_server_filename_inside_output_dir`: `../escaped.txt` resolved outside the requested directory. | Normalize remote filename to a single path component, accepting either slash convention. Same full AnyGen suite passed. |
| AnyGen dangling symlink escape | `test_download_file_does_not_follow_dangling_output_symlink`: outside target was created. | Treat existing and dangling symlinks as occupied output names. Same full AnyGen suite passed. |
| AdGuardHome config credentials were group/other-readable | `TestProject::test_save_config`: observed 0644 (`st_mode & 077 == 064`). | Save config mode 0600. Full suite: 39 passed. |
| Browser filter allowed alternate numeric loopback | `TestPrivateNetworkBlocking::test_decimal_ipv4_loopback_not_accepted_when_private_block_enabled`: `http://2130706433` returned valid. | Parse IP literals and legacy numeric IPv4 forms; reject non-global addresses when private blocking is enabled. Full suite: 196 passed, 11 skipped, 1 warning. |

Focused tests failed before their corresponding fixes and passed afterward. Final full-suite logs for all 16 harnesses are saved under `verified/`; the exact matrix above records collection errors, backend failures, and skips separately.

## Remaining pressure gates

- Local backend integration is still unavailable for 3MF (SciPy dependency), QGIS/PyQGIS, Audacity/SoX, Blender, Browser/DOMShell, Calibre, ChromaDB, CloudAnalyzer, CloudCompare, Dify, draw.io, EEZ Studio, and eth2-quickstart. Specific test gates are above.
- Static review found blocking subprocess calls without timeouts in QGIS `run_process_json`, CloudCompare `run_cloudcompare`, Dify `run_dify_workflow`, and eth2-quickstart `_run`. Their valid maximum run durations are not documented, so no arbitrary timeout was introduced.
- Browser's private-network check is disabled unless `CLI_ANYTHING_BROWSER_BLOCK_PRIVATE` is enabled. The alias fix is covered; hostname resolution and browser-side DNS rebinding were not tested because DOMShell was unavailable.
- Some suites report absent backends as test failures or setup errors rather than skips (Audacity, Blender, CloudCompare, QGIS, Dify); those are environment gates, not claimed product bugs.

`git diff --check` passed. Only source/tests for AnyGen, AdGuardHome, Browser, and ChromaDB were changed and committed on `audit/remaining-a` at `d7dccb551dc560db418db0483b930dff8a68a82b`. The commit was not pushed.
