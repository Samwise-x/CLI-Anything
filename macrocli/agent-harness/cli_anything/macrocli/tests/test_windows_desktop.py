"""Read-only accessibility against an owned window, with no focus/input."""
import sys
import threading
import uuid
import pytest

pytestmark=pytest.mark.skipif(sys.platform != 'win32',reason='Windows native fixture')


def test_semantic_controls_can_inspect_owned_window():
    import win32api
    import win32con
    import win32gui
    from cli_anything.macrocli.backends.semantic_ui import SemanticUIBackend
    from cli_anything.macrocli.backends.base import BackendContext
    from cli_anything.macrocli.core.macro_model import MacroStep
    title='MacroCLI pressure '+uuid.uuid4().hex
    ready=threading.Event()
    stop=threading.Event()
    errors=[]
    def window_thread():
        handle=None
        try:
            cls=win32gui.WNDCLASS()
            cls.hInstance=win32api.GetModuleHandle(None)
            cls.lpszClassName=title
            cls.lpfnWndProc=win32gui.DefWindowProc
            atom=win32gui.RegisterClass(cls)
            handle=win32gui.CreateWindowEx(win32con.WS_EX_NOACTIVATE,atom,title,win32con.WS_OVERLAPPEDWINDOW,30,30,300,150,0,0,cls.hInstance,None)
            win32gui.CreateWindowEx(0,'Button','Owned fixture button',win32con.WS_CHILD|win32con.WS_VISIBLE,10,10,180,30,handle,1,cls.hInstance,None)
            win32gui.ShowWindow(handle,win32con.SW_SHOWNOACTIVATE)
            ready.set()
            while not stop.wait(0.01):win32gui.PumpWaitingMessages()
        except BaseException as exc:
            errors.append(str(exc));ready.set()
        finally:
            if handle:win32gui.DestroyWindow(handle)
    thread=threading.Thread(target=window_thread,daemon=True)
    thread.start()
    try:
        assert ready.wait(5)
        assert not errors,errors
        result=SemanticUIBackend().execute(MacroStep(backend='semantic_ui',action='get_controls',params={'window_title':title}),{},BackendContext({}))
        assert result.success,result.error
        assert any(item['name']=='Owned fixture button' and item['role']=='Button' for item in result.output['controls'])
    finally:
        stop.set();thread.join(5)
