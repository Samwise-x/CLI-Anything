# Cross-cutting static adversarial review

Date: 2026-10-15
Frozen source: `/home/master_j/work/cli-anything-frozen-clone`
Commit: `ffc01aa574feab64299f271ba49b6e3d56d6e0b0`
Scope: all 64 upstream harness trees not covered by the five-project local pressure snapshot. Read-only static review; no tests, installs, or live services were run.

Batch ownership follows the coordinating split: A = 3MF through eth2-quickstart; B = exa through mailchimp; C = mermaid through rms; D = safari through zotero.

## Confirmed reachable risks

### D - UniMol Tools: archive restore trusts project paths and extracts unfiltered tar data

- **Evidence:** `unimol_tools/agent-harness/cli_anything/unimol_tools/unimol_tools_cli.py:81-85` accepts a project path; `core/project.py:103-119` loads JSON without validating run records or `_project_dir`; CLI archive restore accepts external `run_id` and calls the core at `unimol_tools_cli.py:777-825`. `core/cleanup.py:160-194` looks up the run record, trusts its `archive_path`, derives the extraction root from project metadata at lines 180-183, then calls `tar.extractall(experiments_dir)` without member validation at line 194.
- **Impact / reachability:** A user who opens a crafted project JSON and invokes `archive restore` can cause an archive member such as `../../target` to write outside the expected experiments directory. An attacker-controlled `_project_dir` can also change that root. This is a local arbitrary-file-write path conditional on the user loading the crafted project and running restore.
- **Reproducer idea:** Create a project JSON with one archived run pointing to a test tar containing a traversal member; invoke archive restore in a disposable temp tree. Assert the command rejects traversal and no sentinel outside experiments is created.
- **Suggested owner:** D.

### D - UniMol Tools: cleanup deletes a project-supplied path

- **Evidence:** `core/cleanup.py:25-48` takes `model_dir` directly from a run record and calls `shutil.rmtree(model_dir)` without checking containment under the project experiments directory. The CLI loads project JSON at `unimol_tools_cli.py:666-671`; `cleanup --auto` passes suggested IDs into `batch_cleanup(..., confirm=True)` at lines 716-725. The confirmation in `core/cleanup.py:236-267` reports only counts, then invokes `delete_model(..., confirm=False)`.
- **Impact / reachability:** A crafted project can mark an old, low-scoring run as deletable and point its `model_dir` at another writable directory. After the generic “Proceed?” confirmation, cleanup recursively deletes that path. Confirmation does not display the concrete directory.
- **Reproducer idea:** In a disposable fixture, load a crafted project whose eligible run points to a sibling sentinel directory; answer yes to the batch prompt. Assert cleanup refuses paths outside the project's experiments root and preserves the sentinel.
- **Suggested owner:** D.

### D - UniMol Tools: project name escapes the selected output directory

- **Evidence:** CLI `unimol_tools_cli.py:140-159` accepts `--name` and `--output-dir`; `core/project.py:10-40` forms `os.path.join(output_dir, name)` and creates the directory without validating that the resolved path remains under output_dir.
- **Impact / reachability:** A name such as `../outside` makes the CLI create the project directory and project files outside the requested output directory.
- **Reproducer idea:** Use a temporary output directory with name `../escaped`; assert creation rejects the name or that the resolved project path remains contained.
- **Suggested owner:** D.

### D - s&box: project name escapes the intended working directory

- **Evidence:** CLI `sbox_cli.py:198-215` accepts `project new --name`; `core/project.py:187-225` sets default root to `os.path.join(os.getcwd(), name)` and then creates it at line 213. There is no name/path containment validation. The same name is used to form the .sbproj filename at lines 215-226.
- **Impact / reachability:** A name containing parent components can create the project tree outside the current directory. The output-dir option intentionally selects a root, but the no-output-dir default still interprets a project name as a path.
- **Reproducer idea:** In a temporary working directory, invoke project creation with `--name ../escaped`; assert rejection or containment under the working directory.
- **Suggested owner:** D.

## Conditional data-flow risks to pressure-test

### A - AnyGen: API response body can reflect a request credential into CLI errors

- **Evidence:** `anygen_backend.py:158-185` constructs a task-prepare request whose JSON body includes `auth_token` at line 172, then raises a RuntimeError containing up to 300 characters of untrusted `resp.text` on non-200 at line 185. The CLI reaches this API via `anygen_cli.py:298` and `core/task.py:126`. Other endpoints also include raw response text in errors at backend lines 111, 259, and 285.
- **Impact / reachability:** If a service/proxy error response echoes the submitted token, it appears in exception output and can be retained in agent logs. The current implementation doesn't redact the known token.
- **Reproducer idea:** Mock a failing response body containing the exact auth token; assert the surfaced exception/output redacts it.
- **Classification:** Confirmed unredacted response-body data flow; credential exposure depends on the server/proxy echoing a secret.
- **Suggested owner:** A.

### B - Firefly III: generic HTTP errors include the raw response body

- **Evidence:** `firefly_iii_backend.py:25-29` places the PAT in the Authorization header. `_validate_connection` raises raw `response.text` for non-401 HTTP errors at lines 51-57; API requests also expose raw response text at lines 92-101.
- **Impact / reachability:** A configured Firefly endpoint or intermediary that echoes the request Authorization value in an error body can reflect the PAT into CLI errors/logs. 401 is handled with a constant message, but other statuses are not redacted.
- **Reproducer idea:** Mock a non-401 response whose body contains the test PAT; assert the reported error redacts it.
- **Classification:** Conditional secret-reflection risk, not evidence that the official server currently echoes credentials.
- **Suggested owner:** B.

## Heuristic availability leads

These are source-level call sites worth deadline tests; a missing timeout may be intentional for long-running operations. The broader AST scan found 38 production subprocess calls without a literal timeout, including persistent Popen-based servers/editors. Do not classify those Popen lifetimes as defects without tracing their wait/stop contract.

- **A / QGIS:** `QGIS/agent-harness/cli_anything/qgis/utils/qgis_backend.py:164-184` runs `qgis_process` synchronously without a timeout, and commands feed into this shared runner. Consider a test with a hanging fake qgis_process and define a bounded-operation contract; long GIS algorithms may legitimately need configurable deadlines.
- **C / QuietShrink:** `quietshrink/agent-harness/cli_anything/quietshrink/quietshrink_cli.py:69-97` invokes the Bash compressor with `subprocess.run` without a timeout; user-supplied video input can keep the command active for an unbounded duration. `probe` also runs ffprobe without a timeout at lines 107-143. Consider a fake hanging backend test and an explicit configurable timeout policy.
- **D / UniMol Tools:** `utils/unimol_backend.py:108-117` deserializes `metric.result` with `pickle.load`. The file is in the generated training output path and appears intended as a library-generated artifact; static inspection did not establish a normal CLI route for an attacker-controlled pickle. Treat it as a trust-boundary question if projects or run directories are imported from untrusted sources.

## Negative and false-positive checks

- Static scan found no `shell=True` or `os.system` with interpolated user input in the 64 remaining trees. One `os.system('')` match in Firefly III is a terminal/clear-screen shim, not command composition.
- AST scan found no production `requests.*` or `urllib.request.urlopen` call lacking a literal `timeout` argument in the reviewed Python files.
- Calibre's `zipfile.extract` use at `calibre/agent-harness/cli_anything/calibre/core/export.py:305-313` is preceded by resolved-path containment validation; the simple extraction-pattern match is not a finding.
- This review is static triage. It establishes code paths and test hypotheses; it does not establish exploit execution, backend availability, or a passed regression test.
