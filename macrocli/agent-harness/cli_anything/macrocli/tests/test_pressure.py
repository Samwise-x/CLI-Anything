"""Regressions for false success and side effects found during pressure testing."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli_anything.macrocli.core.macro_model import MacroCondition, MacroDefinition, MacroParameter, MacroStep
from cli_anything.macrocli.core.registry import MacroRegistry
from cli_anything.macrocli.core.routing import RoutingEngine
from cli_anything.macrocli.core.runtime import MacroRuntime, _check_condition
from cli_anything.macrocli.macrocli_cli import cli
from cli_anything.macrocli.backends.base import BackendContext


def runtime_for(macro):
    registry = MacroRegistry()
    registry.register(macro)
    return MacroRuntime(registry=registry)


def test_unknown_condition_blocks_execution(tmp_path):
    output = tmp_path / 'must-not-exist.json'
    macro = MacroDefinition(name='unknown', preconditions=[MacroCondition('file_exits', str(output))], steps=[MacroStep(backend='file_transform', action='json_set', params={'input_file':str(output),'path':'ran','value':True})])
    result = runtime_for(macro).execute('unknown', {})
    assert not result.success
    assert not output.exists()


def test_unavailable_requested_backend_never_runs_unrelated_command(tmp_path):
    output = tmp_path / 'must-not-run.txt'
    engine = RoutingEngine()
    # Removing a backend deterministically models a missing installation.
    engine._backends.pop('gui_macro')
    macro = MacroDefinition(name='missing', steps=[MacroStep(backend='gui_macro',action='run_command',params={'command':[sys.executable,'-c',f'from pathlib import Path; Path({str(output)!r}).write_text("wrong backend")']})])
    rt = runtime_for(macro)
    rt.routing = engine
    result = rt.execute('missing', {})
    assert not result.success
    assert not output.exists()


def test_dry_run_does_not_require_produced_output(tmp_path):
    output = tmp_path / 'dry.json'
    macro = MacroDefinition(name='dry', steps=[MacroStep(backend='file_transform',action='json_set',params={'input_file':str(output),'path':'ran','value':True})],postconditions=[MacroCondition('file_exists',str(output))])
    result = runtime_for(macro).execute('dry', {}, dry_run=True)
    assert result.success
    assert not output.exists()


def test_invalid_failure_policy_cannot_hide_failed_step():
    macro = MacroDefinition(name='typo',steps=[MacroStep(backend='native_api',action='run_command',on_failure='faill',params={'command':[sys.executable,'-c','raise SystemExit(2)']})])
    assert not runtime_for(macro).execute('typo', {}).success


@pytest.mark.parametrize('kind,value',[('integer',1.5),('integer',True),('boolean','maybe'),('list','not-a-list'),('dict',[]),('float','not-a-number'),('string',42)])
def test_invalid_parameter_type_is_rejected(kind,value):
    assert MacroParameter(name='value',type=kind).validate_value(value)


def test_failed_dry_run_has_nonzero_cli_exit():
    result = CliRunner().invoke(cli,['--json','macro','dry-run','__missing_macro__'])
    assert result.exit_code != 0


def test_bundled_export_creates_declared_file(tmp_path):
    output=tmp_path/'export.txt'
    result=CliRunner().invoke(cli,['--json','macro','run','export_file','--param',f'output={output.as_posix()}'])
    assert result.exit_code == 0,result.output
    assert output.is_file()
    assert output.read_text(encoding='utf-8').strip() == f'Exported to {output.as_posix()} (format=plain)'


def test_unknown_gui_replay_action_fails_before_execution(tmp_path):
    from cli_anything.macrocli.backends.gui_macro import GUIMacroBackend
    path=tmp_path/'invalid.json'
    path.write_text(json.dumps({'steps':[{'type':'clik'}]}))
    result=GUIMacroBackend().execute(MacroStep(backend='gui_macro',action='replay',params={'macro_file':str(path)}),{},BackendContext({}))
    assert not result.success


def test_gui_replay_honors_step_budget(tmp_path):
    import time
    from cli_anything.macrocli.backends.gui_macro import GUIMacroBackend
    path=tmp_path/'slow.json'
    path.write_text(json.dumps({'steps':[{'type':'sleep','ms':1500}]}))
    start=time.monotonic()
    result=GUIMacroBackend().execute(MacroStep(backend='gui_macro',action='replay',params={'macro_file':str(path)}),{},BackendContext({},timeout_ms=10))
    assert not result.success
    assert time.monotonic()-start < 0.5


@pytest.mark.skipif(sys.platform != 'win32',reason='Windows input encoding')
def test_windows_ctrl_shortcut_encodes_modifier(monkeypatch):
    import pywinauto.keyboard as keyboard
    from cli_anything.macrocli.backends.semantic_ui import SemanticUIBackend
    parsed=[]
    # Only OS input is replaced: pywinauto's real parser checks the encoding.
    monkeypatch.setattr(keyboard,'send_keys',lambda text: parsed.extend(keyboard.parse_keys(text)))
    result=SemanticUIBackend().execute(MacroStep(backend='semantic_ui',action='shortcut',params={'keys':'ctrl+s'}),{},BackendContext({}))
    assert result.success
    assert any(action.key == 17 and action.down and not action.up for action in parsed)


def test_process_launch_uses_platform_null_sink(tmp_path):
    import time
    from cli_anything.macrocli.backends.native_api import NativeAPIBackend
    path=tmp_path/'started.txt'
    result=NativeAPIBackend().execute(MacroStep(backend='native_api',action='start_process',params={'command':[sys.executable,'-c',f'from pathlib import Path; Path({str(path)!r}).write_text("started")']}),{},BackendContext({}))
    assert result.success,result.error
    deadline=time.monotonic()+5
    while not path.exists() and time.monotonic()<deadline:
        time.sleep(0.02)
    assert path.read_text() == 'started'


def test_misspelled_action_does_not_pass_dry_run():
    macro=MacroDefinition(name='bad_action',steps=[MacroStep(backend='file_transform',action='jsoon_set')])
    assert not runtime_for(macro).execute('bad_action',{},dry_run=True).success


def test_session_readers_never_observe_truncated_json(tmp_path):
    import concurrent.futures
    import threading
    from cli_anything.macrocli.core.session import _locked_save_json
    path=tmp_path/'session.json'
    path.write_text('{"state":"before"}')
    encoding=threading.Event()
    proceed=threading.Event()
    class PausingEncoder(json.JSONEncoder):
        def iterencode(self,*args,**kwargs):
            encoding.set()
            proceed.wait(3)
            yield from super().iterencode(*args,**kwargs)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(_locked_save_json,str(path),{'state':'after'},cls=PausingEncoder)
        try:
            assert encoding.wait(2)
            try:
                data=json.loads(path.read_text())
            except json.JSONDecodeError:
                data=None
        finally:
            proceed.set()
            pending.result(timeout=5)
    assert data == {'state':'before'}
    assert json.loads(path.read_text()) == {'state':'after'}


@pytest.mark.parametrize('session_id',['../escape','..','a/b','C:escape'])
def test_session_id_cannot_escape_storage_directory(session_id):
    from cli_anything.macrocli.core.session import ExecutionSession
    with pytest.raises(ValueError):
        ExecutionSession(session_id)


def test_process_condition_cannot_pass_without_verifier(monkeypatch):
    import builtins
    import shutil
    original=builtins.__import__
    def missing_psutil(name,*args,**kwargs):
        if name=='psutil':raise ImportError('optional package absent')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(shutil,'which',lambda name: None)
    monkeypatch.setattr(builtins,'__import__',missing_psutil)
    assert _check_condition(MacroCondition('process_running','__missing_process__'),{}) is not None


@pytest.mark.skipif(sys.platform != 'win32',reason='Windows discovery')
def test_semantic_wait_respects_context_budget():
    import time
    from cli_anything.macrocli.backends.semantic_ui import SemanticUIBackend
    start=time.monotonic()
    result=SemanticUIBackend().execute(MacroStep(backend='semantic_ui',action='wait_for_window',params={'title_contains':'__MacroCLI_nonexistent_unique_window__','timeout_ms':2000}),{},BackendContext({},timeout_ms=10))
    assert not result.success
    assert time.monotonic()-start < 0.5


@pytest.mark.skipif(sys.platform != 'win32',reason='Windows discovery')
def test_semantic_empty_target_cannot_select_arbitrary_window():
    from cli_anything.macrocli.backends.semantic_ui import _win_find_app
    with pytest.raises(RuntimeError):
        _win_find_app('')


def test_replay_requires_the_library_that_executes_inputs(monkeypatch):
    import builtins
    from cli_anything.macrocli.backends.gui_macro import GUIMacroBackend
    original=builtins.__import__
    def no_pyautogui(name,*args,**kwargs):
        if name=='pyautogui':raise ImportError('not installed')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',no_pyautogui)
    assert not GUIMacroBackend().is_available()


def test_dry_run_does_not_record_an_executed_run():
    macro=MacroDefinition(name='plan',steps=[MacroStep(backend='file_transform',action='json_get',params={'input_file':'not-created.json','path':'x'})])
    runtime=runtime_for(macro)
    result=runtime.execute('plan',{},dry_run=True)
    assert result.success
    assert runtime.session.history() == []


def test_menu_dispatch_uses_uia_compatible_interface(monkeypatch):
    from types import SimpleNamespace
    from cli_anything.macrocli.backends import semantic_ui
    # Force the Windows dispatch branch against a strict fake UIA window; no desktop input.
    window=SimpleNamespace(menu_select=lambda path: None)
    monkeypatch.setattr(semantic_ui,'_SYSTEM','Windows')
    monkeypatch.setattr(semantic_ui,'_win_find_app',lambda title: window)
    result=semantic_ui.SemanticUIBackend().execute(MacroStep(backend='semantic_ui',action='menu_click',params={'app_name':'Owned window','menu_path':['File','Open']}),{},BackendContext({}))
    assert result.success,result.error
    assert result.output['menu_path'] == ['File','Open']
