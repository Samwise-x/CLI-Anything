# Remaining harness pressure audit - batch B

Date: 2026-10-15
Checkout: `/home/master_j/work/cli-anything-audit-b`
Branch: `audit/remaining-b`
Policy: WSL only; no credentials, live services, or Windows installs/edits.

## Results matrix

| Harness | Full suite result | Backend / test gate | Adversarial audit notes |
|---|---:|---|---|
| exa | blocked at collection: 2 errors | `exa-py` Python package is absent; EXA_API_KEY was unset, so live API tests were not enabled | Unit and live API tests could not be collected. No service called. |
| firefly-iii | 42 passed, 56 skipped | Remote E2E requires FIREFLY_III_BASE_URL and FIREFLY_III_PAT; both were scrubbed/unset | Confirmed PAT reflection in HTTP error text; red/green details below. |
| freecad | 88 unit passed; full-suite collection blocked by 1 error | Pillow missing; FreeCAD executable and GUI backend unavailable | Native export/preview E2E could not be collected/run. |
| gimp | 71 unit passed; full-suite collection blocked by 1 error | Pillow missing; GIMP executable unavailable | Native image-render E2E could not be collected/run. |
| godot | 28 passed, 22 skipped | Godot executable absent; engine E2E skips | Backend dependent tests skipped; local project/state tests ran. |
| inkscape | 201 passed, 4 skipped, 5 failed on backend gate | Inkscape executable absent; 5 checks intentionally require it | Five failures are explicit missing-backend checks / native exports, not unit assertion regressions. |
| intelwatch | 4 passed | External command is invoked through subprocess forwarding; E2E harness tests mock forwarding | No external command executed by E2E fixtures. |
| iterm2 | 89 passed, 28 skipped, 21 failed at dependency gate | `iterm2` Python package absent; macOS iTerm2 connection unavailable | Failed tests' traces report missing Python package; no live iTerm2 connection. |
| joplin | 117 passed, 18 skipped | Joplin CLI executable absent; 18 backend checks skipped | Local CLI/project tests ran; no Joplin profile/service was accessed. |
| jumpserver | 116 passed | API scenarios are local/mocked; no URL or credentials supplied | Confirmed session file was mode 0644 and followed symlinks; red/green below. |
| kdenlive | 174 passed, 5 failed on backend gate | `melt` executable absent | Five failures require real MLT rendering and explicitly report missing `melt`. |
| krita | 43 passed, 4 failed on backend gate | Krita executable absent | Four failures require the real renderer and explicitly report missing Krita. |
| libreoffice | 162 passed, 18 failed on backend gate | LibreOffice executable absent | 18 failures are native conversion/import checks that require the actual binary. |
| live2d | 49 passed | Local parser/validator/backup workflows; no external runtime required by this suite | Confirmed backup path traversal and symlinked backup-directory write escape; red/green below. |
| lldb | 49 passed, 7 skipped | LLDB module/binary unavailable for debugger-backed cases | Protocol/session/unit tests ran; live debugger cases skipped. |
| mailchimp | blocked at collection: 1 error | `responses` Python test dependency absent; MAILCHIMP_API_KEY was unset | Mocked client tests could not collect; live API tests were not enabled. |

The environment used an isolated WSL test process with a temporary HOME and an allowlisted PATH. API credential variables were absent. No live account or service was accessed.

## Confirmed fixes: red/green

### Live2D backup restore traversal

Test: `test_restore_rejects_backup_path_traversal` in `live2d/agent-harness/tests/test_new_features.py`.

- RED: with a valid backup directory present, `restore(model, "../../outside.model3.json")` did not raise, so a non-backup file could be copied over the model.
- GREEN: restore now accepts a backup filename only; slash and backslash path components are rejected.
- Full suite: **49 passed**.

### Live2D backup symlink escape

Test: `test_snapshot_rejects_symlinked_backup_directory`.

- RED: snapshot through a symlinked per-model backup directory did not raise and wrote into the linked directory.
- GREEN: the shared backup path resolver rejects a symlinked backup root or per-model backup directory.
- Full suite: **49 passed**.

### Firefly III PAT reflection

Test: `test_http_error_redacts_pat_reflected_by_server` in `firefly-iii/agent-harness/cli_anything/firefly_iii/tests/test_core.py).

- RED: mocked HTTP 500 response containing `test-pat-secret` produced a RuntimeError containing that same PAT.
- GREEN: response error text replaces the configured PAT before surfacing it, including connection validation errors.
- Full suite: **42 passed, 56 skipped**. All remote tests were skipped because credentials and base URL were absent.

### JumpServer session permissions

Test: `test_session_file_is_private` in `jumpserver/agent-harness/cli_anything/jumpserver/tests/test_core.py).

- RED: the saved token session file had mode `0644` (observed decimal mode 420), not `0600`.
- GREEN: session save opens/creates the file with mode `0600` and enforces that mode on existing files.
- Full suite: **116 passed**.

### JumpServer symlink following

Test: `test_session_save_does_not_follow_symlink`.

- RED: saving through a symlink to a victim file did not raise and replaced the victim content.
- GREEN: session save uses `O_NOFOLLOW` where supported; the linked destination fails closed and the victim remains intact.
- Full suite: **116 passed**.

Exact red/green logs are in `/home/master_j/work/cli-anything-pressure-lab/pressure-evidence/upstream/batch-b-logs/`.

## Commands and evidence

For each harness, ran the suite's `tests/` directory with:

```sh
env -i PATH=/home/master_j/work/cli-anything-hardened/.venv/bin:/usr/local/bin:/usr/bin:/bin \
  HOME=/tmp/cli-audit-home LANG=C.UTF-8 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH=<harness>/agent-harness \
  /home/master_j/work/cli-anything-hardened/.venv/bin/pytest -v --tb=short <harness-test-directory>
```

For Live2D, the suite lives at `live2d/agent-harness/tests`; for iTerm2, at `iterm2/agent-harness/cli_anything/iterm2_ctl/tests`. FreeCAD and GIMP unit suites were also run separately to avoid their E2E collection failure caused by missing Pillow:

```sh
pytest -q <harness>/agent-harness/cli_anything/<package>/tests/test_core.py
```

Final full-suite logs are named `<harness>.log` in the evidence directory. FreeCAD and GIMP unit-only runs are `freecad-core.log` and `gimp-core.log`. Final changed-harness totals were re-run after fixes. `git diff --check` passed.

## Coverage limits

The 16 suites were run under the available WSL runtime. Native application E2E for FreeCAD, GIMP, Godot, Inkscape, iTerm2, Joplin, Kdenlive, Krita, LibreOffice, and LLDB was skipped or blocked by absent native software / platform backend. Exa, Mailchimp, and Firefly III live API tests were not enabled because credentials/endpoints were deliberately absent. The code review focused on path and symlink boundaries, subprocess deadlines, secret-bearing errors/session files, malformed inputs, destructive state changes, and state consistency; no other confirmed defect was established from this run. Full missing Python/native dependencies were not installed.

## Local source changes

- `firefly-iii/agent-harness/cli_anything/firefly_iii/tests/test_core.py`
- `firefly-iii/agent-harness/cli_anything/firefly_iii/utils/firefly_iii_backend.py`
- `jumpserver/agent-harness/cli_anything/jumpserver/core/session.py`
- `jumpserver/agent-harness/cli_anything/jumpserver/tests/test_core.py`
- `live2d/agent-harness/cli_anything/live2d/core/backup.py`
- `live2d/agent-harness/tests/test_new_features.py`

No source changes were made for the other harnesses. The isolated branch has not been pushed.
