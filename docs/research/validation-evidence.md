# Validation evidence: WSL2 maintainer goal execution

Recorded 2026-10-15. This change adds a local maintainer goal driver, distinct executor and evaluator, Linux sandbox, repository CI/security configuration and implementation notes.

## Observed verification

- Host complete tools suite: 29/29 passing with Docker integration enabled. Live Docker sandbox suite: 10/10 passing. Attempts to write protected policy or root filesystem fail; reviewer source writes fail; host marker/environment/socket unavailable.
- Isolated complete tools suite: 28 passing, 1 Docker integration test skipped inside the container (nested Docker is deliberately unavailable). The Docker integration suite runs separately on the WSL host and in CI.
- Independent review reproduced then fixed terminal-marker false approval, evidence overwrite, runaway descendants, missing deletion/addition diffs, competing writers, empty Git pathspec secret leaks and wildcard pathspec expansion. Final independent review found no remaining blockers within runner/sandbox scope.
- actionlint 1.7.12 validates all workflows. Ruff 0.17.1 checks Python correctness (E9,F63,F7,F82). Pre-commit configuration validates.
- OpenCode 2.0.30 SHA256: 37d1ad1bea702ba87272e6679a2c4150ae936785bc31b561ea43ebe74cc961b8. No authenticated integrations. Nemotron and Muse both responded through the actual container wrapper. These were connectivity checks, not approval of an implementation. A prior Muse host review attempt ended with a transport socket error: provider availability remains a runtime dependency.
- Wrapper SIGTERM smoke exited143 and removed its named Docker container.

## Operational limits

Use only public source and non-sensitive goals: filename filtering does not inspect arbitrary content for secrets. Model roles use Docker bridge networking and can reach services available from that network. Repository sync locks coordinate cooperating wrappers; host editors must coordinate. Abrupt host loss can leave a run lock requiring inspection of its recorded owner. Model review quality is not established by connectivity or boundary tests.

Server settings and Actions results must be verified separately after publishing. Committed ruleset JSON alone does not enforce GitHub rules. Do not describe remote CI or merge protection as active from local test results.
