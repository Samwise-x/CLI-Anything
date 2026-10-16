# Shared builder and installer verification

Date: 2026-10-15
Source: frozen WSL checkout at ffc01aa574feab64299f271ba49b6e3d56d6e0b0.

- CLI-Anything generator tests: `/home/master_j/work/cli-anything-hardened/.venv/bin/python -m pytest -q cli-anything-plugin/tests` - 41 passed in 0.68s.
- Codex skill installer self-test: `bash codex-skill/tests/test_install.sh` from the frozen checkout - PASS. It installs into a temporary CODEX_HOME, checks vendored resources and idempotency rejection, verifies detached-install failure, then cleans up.
- `pytest -q codex-skill/tests` is not a valid command for this directory: pytest found no tests because the test is a shell script. Ran the shell test instead.
