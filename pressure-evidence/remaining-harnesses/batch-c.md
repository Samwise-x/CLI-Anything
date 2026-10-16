# Remaining Harness Audit - Batch C

Date: 2026-10-15
Checkout: /home/master_j/work/cli-anything-audit-c
Branch: audit/remaining-c
Scope: mermaid, minimax, mubu, musescore, novita, nsight-graphics, nslogger, obs-studio, ollama, openrefine, openscreen, pm2, quietshrink, rekordbox, renderdoc, rms

## Method

Read the installed CLI-Anything methodology (HARNESS.md and test-mode spec), Superpowers TDD instructions, and checked for repository AGENTS.md files. No AGENTS.md exists in this checkout. Ran each harness's documented tests directory using pytest, with the shared WSL venv for pytest and per-harness PYTHONPATH. No software was installed. No Windows binaries were intentionally invoked, no credentials were present, and no live accounts were accessed.

Initial command for each harness:

    python3 -m pytest -v -s --tb=short <harness>/cli_anything/<module>/tests

It was launched in WSL with the repo harness directory in PYTHONPATH and the existing WSL test venv first on PATH. Final Mubu verification used the same pytest args from its harness directory with PATH excluding shared CLI entrypoint scripts, so the package's current source module ran.

## Results matrix

| Harness | Initial unit + E2E result | Backend / skipped-test gate | Triage |
|---|---:|---|---|
| mermaid | 10 passed | Tests TestMermaidCLI::test_render_svg and TestMermaidCLI::test_render_png call the public mermaid.ink renderer. See external-request note below. | Suite green; tests include external E2E. |
| minimax | 32 passed | MINIMAX_API_KEY unset; API cases use mocks/local fake HTTP server. | Green, credential-free. |
| mubu | Initial: 1 failed, 93 passed, 12 skipped. Final: 94 passed, 12 skipped. | Local Mubu data/API-dependent discovery and dry-run cases skipped because data was unavailable. No mutations ran. | Confirmed banner discoverability defect fixed; details below. |
| musescore | 40 passed, 16 skipped | MuseScore executable absent; export/transpose/media/CLI backend E2Es skipped. | Unit/intermediate tests green; real backend unverified. |
| novita | 9 passed | NOVITA_API_KEY unset; cases use mocks. | Green, credential-free. |
| nsight-graphics | 2 failed, 44 passed, 5 skipped | Nsight executables absent. Two unit tests' patches target the wrong module symbol, so their simulated Windows drive roots do not reach the implementation. | Test-fixture defect, not a confirmed product defect. |
| nslogger | 141 passed | Uses local synthetic/temp data. | Green. |
| obs-studio | 178 passed | No live OBS service was used; suite passed its local/mock coverage. | Green; backend state unverified. |
| ollama | 88 passed, 11 skipped | Ollama binary/server absent; live model and generation tests skipped. | Green unit coverage; server/backend unverified. |
| openrefine | 85 passed, 10 setup errors | 127.0.0.1:3333 refused connection; no local OpenRefine service. E2E fixture treats missing backend as an error, as documented. | Backend gate; no test behavior change made. |
| openscreen | 1 failed, 90 passed, 15 skipped | ffmpeg and ffprobe absent. The explicit dependency test failed; media generation/export tests skipped. | Backend gate; no test behavior change made. |
| pm2 | 28 passed, 9 skipped | PM2 binary/daemon absent; process/system CLI E2Es skipped. | Unit coverage green; daemon/backend unverified. |
| quietshrink | 15 passed | Unit tests mock subprocess behavior. No live ffmpeg export was available. | Green unit coverage; real encode unverified. |
| rekordbox | 8 passed | Smoke and mocked backup/write-guard tests only; no Rekordbox application/database was accessed. | Green safety tests; live integration unverified. |
| renderdoc | 48 passed, 18 skipped | RenderDoc Python module, CLI, capture files, and GPU backend unavailable; real capture/replay/preview cases skipped. | Unit coverage green; real backend unverified. |
| rms | 85 passed, 9 skipped | RMS URL and API key unset; authenticated API cases skipped. | Green unit coverage; live API unverified. |

Test logs and summary:
- mermaid.log, minimax.log, mubu.log (original fail), mubu-source-red.log, mubu-focused.log, mubu-full.log, and one <harness>.log per suite are beside this report.
- unit-e2e-summary.json records the initial unmodified-suite results.

## Confirmed defect and TDD evidence

Mubu's compatibility-name/default REPL entrypoint used the styled banner but omitted the resolved local SKILL.md path. This prevented an agent from discovering the harness instructions from the banner, despite ReplSkin resolving a skill file.

- Regression: existing CliEntrypointTests.test_default_entrypoint_banner_includes_skill_path.
- RED: temporarily restored the frozen baseline implementation from HEAD and ran the focused test. It failed because stdout had no Skill: line. Full output: mubu-source-red.log.
- GREEN: added the resolved skin.skill_path line to the compatibility banner. The focused test passed (1 passed).
- The existing test had assumed only a package-local path. ReplSkin's documented resolution prefers the repository canonical skill path, so the assertion now accepts a resolved path ending in /skills/cli-anything-mubu/SKILL.md.
- Final Mubu full suite: 94 passed, 12 skipped in 6.66s.
- git diff --check passed.

Only these tracked source/test files are changed:
- mubu/agent-harness/cli_anything/mubu/mubu_cli.py
- mubu/agent-harness/cli_anything/mubu/tests/test_cli_entrypoint.py

## Other failures triage

- Nsight Graphics' two failing assertions are attributable to test mocking: tests patch _fixed_windows_drive_roots through nsight_graphics_backend, but discovery.py calls its directly imported local symbol. The expected D: drive never enters the implementation. No source change was made; test assertions are preserved in nsight-graphics.log.
- OpenRefine E2E setup errors report connection refusal from the default local endpoint. No service was listening, so no E2E workflow or project mutation occurred. The tests are not silently skipped.
- OpenScreen requires ffmpeg per its backend/test contract. The missing binary caused the direct dependency test to fail; no software was installed.

## External-request note

The Mermaid suite contains these renderer E2Es:
- TestMermaidCLI::test_render_svg — https://mermaid.ink/svg/<serialized-diagram>
- TestMermaidCLI::test_render_png — https://mermaid.ink/img/<serialized-diagram>?type=png

I discovered after the initial batch run that these tests use urllib to call the public renderer. Those two calls were inadvertently made before this was noticed. The request bodies represented the tests' synthetic diagram fixture; no credentials or account data were sent. Outputs were written under pytest temporary directories. These tests were not rerun. The exact serialized URL payload is intentionally not reproduced here.

## Adversarial review coverage and limits

Reviewed each harness's path/file operations, subprocess usage and timeout behavior, error construction, key/config handling, parsers, mutation/deletion surfaces, and session/project state code. Existing suites cover many malformed-input, subprocess failure, timeout, state round-trip, backup, and mutation-guard cases, but depth varies substantially by harness.

Confirmed findings in this batch: the Mubu skill-path omission above. No additional confirmed path traversal, symlink escape, timeout-overrun, secret-reflection, malformed-input, destructive-operation, or state-consistency defect was reproduced in the local credential-free scope. This statement does not certify real application/backend behavior where the required executable, service, capture file, local app data, or credentials were absent.

## Exact test commands

For each harness, from /home/master_j/work/cli-anything-audit-c/<name>/agent-harness:

    python3 -m pytest -v -s --tb=short cli_anything/<module>/tests

The Mubu final focused command:

    /home/master_j/work/cli-anything-hardened/.venv/bin/python -m pytest -q cli_anything/mubu/tests/test_cli_entrypoint.py::CliEntrypointTests::test_default_entrypoint_banner_includes_skill_path

The Mubu final full command:

    /home/master_j/work/cli-anything-hardened/.venv/bin/python -m pytest -v -s --tb=short cli_anything/mubu/tests

For these final Mubu commands, PYTHONPATH pointed to Mubu's agent-harness directory and PATH was restricted to /usr/bin:/bin to avoid resolving a stale shared CLI console entrypoint.
