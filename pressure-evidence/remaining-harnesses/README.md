# Remaining CLI-Anything harness pressure audit

Date: 2026-10-15
Frozen source baseline: `ffc01aa574feab64299f271ba49b6e3d56d6e0b0`
Integrated pressure branch starting point: `06714e9c673f9622ad1c3c78f7d856b7faeec1a4`

## Scope and method

This pass covered all 64 harnesses left after the earlier focused work on CC Switch, MacroCLI, n8n, NotebookLM, and Obsidian. The 64 were divided into four isolated WSL worktrees, 16 harnesses per batch. Each documented test suite was attempted. Tests unavailable because of missing dependencies, native applications, platform requirements, services, or credentials are explicitly classified in the batch reports.

Confirmed fixes followed the requested test-first sequence: add a focused regression, observe it fail against the unmodified implementation, make a minimal fix, then run the affected suite. The fixes were committed separately per batch. No Windows software or configuration was installed or changed. No credentials or live accounts were used.

## Integrated fixes

- **AdGuardHome:** save the configuration containing Basic Auth credentials with mode 0600.
- **AnyGen:** redact API tokens reflected in response errors; constrain server-provided download names to the output directory; reject dangling symlink targets.
- **Browser:** block legacy numeric IPv4 loopback forms when private-network blocking is enabled.
- **ChromaDB:** apply a finite 30-second timeout to REST requests.
- **Firefly III:** redact a PAT reflected in HTTP error text.
- **JumpServer:** make session files private and fail closed on symlink targets.
- **Live2D:** reject backup path traversal and symlinked backup directories.
- **Mubu:** include the resolved SKILL.md location in the default compatibility banner.
- **s&box:** reject project names that escape the selected output directory.
- **UniMol Tools:** confine archive/delete operations to the project, extract archives into staging with tar's data filter, and publish restored data atomically to prevent traversal and partial state.

## Verification

After integration, the modified suites were rerun against the combined branch:

| Harness | Result |
|---|---:|
| AdGuardHome | 39 passed |
| AnyGen | 47 passed, 6 skipped |
| Browser | 196 passed, 11 skipped, 1 warning |
| ChromaDB | 39 passed, 14 skipped |
| Firefly III | 42 passed, 56 skipped |
| Live2D | 49 passed |
| JumpServer | 116 passed |
| Mubu | 94 passed, 12 skipped |
| s&box | 241 passed, 4 skipped |
| UniMol cleanup regressions | 11 passed |

UniMol's normal test collection remains blocked by missing pandas in WSL; its changed cleanup suite was run with `--noconftest`. Shared tooling checks also passed: CLI-Anything plugin tests (41 passed) and the Codex skill installer shell self-test.

## Remaining gates and defects

The other harnesses were still exercised as far as the local WSL environment allowed; the detailed matrices are in the batch reports below. Some tests remain blocked or fail because WSL lacks native apps, macOS-only components, optional Python packages, local backends, or opt-in credentials. A small number of test failures remain in upstream harnesses (including Shotcut, UnrealInsights, and Zotero); these were not masked or relabeled as product passes. Sketch has no executable harness structure in the checkout. VideoCaptioner has a missing `core.review` import/API with unclear intended implementation and was left for a separate design decision.

The static review lists additional path and deletion risks, conditional credential-reflection paths, and timeout-test leads. Risks without a reproduced, focused regression are labeled as leads rather than confirmed defects.

## External test request recorded

The Mermaid suite's SVG and PNG tests made one request each to the public mermaid.ink renderer before the network call was noticed. The requests contained only synthetic diagram fixtures, no credentials or account data. Those tests were not rerun. The batch C report records the exact test names without preserving request payloads.

## Reports

- [Batch A: 3MF through eth2-quickstart](batch-a.md)
- [Batch B: Exa through Mailchimp](batch-b.md)
- [Batch C: Mermaid through RMS](batch-c.md)
- [Batch D: Safari through Zotero](batch-d.md)
- [Cross-cutting static review](cross-cutting-static-review.md)
- [Shared plugin and installer checks](shared-tooling.md)

Per-suite logs and red/green traces are preserved in the cold-storage pressure-lab archive; the reports above summarize the evidence without adding verbose logs to the source repository.
