# WSL2 follow-up pressure results

Date: 2026-10-15
Branch: `codex/psycho-tier-pressure-fixes-2026-10-15`

This follow-up resolved the actionable failures left by the initial 64-harness pressure pass. All commands ran inside WSL2; no Windows or macOS applications were installed or invoked.

## Fixes and verification

| Harness | Change | Result |
|---|---|---|
| Shotcut | Synchronize the project tractor duration before checking for the optional `melt` renderer, so missing-renderer errors do not leave stale timeline duration metadata. | `test_core.py`: 225 passed. |
| UnrealInsights | Normalize response-file output quoting independently from interactive command quoting; remove unnecessary quotes for paths without spaces, causing changed response files to be written to a temporary file. | `test_core.py`: 68 passed, 2 skipped. |
| Zotero | Mock selected-collection lookup in the import test fixture; tests had mocked import actions but still made a live request to the absent local connector. | `test_core.py`: 43 passed. |
| UniMol | Correct stale storage fixtures to use the current `_project_dir` and `experiments/` project schema. | Storage + cleanup: 31 passed with `--noconftest`. |
| VideoCaptioner | Add missing subtitle/script review and ffmpeg preview helpers exercised by existing tests. | `test_core.py`: 21 passed. |

`git diff --check` passed before this follow-up.

## Environment and remaining gates

The initial broad suite runs had dependency gates (including Pillow, pandas, and SciPy). An isolated pip download stalled, and a simulated WSL package install would add about 728 MB, so that bulk installation was cancelled before any packages were installed. Sketchs harness exists and contains Node tests, but Node.js is absent in WSL2. Native macOS GUI applications and their live integrations are unavailable in this Linux environment; those integrations require mock/offline coverage, not an attempted Windows or macOS install.

These results are local WSL2 test evidence; they do not claim native GUI or external-account end-to-end validation.
