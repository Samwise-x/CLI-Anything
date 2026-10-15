"""Unit tests for NotebookLM harness scaffold."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cli_anything.notebooklm.core.session import Session
from cli_anything.notebooklm.utils.notebooklm_backend import (
    build_command,
    command_supports_json,
    require_notebooklm,
    run_notebooklm,
    sanitize_error,
)


class TestBackendDiscovery:
    def test_require_notebooklm_returns_path(self):
        with patch("cli_anything.notebooklm.utils.notebooklm_backend.shutil.which", return_value="/usr/local/bin/notebooklm"):
            assert require_notebooklm() == "/usr/local/bin/notebooklm"

    def test_require_notebooklm_raises_with_install_guidance(self):
        with patch("cli_anything.notebooklm.utils.notebooklm_backend.shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="notebooklm command not found"):
                require_notebooklm()


class TestCommandBuilder:
    def test_build_command_with_notebook_id_and_json(self):
        command = build_command(
            ["source", "list"],
            notebook_id="nb_123",
            json_output=True,
        )
        assert command == [
            "notebooklm",
            "source",
            "list",
            "-n",
            "nb_123",
            "--json",
        ]

    def test_build_command_without_notebook_id(self):
        command = build_command(["list"])
        assert command == ["notebooklm", "list"]

    def test_command_supports_json_for_verified_command(self):
        assert command_supports_json(["download", "report"]) is True

    def test_command_supports_json_rejects_unsupported_command(self):
        assert command_supports_json(["login"]) is False


class TestRunNotebooklm:
    def test_run_notebooklm_rejects_json_for_unsupported_command(self):
        with patch("cli_anything.notebooklm.utils.notebooklm_backend.subprocess.run") as run_mock:
            with pytest.raises(RuntimeError, match="JSON output is not supported for command: login"):
                run_notebooklm(["login"], json_output=True)
        run_mock.assert_not_called()

    def test_run_notebooklm_applies_a_bounded_timeout(self):
        completed = type("Completed", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
        with patch("cli_anything.notebooklm.utils.notebooklm_backend.require_notebooklm", return_value="notebooklm.exe"), \
             patch("cli_anything.notebooklm.utils.notebooklm_backend.subprocess.run", return_value=completed) as run_mock:
            assert run_notebooklm(["status"]) == "ok"
        assert run_mock.call_args.kwargs["timeout"] == 120

    def test_run_notebooklm_reports_a_timeout_without_stalling(self):
        import subprocess

        with patch("cli_anything.notebooklm.utils.notebooklm_backend.require_notebooklm", return_value="notebooklm.exe"), \
             patch("cli_anything.notebooklm.utils.notebooklm_backend.subprocess.run", side_effect=subprocess.TimeoutExpired("notebooklm", 120)):
            with pytest.raises(RuntimeError, match="timed out"):
                run_notebooklm(["status"])


class TestErrorSanitization:
    def test_sanitize_error_redacts_storage_state_path(self):
        raw = "Failed to open /Users/tester/.notebooklm/storage_state.json because auth expired"
        assert "storage_state.json" not in sanitize_error(raw)
        assert "[redacted-auth-path]" in sanitize_error(raw)


class TestSession:
    def test_session_persists_active_notebook(self, tmp_path):
        session_file = tmp_path / "session.json"
        session = Session(session_file=session_file)
        session.set_active_notebook("nb_abc")

        reloaded = Session(session_file=session_file)
        assert reloaded.get_active_notebook() == "nb_abc"

    def test_session_clear_active_notebook(self, tmp_path):
        session_file = tmp_path / "session.json"
        session = Session(session_file=session_file)
        session.set_active_notebook("nb_abc")
        session.clear_active_notebook()

        data = json.loads(Path(session_file).read_text())
        assert data["active_notebook"] is None

    def test_non_object_session_state_is_recovered_as_empty(self, tmp_path):
        session_file = tmp_path / "session.json"
        session_file.write_text("[]", encoding="utf-8")

        assert Session(session_file=session_file).get_active_notebook() is None


class TestPackagingFixtures:
    def test_acknowledgements_reference_external_projects(self):
        readme = Path("cli_anything/notebooklm/README.md").read_text(encoding="utf-8")
        assert "CLI-Anything" in readme
        assert "notebooklm-py" in readme

    def test_readme_documents_install_test_and_safety_sections(self):
        readme = Path("cli_anything/notebooklm/README.md").read_text(encoding="utf-8")
        assert "## Install" in readme
        assert "## Run Tests" in readme
        assert "## Safety Notes" in readme
        assert "Google NotebookLM" in readme

    def test_skill_file_contains_usage_and_boundary_guidance(self):
        skill = Path("cli_anything/notebooklm/skills/SKILL.md").read_text(encoding="utf-8")
        assert "## Installation" in skill
        assert "## Usage" in skill
        assert "unofficial" in skill.lower()
        assert "not affiliated with Google" in skill

    def test_skill_file_exists(self):
        assert Path("cli_anything/notebooklm/skills/SKILL.md").is_file()
