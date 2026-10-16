import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

MODULE_PATH = Path(__file__).parents[1] / "goal_loop.py"
SPEC = importlib.util.spec_from_file_location("goal_loop", MODULE_PATH)
goal_loop = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(goal_loop)


class GoalLoopContractTests(unittest.TestCase):
    def fixture(self, root, executor_text="print('GOAL_STATUS: complete')\n",
                evaluator_text="print('REVIEW: pass')\n", verify_text="raise SystemExit(0)\n"):
        executor = root / "executor.py"
        evaluator = root / "evaluator.py"
        verify = root / "verify.py"
        executor.write_text(executor_text, encoding="utf-8")
        evaluator.write_text(evaluator_text, encoding="utf-8")
        verify.write_text(verify_text, encoding="utf-8")
        goal = root / "goal.md"
        goal.write_text("Make a safe change.", encoding="utf-8")
        config = {
            "executor": [sys.executable, str(executor)],
            "evaluator": [sys.executable, str(evaluator)],
            "verify": [[sys.executable, str(verify)]],
        }
        return goal, config

    def test_rejects_missing_adapters_and_verification(self):
        with self.assertRaisesRegex(ValueError, "executor"):
            goal_loop.validate_config({"executor": [], "evaluator": [], "verify": []})

    def test_executor_and_evaluator_must_be_separate(self):
        config = {"executor": [sys.executable, "agent.py"],
                  "evaluator": [sys.executable, "agent.py"],
                  "verify": [[sys.executable, "-m", "unittest"]]}
        with self.assertRaisesRegex(ValueError, "independent"):
            goal_loop.validate_config(config)

    def test_rejects_malformed_verification_command(self):
        config = {"executor": ["python", "exec.py"], "evaluator": ["python", "review.py"],
                  "verify": [["python"], []]}
        with self.assertRaisesRegex(ValueError, "nonempty"):
            goal_loop.validate_config(config)

    def test_executor_model_pool_requires_distinct_model_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            goal, config = self.fixture(Path(directory))
            config["executor_models"] = ["opencode/a", "opencode/a"]
            with self.assertRaisesRegex(ValueError, "distinct"):
                goal_loop.validate_config(config)

    def test_model_failover_requires_explicit_model_placeholder(self):
        with tempfile.TemporaryDirectory() as directory:
            goal, config = self.fixture(Path(directory))
            config["executor_models"] = ["opencode/a", "opencode/b"]
            with self.assertRaisesRegex(ValueError, "model"):
                goal_loop.validate_config(config)

    def test_model_pool_recovers_from_observed_socket_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal, config = self.fixture(root)
            attempted = root / "models"
            executor = root / "executor-model.py"
            executor.write_text(
                "import json,pathlib,sys\n"
                f"p=pathlib.Path({str(attempted)!r})\n"
                "model=sys.argv[1]\n"
                "with p.open('a') as out: out.write(model+'\\n')\n"
                "if model.endswith('/a'):\n"
                " print(json.dumps({'type':'error','error':{'type':'unknown','message':'Transport: The socket connection was closed unexpectedly.'}}))\n"
                " raise SystemExit(1)\n"
                "print('GOAL_STATUS: complete')\n",
                encoding="utf-8",
            )
            config["executor"] = [sys.executable, str(executor), "{model}"]
            config["executor_models"] = ["opencode/a", "opencode/b"]
            result = goal_loop.run_goal(goal, root / "run", config, 1, 10)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(attempted.read_text().splitlines(), ["opencode/a", "opencode/b"])

    def test_model_pool_stops_after_failure_trace_contains_tool_event(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal, config = self.fixture(root)
            attempted = root / "models"
            executor = root / "executor-model.py"
            executor.write_text(
                "import pathlib,sys\n"
                f"p=pathlib.Path({str(attempted)!r})\n"
                "model=sys.argv[1]\n"
                "with p.open('a') as out: out.write(model+'\\n')\n"
                "print('{\"type\":\"tool\",\"tool\":\"edit\",\"state\":{\"status\":\"running\"}}')\n"
                "print('{\"type\":\"error\",\"error\":{\"message\":\"HTTP 503 overloaded\"}}')\n"
                "raise SystemExit(1)\n",
                encoding="utf-8",
            )
            config["executor"] = [sys.executable, str(executor), "{model}"]
            config["executor_models"] = ["opencode/a", "opencode/b"]
            result = goal_loop.run_goal(goal, root / "run", config, 1, 10)
            self.assertEqual(result["status"], "incomplete")
            self.assertEqual(attempted.read_text().splitlines(), ["opencode/a"])

    def test_model_pool_advances_only_on_safe_provider_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal, config = self.fixture(root)
            attempted = root / "models"
            executor = root / "executor-model.py"
            executor.write_text(
                "import pathlib,sys\n"
                f"p=pathlib.Path({str(attempted)!r})\n"
                "model=sys.argv[1]\n"
                "with p.open('a') as out: out.write(model+'\\n')\n"
                "if model.endswith('/a'):\n"
                " print('{\"type\":\"step_start\"}')\n"
                " print('{\"type\":\"error\",\"error\":{\"message\":\"HTTP 503 overloaded\"}}')\n"
                " raise SystemExit(1)\n"
                "print('GOAL_STATUS: complete')\n",
                encoding="utf-8",
            )
            config["executor"] = [sys.executable, str(executor), "{model}"]
            config["executor_models"] = ["opencode/a", "opencode/b", "opencode/c"]
            result = goal_loop.run_goal(goal, root / "run", config, 1, 10)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(attempted.read_text().splitlines(), ["opencode/a", "opencode/b"])
            evidence = (root / "run" / "evidence.md").read_text()
            self.assertIn("opencode/a", evidence)
            self.assertIn("opencode/b", evidence)

    def test_loop_persists_evidence_and_passes_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal, config = self.fixture(root)
            run_dir = root / "run"
            result = goal_loop.run_goal(goal, run_dir, config, 2, 10)
            self.assertEqual(result["status"], "complete")
            saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "complete")
            self.assertEqual(json.loads((run_dir / "verification.json").read_text())[0]["exit_code"], 0)
            self.assertIn("Final status", (run_dir / "evidence.md").read_text())

    def test_verification_failure_never_calls_evaluator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "reviewed"
            goal, config = self.fixture(root, verify_text="raise SystemExit(7)\n")
            config["evaluator"] = [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch(); print('REVIEW: pass')"]
            result = goal_loop.run_goal(goal, root / "run", config, 1, 10)
            self.assertEqual(result["status"], "incomplete")
            self.assertFalse(marker.exists())

    def test_evaluator_rejection_keeps_goal_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal, config = self.fixture(root, evaluator_text="print('REVIEW: revise')\n")
            result = goal_loop.run_goal(goal, root / "run", config, 1, 10)
            self.assertEqual(result["status"], "incomplete")

    def test_iteration_budget_is_enforced_and_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            counter = root / "count"
            script = root / "executor-budget.py"
            script.write_text(
                "from pathlib import Path\np=Path(" + repr(str(counter)) + ")\nn=int(p.read_text())+1 if p.exists() else 1\np.write_text(str(n))\nprint('GOAL_STATUS: complete' if n >= 2 else 'GOAL_STATUS: incomplete')\n",
                encoding="utf-8")
            goal, config = self.fixture(root)
            config["executor"] = [sys.executable, str(script)]
            result = goal_loop.run_goal(goal, root / "run", config, 2, 10)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["iteration"], 2)


    def test_incomplete_run_resumes_without_erasing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal, config = self.fixture(root, executor_text="print('GOAL_STATUS: incomplete')\n")
            run_dir = root / "run"
            first = goal_loop.run_goal(goal, run_dir, config, 1, 10)
            self.assertEqual(first["status"], "incomplete")
            prior = (run_dir / "evidence.md").read_text()
            (root / "executor.py").write_text("print('GOAL_STATUS: complete')\n", encoding="utf-8")
            second = goal_loop.run_goal(goal, run_dir, config, 2, 10, resume=True)
            self.assertEqual(second["status"], "complete")
            self.assertEqual(second["iteration"], 2)
            evidence = (run_dir / "evidence.md").read_text()
            self.assertIn(prior, evidence)
            self.assertIn("## Resume", evidence)

    def test_resume_rejects_a_different_goal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal, config = self.fixture(root, executor_text="print('GOAL_STATUS: incomplete')\n")
            run_dir = root / "run"
            goal_loop.run_goal(goal, run_dir, config, 1, 10)
            other = root / "other.md"
            other.write_text("Different goal", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                goal_loop.run_goal(other, run_dir, config, 2, 10, resume=True)
    def test_timeout_is_persisted_as_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal, config = self.fixture(root, executor_text="import time; time.sleep(2)\n")
            with self.assertRaises(__import__("subprocess").TimeoutExpired):
                goal_loop.run_goal(goal, root / "run", config, 1, 1)
            state = json.loads((root / "run" / "state.json").read_text())
            self.assertEqual(state["status"], "error")
            self.assertIn("TimeoutExpired", state["error"])


    def test_embedded_success_markers_do_not_pass(self):
        for executor, evaluator in [("print('GOAL_STATUS: complete is only an example')", "print('REVIEW: pass')"), ("print('GOAL_STATUS: complete')", "print('Do not output REVIEW: pass\\nREVIEW: revise')")]:
            with self.subTest(executor=executor, evaluator=evaluator), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                goal, config = self.fixture(root, executor_text=executor, evaluator_text=evaluator)
                self.assertEqual(goal_loop.run_goal(goal, root / "run", config, 1, 10)["status"], "incomplete")

    def test_json_text_events_pass_terminal_marker_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executor = "print(" + repr(json.dumps({"type": "text", "part": {"text": "GOAL_STATUS: complete"}})) + ")"
            evaluator = "print(" + repr(json.dumps({"type": "text", "part": {"text": "REVIEW: pass"}})) + ")"
            goal, config = self.fixture(root, executor_text=executor, evaluator_text=evaluator)
            self.assertEqual(goal_loop.run_goal(goal, root / "run", config, 1, 10)["status"], "complete")

    def test_existing_run_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal, config = self.fixture(root)
            run = root / "run"
            goal_loop.run_goal(goal, run, config, 1, 10)
            prior = (run / "evidence.md").read_bytes()
            with self.assertRaisesRegex(ValueError, "existing"):
                goal_loop.run_goal(goal, run, config, 1, 10)
            self.assertEqual((run / "evidence.md").read_bytes(), prior)

    def test_active_run_lock_rejects_concurrent_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal, config = self.fixture(root)
            run = root / "run"
            run.mkdir()
            (run / ".lock").write_text("active")
            with self.assertRaisesRegex(ValueError, "locked"):
                goal_loop.run_goal(goal, run, config, 1, 10)
            self.assertFalse((run / "state.json").exists())

    def test_resume_rejects_changed_goal_or_config(self):
        for change in ("goal", "config"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                goal, config = self.fixture(root, executor_text="print('GOAL_STATUS: incomplete')")
                run = root / "run"
                goal_loop.run_goal(goal, run, config, 1, 10)
                if change == "goal":
                    goal.write_text("changed")
                else:
                    config["verify"] = [[sys.executable, "-c", "pass"]]
                with self.assertRaisesRegex(ValueError, "changed"):
                    goal_loop.run_goal(goal, run, config, 2, 10, resume=True)
                self.assertFalse((run / ".lock").exists())

    def test_running_resume_keeps_existing_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal, config = self.fixture(root, evaluator_text="print('REVIEW: revise')")
            run = root / "run"
            goal_loop.run_goal(goal, run, config, 1, 10)
            state = json.loads((run / "state.json").read_text())
            state["status"] = "running"
            (run / "state.json").write_text(json.dumps(state))
            prior = (run / "executor-1.log").read_bytes()
            result = goal_loop.run_goal(goal, run, config, 2, 10, resume=True)
            self.assertEqual(result["iteration"], 2)
            self.assertEqual((run / "executor-1.log").read_bytes(), prior)
            self.assertTrue((run / "verify-1-1.log").exists())
            self.assertTrue((run / "verify-2-1.log").exists())
            self.assertTrue((run / "verification-1.json").exists())
            self.assertTrue((run / "verification-2.json").exists())
            self.assertFalse((run / ".lock").exists())

    def test_timeout_kills_descendant_process(self):
        import subprocess
        import time
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "child"
            child = "import time,pathlib; time.sleep(0.6); pathlib.Path(" + repr(str(marker)) + ").touch()"
            parent = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c'," + repr(child) + "]); time.sleep(5)"
            with self.assertRaises(subprocess.TimeoutExpired):
                goal_loop._run([sys.executable, "-c", parent], root, 0.1)
            time.sleep(0.8)
            self.assertFalse(marker.exists())


    def test_timeout_allows_sigterm_cleanup(self):
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "cleaned"
            script = "import signal,sys,time,pathlib; signal.signal(signal.SIGTERM, lambda *_: (pathlib.Path(" + repr(str(marker)) + ").touch(), sys.exit(0))); print('ready', flush=True); time.sleep(5)"
            with self.assertRaises(subprocess.TimeoutExpired):
                goal_loop._run([sys.executable, "-c", script], root, 0.3)
            self.assertTrue(marker.exists())

    def test_timeout_kills_detached_output_child_that_ignores_sigterm(self):
        import subprocess
        import time
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "survived"
            child = "import signal,time,pathlib; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(0.9); pathlib.Path(" + repr(str(marker)) + ").touch(); time.sleep(3)"
            parent = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c'," + repr(child) + "], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(5)"
            with self.assertRaises(subprocess.TimeoutExpired):
                goal_loop._run([sys.executable, "-c", parent], root, 0.3)
            time.sleep(1)
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
