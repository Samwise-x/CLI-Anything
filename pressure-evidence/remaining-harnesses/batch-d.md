# CLI-Anything adversarial audit: batch D

Date: 2026-10-15
Source: `/home/master_j/work/cli-anything-audit-d`
Branch: `audit/remaining-d`
Commit: `9ef6dc8b60cfe2f46752c18088992403fdcf8b1c`
Scope: safari, sbox, seaclip, shotcut, siyuan, sketch, slay_the_spire_ii, tigris, unimol_tools, unrealinsights, videocaptioner, wavetone, web-yu-pri, wiremock, zoom, zotero.

## Method

Read the installed CLI-Anything `references/HARNESS.md` and `references/commands/test.md`, plus Superpowers TDD and its writing-good-tests reference. No repository `AGENTS.md` was present. Default test trees ran with the WSL venv Python and `pytest -q --tb=short`. Test child processes received only PATH, HOME, and locale, so account tokens and opt-in live-test switches were absent. Four suites ran concurrently, with a five-minute per-suite limit. No credentials or live accounts were accessed; no Windows-side installs or edits occurred.

Full-run logs are beside this report in `pressure-evidence/upstream/batch-d/`. Logs were not committed. The source commit contains only production code and regression tests.

## Test matrix

| Harness | Default full tests | Focused results | Backend gate or blocker |
|---|---|---|---|
| safari | Collection blocked by missing `mcp` Python dependency. | Core/security subset: 30 passed, 11 failed; all 11 import the missing `mcp` module from `safari_backend.py`. | Safari and its MCP backend require macOS. |
| sbox | **241 passed, 4 skipped** after fix. | New project-name traversal regression: RED (no `ValueError`, wrote `../escaped.sbproj` outside output dir), then GREEN. | Four backend tests skipped; s&box executable absent in WSL. |
| seaclip | **28 passed, 7 skipped**. | Local project tests only. | Seven local backend checks skipped; no service listener/process present. |
| shotcut | Collection blocked by missing `PIL` dependency. | Core unit tests: 224 passed, 1 failed (`TestExport.test_export_updates_tractor_out_with_trailing_blank`, actual 150 vs expected 240). | E2E blocked at collection by missing Pillow; renderer not exercised. |
| siyuan | **41 passed, 5 skipped**. | N/A | Live app checks skipped; no local SiYuan service present. |
| sketch | No test directory, `setup.py`, or CLI package under `agent-harness`. | N/A | Documentation/scaffold only; no executable harness to test. |
| slay_the_spire_ii | **14 passed**. | N/A | E2E uses a fake local bridge server; game was not started. |
| tigris | **43 passed, 5 skipped**. | N/A | Live operations require opt-in and a test bucket/auth; gates stayed unset. |
| unimol_tools | Full suite collection blocked: missing `pandas` in `tests/conftest.py`. | Cleanup after fixes: **11 passed** with `--noconftest`. Cleanup+storage without conftest: 24 passed, 5 failed. Core+cleanup+storage without conftest: 25 passed, 5 failed, 3 errors (`tmp_dir` fixture absent). | Scientific/model runtime not installed; no model execution attempted. |
| unrealinsights | **70 passed, 13 skipped, 2 failed**. | Two response-file failures: quoting expectation and normalized response-file temp-copy expectation. | Capture tests require `UNREALINSIGHTS_TEST_TARGET_EXE`; absent. |
| videocaptioner | **14 passed, 11 skipped, 7 failed**. | Direct CLI import fails because `core/synthesize.py` imports absent `core.review`. Four synthesize patch/import tests and three review tests fail. | Eleven external backend tests skipped; no captioning service used. |
| wavetone | **30 passed, 2 skipped**. | N/A | Real backend is a Windows GUI executable and opt-in; disabled in WSL. |
| web-yu-pri | **16 passed, 1 skipped**. | N/A | Live account/browser-profile test skipped. |
| wiremock | **66 passed, 15 skipped**. | N/A | Live server tests require `WIREMOCK_URL`; unset. |
| zoom | **28 passed, 4 skipped**. | N/A | OAuth/account E2E is opt-in; unset. |
| zotero | **69 passed, 13 skipped, 6 failed**. | Six import tests attempted the local Zotero connector and received connection refused. | No Zotero process/listener present; no account credentials supplied. Tests are not isolated correctly when connector is absent. |

Common full command (run from each harness directory):
`/home/master_j/work/cli-anything-hardened/.venv/bin/python -m pytest -q --tb=short <absolute tests directory>`

Focused commands:
- sbox: `python -m pytest cli_anything/sbox/tests -q --tb=short` => 241 passed, 4 skipped.
- unimol_tools: `python -m pytest --noconftest cli_anything/unimol_tools/tests/test_cleanup.py -q --tb=short` => 11 passed.
- unimol_tools full attempt: `python -m pytest -q --tb=short cli_anything/unimol_tools/tests` => conftest import error for missing pandas.

Zotero failed tests, each tried `localhost:<connector-port>/connector/getSelectedCollection` and got connection refused:
- `ImportCoreTests.test_import_file_manifest_index_out_of_range_and_missing_connector_id_fail_cleanly`
- `ImportCoreTests.test_import_file_manifest_partial_success_records_attachment_failures`
- `ImportCoreTests.test_import_file_manifest_title_mismatch_marks_attachment_failure`
- `ImportCoreTests.test_import_json_duplicate_inline_attachments_are_skipped`
- `ImportCoreTests.test_import_json_strips_inline_attachments_and_uploads_local_pdf`
- `ImportCoreTests.test_import_json_url_attachment_uses_delay_and_default_timeout`

## Confirmed defects and TDD evidence

### sbox: project name escapes requested output directory

`core/project.py:create_project()` used `name` in both the default directory and `<name>.sbproj` filename without rejecting path components. With output_dir set to a temporary `project` directory, name `../escaped` wrote `<tmp>/escaped.sbproj` outside it.

- RED: `test_create_project_rejects_path_traversal_name` failed because no `ValueError` was raised.
- GREEN: reject names containing `/` or `\\` and names `.` / `..`; focused test passed.
- Full suite after fix: 241 passed, 4 skipped.

Regression: `sbox/agent-harness/cli_anything/sbox/tests/test_core.py`.

### unimol_tools: archive restore traversal and partial state; destructive path escape

`core/cleanup.py:restore_model()` called `tar.extractall(experiments_dir)` on a path from mutable project metadata. A controlled tar member `../escaped.txt` wrote outside `experiments/` while restore returned `status=restored`. A safe member before a malicious one also left partial files after rejection.

`delete_model()` and `archive_model()` trusted run `model_dir` / `save_path`; both removed a temporary fixture directory outside the project during reproduction. All reproduction paths stayed inside pytest temporary directories.

- RED: malicious archive regression observed outside write and false restored status; expanded test also observed partial extraction.
- RED: external-directory delete regression returned true and deleted its temporary fixture.
- RED: external-directory archive regression returned archived and deleted its temporary fixture.
- GREEN: resolve model paths and require them to be under project root; restore through tar's `data` filter into a temporary staging directory; validate the expected run directory; atomically move only after extraction succeeds.
- Focused cleanup suite after fixes: 11 passed.
- Separate storage tests still have five fixture/schema failures: they provide `project_root` and `models/` paths while the analyzer reads `_project_dir` and scans `experiments/`. Left unchanged because the intended project schema needs a separate decision.

Regressions: `unimol_tools/agent-harness/cli_anything/unimol_tools/tests/test_cleanup.py`.

## Other findings

- VideoCaptioner CLI import is broken in this checkout: missing `core.review`, which `core/synthesize.py` imports. Existing tests show the missing behavior but the intended review API is incomplete; no speculative module was added here.
- Shotcut has one existing unit failure: calculated tractor `out` duration was 150 vs expected 240. Full E2E collection was blocked by missing Pillow.
- UnrealInsights has two existing response-file test failures. No Unreal executable was available to establish backend behavior.
- Zotero's connector-dependent tests are not mocked or skipped when its local connector is absent; they completed with refused localhost connections.
- Static review covered filesystem path boundaries, symlinks, subprocess timeouts, error/secret handling, malformed inputs, and destructive APIs. Only the two reproduced path-boundary issues above were patched; no other adversarial defect was confirmed in this bounded pass.

## Commit

Source and regression tests are committed on `audit/remaining-d`:
`9ef6dc8b60cfe2f46752c18088992403fdcf8b1c` (`Harden SBox and UniMol path boundaries`).

`git diff --check` passed before commit. Branch was not pushed.
