"""Provider isolation and rollback must be established before live use."""
import json
import runpy
from pathlib import Path
from click.testing import CliRunner
from cli_anything.ccswitch.ccswitch_cli import cli


def fixture_db(tmp_path):
    init=runpy.run_path(str(Path(__file__).with_name('test_core.py')))['_init_cli_db']
    path=tmp_path/'fixture.db'
    db=init(path)
    db.execute('INSERT INTO providers (id,app_type,name,settings_config,is_current) VALUES (?,?,?,?,?)',('new','codex','Fixture',json.dumps({'config':'model = "fixture-model"\n','auth':{'OPENAI_API_KEY':'synthetic-test-key'}}),0))
    db.commit();db.close()
    return path


def test_explicit_live_home_confines_provider_writes(tmp_path):
    db=fixture_db(tmp_path)
    live=tmp_path/'managed'
    result=CliRunner().invoke(cli,['--db',str(db),'--live-home',str(live),'providers','set-current','new','--app','codex'])
    assert result.exit_code == 0,result.output
    assert 'fixture-model' in (live/'.codex/config.toml').read_text()
    assert json.loads((live/'.codex/auth.json').read_text()) == {'OPENAI_API_KEY':'synthetic-test-key'}


def test_failed_auth_write_restores_config_and_database(tmp_path):
    import sqlite3
    db=fixture_db(tmp_path)
    live=tmp_path/'managed'
    codex=live/'.codex'
    codex.mkdir(parents=True)
    target=codex/'config.toml'
    target.write_text('model = "before"\n',encoding='utf-8')
    (codex/'auth.json').mkdir()  # a real filesystem failure, no mocked writer
    result=CliRunner().invoke(cli,['--db',str(db),'--live-home',str(live),'providers','set-current','new','--app','codex'])
    assert result.exit_code != 0
    assert target.read_text() == 'model = "before"\n'
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT is_current FROM providers WHERE id="new"').fetchone()[0] == 0


def test_database_override_requires_explicit_live_destination(tmp_path,monkeypatch):
    db=fixture_db(tmp_path)
    synthetic_home=tmp_path/'unselected-home'
    # Upstream writers use expanduser; confine the regression even while red.
    monkeypatch.setenv('USERPROFILE',str(synthetic_home))
    monkeypatch.setenv('HOME',str(synthetic_home))
    result=CliRunner().invoke(cli,['--db',str(db),'providers','set-current','new','--app','codex'])
    assert result.exit_code != 0
    assert not synthetic_home.exists()


def test_output_failure_after_commit_preserves_committed_files(tmp_path,monkeypatch):
    import sqlite3
    import click
    db=fixture_db(tmp_path)
    live=tmp_path/'managed'
    (live/'.codex').mkdir(parents=True)
    config=live/'.codex/config.toml'
    config.write_text('model = "before"\n',encoding='utf-8')
    original=click.echo
    def broken_output(message=None,*args,**kwargs):
        if isinstance(message,str) and message.startswith('Switched'):
            raise BrokenPipeError('consumer closed output')
        return original(message,*args,**kwargs)
    monkeypatch.setattr(click,'echo',broken_output)
    CliRunner().invoke(cli,['--db',str(db),'--live-home',str(live),'providers','set-current','new','--app','codex'])
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT is_current FROM providers WHERE id="new"').fetchone()[0] == 1
    assert 'fixture-model' in config.read_text()


def test_restore_continues_after_one_managed_file_restore_fails(tmp_path,monkeypatch):
    import cli_anything.ccswitch.ccswitch_cli as module
    db=fixture_db(tmp_path)
    live=tmp_path/'managed'
    codex=live/'.codex'
    codex.mkdir(parents=True)
    config=codex/'config.toml'
    auth=codex/'auth.json'
    config.write_bytes(b'old-config\n')
    auth.write_bytes(b'{"old":true}\n')

    def partially_write_then_fail(app, connection, live_home=None):
        config.write_bytes(b'new-config\n')
        auth.write_bytes(b'{"new":true}\n')
        raise OSError('synthetic post-write failure')

    real_replace=module._os.replace
    restored=[]
    def fail_first_restore(source,destination):
        if Path(destination)==config and Path(source).name.startswith('.rollback-'):
            raise PermissionError('synthetic locked config')
        result=real_replace(source,destination)
        if Path(destination)==auth and Path(source).name.startswith('.rollback-'):
            restored.append(Path(destination))
        return result

    monkeypatch.setattr(module,'_write_live_config',partially_write_then_fail)
    monkeypatch.setattr(module._os,'replace',fail_first_restore)
    result=CliRunner().invoke(cli,['--db',str(db),'--live-home',str(live),'providers','set-current','new','--app','codex'])

    assert result.exit_code != 0
    assert restored == [auth]
    assert auth.read_bytes() == b'{"old":true}\n'
    assert 'filesystem restoration also failed' in str(result.exception)


def test_explicit_live_home_rejects_symlinked_managed_directory(tmp_path):
    import sqlite3
    db = fixture_db(tmp_path)
    live = tmp_path / "managed"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "config.toml").write_text('model = "outside-before"\n', encoding="utf-8")
    live.mkdir()
    (live / ".codex").symlink_to(outside, target_is_directory=True)

    result = CliRunner().invoke(
        cli, ["--db", str(db), "--live-home", str(live),
              "providers", "set-current", "new", "--app", "codex"]
    )

    assert result.exit_code != 0, "managed path symlink escaped the explicit live-home sandbox"
    assert (outside / "config.toml").read_text(encoding="utf-8") == 'model = "outside-before"\n'
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT is_current FROM providers WHERE id="new"').fetchone()[0] == 0


def test_explicit_live_home_rejects_symlinked_config_file(tmp_path):
    import sqlite3
    db = fixture_db(tmp_path)
    live = tmp_path / "managed"
    codex = live / ".codex"
    outside = tmp_path / "outside.toml"
    outside.write_text('model = "outside-before"\n', encoding="utf-8")
    codex.mkdir(parents=True)
    (codex / "config.toml").symlink_to(outside)

    result = CliRunner().invoke(
        cli, ["--db", str(db), "--live-home", str(live),
              "providers", "set-current", "new", "--app", "codex"]
    )

    assert result.exit_code != 0
    assert outside.read_text(encoding="utf-8") == 'model = "outside-before"\n'
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT is_current FROM providers WHERE id="new"').fetchone()[0] == 0
