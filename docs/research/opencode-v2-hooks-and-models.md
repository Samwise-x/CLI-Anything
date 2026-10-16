# OpenCode CLI v2: install, models, hooks, and CI patterns

Checked 2026-10-15 from first-party OpenCode docs/catalog, OpenCode's GitHub source, and a read-only npm registry query. No installation was performed.

## Install on WSL2/Linux

OpenCode v2's install page documents npm install -g @opencode/cli. The npm package selects the native binary in postinstall, and the docs state Windows package managers are unsupported. The environment is WSL2/Linux. The official page also offers the v2 install script, Bun, and pnpm. A read-only registry query returned latest 2.0.30 on 2026-10-15. To stay on major v2, use npm install -g @opencode/cli@2 and verify with opencode --version.

Sources: [v2 installation](https://dev.opencode.ai/v2/docs/), [npm registry metadata](https://registry.npmjs.org/@opencode%2fcli).

## Free and promotional models

OpenCode's v2 catalog gives these separate entries. The selector format is opencode/<model-id>.

| Catalog name | Selector | Current listed price/status |
|---|---|---|
| Nemotron 3 Ultra Free | opencode/nemotron-3-ultra-free | $0 input/output/cache; limited time |
| Muse Spark 1.3 Contributor Free | opencode/muse-spark-1.3-contributor-free | $0 input/output/cache; limited time |

The regular Muse Spark 1.3 entry is a different model ID, opencode/muse-spark-1.3, with nonzero prices. The catalog specifies Nemotron as OpenAI-compatible chat completions and Muse Contributor Free as Responses API; OpenCode handles routing for its model selector.

The catalog does not publish numeric RPM, daily, or monthly quotas for these two entries. Free pricing does not mean unlimited or permanent access. Verify current availability in /models after connecting, then use a small non-sensitive request. That confirms current access but not a quota guarantee.

Sources: [model IDs, pricing, and privacy notes](https://opencode.ai/v2/docs/console/models/), [provider docs](https://opencode.ai/v2/docs/providers/).

## Data handling

OpenCode says Nemotron 3 Ultra Free is an NVIDIA trial endpoint. Do not submit personal or confidential data. Requests are logged for security and to improve NVIDIA products and services. OpenCode links the [NVIDIA API Trial Terms](https://assets.ngc.nvidia.com/products/api-catalog/api-catalog-terms.pdf) and [NVIDIA privacy policy](https://assets.ngc.nvidia.com/products/api-catalog/api-catalog-privacy-policy.pdf).

OpenCode says Muse Spark 1.3 Contributor Free permits prompts and completions to be used to train future Meta models. Under these published terms, keep private source, credentials, customer information, and other sensitive repository data out of both free endpoints.

Source: [OpenCode model privacy notes](https://opencode.ai/v2/docs/console/models/).

## V2 project hook/event APIs

V2 discovers local plugins under .opencode/plugins/. The documented plugin exports Plugin.define({ id, setup(ctx) { ... } }) from @opencode/plugin; setup may return cleanup logic. Plugin configuration uses plural plugins in opencode.json(c).

Relevant APIs:
- ctx.permission.hook("evaluate", callback): sees allow/ask decisions before action or prompt; callback can set allow, ask, or deny. An explicit configured deny is final and skips the hook.
- ctx.shell.hook("create.before", callback): inspect or modify command, cwd, timeout, executable, or environment before shell execution.
- ctx.tool.hook("execute.before"/"execute.after"): inspect tool input and result.
- Session hooks cover prompt admission, model context, compaction, generation, title, model/HTTP request and response, and retry.
- ctx.event.subscribe() receives server events; clean up the subscription when the plugin unloads.
- CLI/TUI plugins are a separate local extension surface.

V1 plugins do not run in V2. Do not carry over V1's @opencode-ai/plugin imports or returned string-keyed hook objects; V2 uses @opencode/plugin and domain hook registrations.

Sources: [v2 plugin API](https://dev.opencode.ai/v2/docs/build/plugins/), [V1 migration guide](https://dev.opencode.ai/v2/docs/build/plugins/migrate-v1), [plugin loading](https://dev.opencode.ai/v2/docs/plugins), [CLI plugins](https://dev.opencode.ai/v2/docs/cli/plugins).

## First-party CI and release patterns for local WSL governance

The OpenCode repository's CI and release workflows provide examples for Linux checks, tests/builds, and release automation. Treat them as patterns to review, not files to copy wholesale: this is a monorepo with its own release secrets and deployment authority. The repository uses a moving dev branch, so record the exact reviewed commit before borrowing a pattern.

- [Workflow directory](https://github.com/anomalyco/opencode/tree/dev/.github/workflows)
- [CI workflow](https://github.com/anomalyco/opencode/blob/dev/.github/workflows/ci.yml)
- [Release workflow](https://github.com/anomalyco/opencode/blob/dev/.github/workflows/release.yml)
- [Plugin API package source](https://github.com/anomalyco/opencode/tree/dev/packages/plugin)
- [v2 plugin guide](https://dev.opencode.ai/v2/docs/build/plugins/)

For our local WSL loop, use deterministic local scripts called by hooks and the same scripts in Linux CI. A plugin test gate should cover allow/deny paths, malformed inputs, hook failures, cleanup/unload, and an OpenCode v2 smoke load against a fixture project. Keep model calls out of CI. Model-backed judgments can be advisory evidence, but should not decide test success or merge eligibility. Do not transplant release credentials, publish jobs, or release permissions.

## Confirmed and unknown

Confirmed on 2026-10-15: v2 Linux package/install docs; npm latest was v2.0.30 when queried; model IDs, zero listed prices, limited-time qualification, privacy notices, and V2 hook APIs.

Not established: numeric model quotas, promotion end date, whether free-account setup requires payment details, model quality for this repository, successful auth in this environment, or cloud/repository-wide enforcement by a local plugin. Keep deterministic CI and GitHub rules as repository enforcement; the OpenCode plugin governs its local runtime seam.
## CI and release workflow review

For commit e25b7abf8955a4fa1b02b935964cb47db4c3a02a (the upstream dev tip returned by GitHub during this review), the useful exact files are:

- [check.yml at reviewed commit](https://github.com/anomalyco/opencode/blob/e25b7abf8955a4fa1b02b935964cb47db4c3a02a/.github/workflows/check.yml): pull_request, push to dev, and manual triggers; concurrency cancels stale branch/PR checks; checkout fetches two commits for PR diffing; runs the repository check command and changed-file lint. This is the small reproducible pattern: one stable PR check, local check command reused in CI, and changed-file lint using the merge base. Its actual runner is Blacksmith, so do not copy that runner label.
- [test.yml at reviewed commit](https://github.com/anomalyco/opencode/blob/e25b7abf8955a4fa1b02b935964cb47db4c3a02a/.github/workflows/test.yml): determines affected packages, then runs affected unit tests and package verification with explicit timeouts; also has manual full-run behavior. This is a useful test selection pattern. Its workflow uses Blacksmith and includes Windows jobs; adapt only the affected-package concept and keep our local project Linux/WSL scoped.
- [plugin package.json at reviewed commit](https://github.com/anomalyco/opencode/blob/e25b7abf8955a4fa1b02b935964cb47db4c3a02a/packages/plugin/package.json): defines separate test, typecheck, and build scripts (Bun test, TypeScript typecheck, and build). Keep these gates independently visible rather than hiding all validation behind one aggregate script.
- [publish.yml at reviewed commit](https://github.com/anomalyco/opencode/blob/e25b7abf8955a4fa1b02b935964cb47db4c3a02a/.github/workflows/publish.yml): release pipeline uses workflow inputs and branch triggers, release-only write permissions and OIDC, plus upstream secrets; critical jobs guard on the canonical anomalyco/opencode repository. Its multi-platform artifact signing and publication machinery is upstream-specific and should not be copied into our local WSL governance loop.
- [OpenCode GitHub workflow docs](https://dev.opencode.ai/v2/docs/github/) describe invoking OpenCode from issue comments or PR review comments in GitHub Actions. That is a remote autonomous PR bot. It does not match this request for a local WSL2 long-running loop, so use the CLI's local project plugin hooks and do not install that workflow.

The direct upstream workflow files were fetched from GitHub API/raw endpoints at the commit above. The dev branch moves; commit-pinned links preserve the reviewed source snapshot. This review establishes workflow structure, not test outcomes for our plugin.

### Applicable local pattern

Expose independent local commands for formatting/lint, typecheck, plugin unit tests, and CLI smoke load. The hook should invoke the fast deterministic subset before risky tool/shell actions or before the loop marks a phase complete; the loop should run the full validation set before reporting completion. CI should call the same commands on a Linux hosted runner. Use bounded execution time and explicit nonzero exits. Add unit tests for deny decisions and hook cleanup. Avoid external model/API calls in these checks. Treat model output as planning/evaluation input only; it cannot grant permission, override failed checks, or satisfy a CI gate.
