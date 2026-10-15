from click.testing import CliRunner


def test_backup_all_sanitizes_server_workflow_id_before_path_join(tmp_path, monkeypatch):
    from cli_anything.n8n import n8n_cli

    monkeypatch.setattr(
        n8n_cli.workflows, "list_workflows",
        lambda **kwargs: {"data": [{"id": "../escaped", "name": "Fixture"}]},
    )
    monkeypatch.setattr(
        n8n_cli.workflows, "get_workflow",
        lambda workflow_id, **kwargs: {
            "id": workflow_id, "name": "Fixture", "nodes": [], "connections": {},
        },
    )
    backup = tmp_path / "backup"
    result = CliRunner().invoke(
        n8n_cli.cli,
        ["--url", "https://n8n.example", "--api-key", "synthetic-key",
         "workflow", "backup-all", "--dir", str(backup)],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "escaped_Fixture.json").exists() is False
    assert list(backup.glob("*.json"))
