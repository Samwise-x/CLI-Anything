# WSL2 autonomous goal loop

This maintainer loop runs OpenCode CLI v2.0.30 in disposable Linux Docker containers. The installed binary is `/home/master_j/.opencode/bin/opencode`; neither Windows executables nor a host home directory enter the container.

## Authentication and model data

Neither configured free model requires a one-time client login, as confirmed by the v2.0.30 provider source. Nemotron completed a live smoke request with no authenticated integrations. Muse responded and read tools, confirming authentication access, but its full reviewer attempt ended with a transport socket error; a complete reviewer verdict remains unconfirmed. Model availability and quotas can change; an unavailable promotional endpoint must stop the run rather than silently selecting a paid provider.

These offers are temporary. Muse Contributor Free may use prompts and completions to train future Meta models; the Nemotron trial endpoint logs requests for security and product improvement. Use only public source and non-sensitive goals. Filename filtering cannot establish that file contents are free of secrets.

## Build the Linux sandbox

From the WSL2 checkout, build the image using only the Dockerfile as build context:

    docker build -t cli-anything-opencode-sandbox:local - < .opencode/sandbox.Dockerfile

The base image is pinned to an immutable Linux amd64 manifest. The image runs as uid/gid 1000, matching this WSL2 checkout. No Docker socket, host environment, provider authentication database, home directory, or Git credential helper is mounted. Containers have a read-only root filesystem, dropped capabilities, no-new-privileges, process/memory/CPU limits, and temporary writable home/tmp directories.

Each stage receives a fresh copy of public repository files. Secret-like filenames (`.env*`, key/certificate files, credential/token/secret data files, SSH keys, and common authentication files) are excluded. All symbolic links and special files fail closed. The copied `.git` is reconstructed locally and contains no host configuration or remote credentials. A source diff is supplied at `/workspace/.goal-loop/source-diff.patch`; host repository paths in prompts map to `/workspace`.

The executor can change source files. Governance, agent configuration, runner/tools, ADRs, Git metadata, and `.goal-loop` evidence are mounted read-only. On successful exit, source changes are copied back only after checking protected files, symbolic links, and concurrent host edits. Cooperating sandbox writers share a repository flock during validation and copy-back; other editors should avoid concurrent changes during this short stage. The reviewer receives an entirely read-only checkout. Deterministic verification also uses a read-only container with networking disabled. Model roles need network access for their provider; they have Docker bridge networking, not network isolation from reachable services.

## Run and resume

Write a bounded goal with explicit acceptance criteria, then run from WSL2:

    python3 tools/goal_loop.py --goal /path/to/public-goal.md --run-dir .goal-loop/runs/<run-id> --config .goal-loop/config.example.json --max-iterations 3

Use `--resume` with the same goal and run directory to continue an incomplete run. The host driver owns state and evidence; the executor records details on stdout. Implementation, deterministic verification, and independent evaluation are separate processes. Model judgments cannot replace deterministic checks or repository merge rules.

The supplied configuration sends executor, evaluator, and verification commands through `tools/run_opencode_sandbox.py`. Calling OpenCode directly, including interactive `/goal`, bypasses this OS boundary. Use the driver configuration for protected autonomous execution.

Run the explicit Docker isolation integration check after building the image:

    RUN_SANDBOX_LIVE=1 python3 -m unittest tools.tests.test_opencode_sandbox -v

That check attempts protected-file and root-filesystem writes, checks a host-only marker and host environment are unavailable, and verifies the reviewer cannot change source. Ordinary tests skip this Docker-dependent integration case.
