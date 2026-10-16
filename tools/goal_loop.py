"""Bounded, resumable subprocess runner with durable evidence and separate evaluator."""
from __future__ import annotations
import argparse
import hashlib
import re
import signal
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone


def validate_config(config):
    for key in ("executor", "evaluator", "verify"):
        if not config.get(key):
            raise ValueError(f"{key} must be configured")
    if config["executor"] == config["evaluator"]:
        raise ValueError("executor and evaluator must be independent")
    for key in ("executor", "evaluator"):
        if not isinstance(config[key], list) or not all(isinstance(x, str) for x in config[key]):
            raise ValueError(f"{key} must be a command argument list")
    if not isinstance(config["verify"], list) or any(
        not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) for x in cmd)
        for cmd in config["verify"]
    ):
        raise ValueError("verify must contain nonempty command argument lists")
    return config


def _run(command, cwd, timeout, env=None):
    with subprocess.Popen(command, cwd=cwd, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, env=env, start_new_session=True) as process:
        try:
            output, _ = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                pass
            finally:
                # A child may ignore TERM after the wrapper exits and closes its pipes.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate()
            raise
        return subprocess.CompletedProcess(command, process.returncode, output)


def _ends_with_marker(output, marker):
    clean = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output)
    lines = [line for line in clean.splitlines() if line.strip()]
    events = []
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            events = []
            break
        if not isinstance(event, dict):
            events = []
            break
        events.append(event)
    if events:
        if any(event.get("type") == "error" for event in events):
            return False
        clean = "".join(event.get("part", {}).get("text", "")
                        for event in events if event.get("type") == "text")
    terminal = [line.strip() for line in clean.splitlines() if line.strip()]
    return bool(terminal) and terminal[-1] == marker


def _command(command, goal_file, run_dir):
    goal_text = goal_file.read_text(encoding="utf-8")
    replacements = {
        "{goal}": goal_text,
        "{goal_path}": str(goal_file),
        "{run_dir}": str(run_dir),
        "{evidence_path}": str(run_dir / "evidence.md"),
    }
    templated = any(token in part for part in command for token in replacements)
    expanded = []
    for part in command:
        for token, value in replacements.items():
            part = part.replace(token, value)
        expanded.append(part)
    if not templated:
        expanded.append(str(goal_file))
    return expanded

def _write_json(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def run_goal(goal_file, run_dir, config, max_iterations=3, timeout=900, resume=False):
    validate_config(config)
    run_dir = Path(run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    lock = run_dir / ".lock"
    try:
        handle = lock.open("x", encoding="utf-8")
    except FileExistsError as error:
        raise ValueError("run directory is locked; inspect the recorded owner before recovery") from error
    try:
        with handle:
            handle.write(str(os.getpid()) + "\n")
        return _run_goal_locked(goal_file, run_dir, config, max_iterations, timeout, resume)
    finally:
        lock.unlink()


def _run_goal_locked(goal_file, run_dir, config, max_iterations=3, timeout=900, resume=False):
    validate_config(config)
    goal_file, run_dir = Path(goal_file).resolve(), Path(run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    state_path = run_dir / "state.json"
    evidence = run_dir / "evidence.md"
    goal_hash = hashlib.sha256(goal_file.read_bytes()).hexdigest()
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
    if not resume and (state_path.exists() or evidence.exists()):
        raise ValueError("existing run requires explicit resume")
    if resume:
        if not state_path.exists() or not evidence.exists():
            raise ValueError("resume requires existing state.json and evidence.md")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("status") == "complete":
            raise ValueError("completed goal runs cannot be resumed")
        if state.get("goal") != str(goal_file):
            raise ValueError("resume goal does not match the recorded goal")
        if state.get("goal_hash") != goal_hash or state.get("config_hash") != config_hash:
            raise ValueError("goal contents or configuration changed since the original run")
        start_iteration = state.get("iteration", 0) + 1
        with evidence.open("a", encoding="utf-8") as out:
            out.write("\n## Resume\n\nResumed: " + datetime.now(timezone.utc).isoformat() + "\n")
        state["status"] = "running"
    else:
        state = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat(),
                 "goal": str(goal_file), "goal_hash": goal_hash, "config_hash": config_hash, "iteration": 0}
        evidence.write_text("# Goal run evidence\n\nStarted: " + state["started_at"] +
                            "\n\n## Goal\n\n" + goal_file.read_text(encoding="utf-8") + "\n",
                            encoding="utf-8")
        start_iteration = 1
    _write_json(state_path, state)
    cwd = Path(config.get("cwd", goal_file.parent)).resolve()
    env = os.environ.copy()
    env["GOAL_FILE"] = str(goal_file)
    env["GOAL_EVIDENCE_DIR"] = str(run_dir)
    status = "incomplete"
    try:
        for iteration in range(start_iteration, max_iterations + 1):
            state["iteration"] = iteration
            _write_json(state_path, state)
            result = _run(_command(config["executor"], goal_file, run_dir), cwd, timeout, env)
            (run_dir / f"executor-{iteration}.log").write_text(result.stdout, encoding="utf-8")
            with evidence.open("a", encoding="utf-8") as out:
                out.write(f"\n## Executor iteration {iteration}\n\nExit: {result.returncode}\n\n{result.stdout}\n")
            if result.returncode != 0 or not _ends_with_marker(result.stdout, "GOAL_STATUS: complete"):
                continue
            checks = []
            for index, command in enumerate(config["verify"], start=1):
                checked = _run(command, cwd, timeout, env)
                (run_dir / f"verify-{iteration}-{index}.log").write_text(checked.stdout, encoding="utf-8")
                checks.append({"command": command, "exit_code": checked.returncode})
                with evidence.open("a", encoding="utf-8") as out:
                    out.write(f"\n## Verification {index}\n\nCommand: {command!r}\nExit: {checked.returncode}\n\n{checked.stdout}\n")
            _write_json(run_dir / f"verification-{iteration}.json", checks)
            _write_json(run_dir / "verification.json", checks)
            if any(item["exit_code"] != 0 for item in checks):
                continue
            reviewed = _run(_command(config["evaluator"], goal_file, run_dir), cwd, timeout, env)
            (run_dir / f"evaluator-{iteration}.log").write_text(reviewed.stdout, encoding="utf-8")
            with evidence.open("a", encoding="utf-8") as out:
                out.write(f"\n## Independent evaluation\n\nExit: {reviewed.returncode}\n\n{reviewed.stdout}\n")
            if reviewed.returncode == 0 and _ends_with_marker(reviewed.stdout, "REVIEW: pass"):
                status = "complete"
                break
        state["status"] = status
        state["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_json(state_path, state)
        with evidence.open("a", encoding="utf-8") as out:
            out.write(f"\n## Final status\n\n{status}\n")
        return state
    except Exception as error:
        state["status"] = "error"
        state["error"] = f"{type(error).__name__}: {error}"
        state["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_json(state_path, state)
        with evidence.open("a", encoding="utf-8") as out:
            out.write(f"\n## Runner error\n\n{state['error']}\n")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--max-iterations", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--resume", action="store_true", help="continue an existing incomplete run")
    args = parser.parse_args()
    if not 1 <= args.max_iterations <= 10 or not 1 <= args.timeout <= 3600:
        parser.error("max iterations must be 1..10 and timeout 1..3600 seconds")
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    state = run_goal(args.goal, args.run_dir, config, args.max_iterations, args.timeout, args.resume)
    print("GOAL_STATUS: " + state["status"])
    raise SystemExit(0 if state["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
