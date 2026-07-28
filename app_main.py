import webview
import threading
import time
import sys
import os
import ctypes
from ctypes import wintypes
import pystray
from PIL import Image

# Set Windows AppUserModelID so Taskbar displays custom icon instead of Python logo
if sys.platform == 'win32':
    try:
        app_id = 'CorsiDanilo.WhisperUtility.App'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

from config import get_translation as _
from main import demo as main 
from security_utils import get_gradio_launch_kwargs

def get_icon_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'logo.ico')
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_rel = os.path.join(script_dir, 'logo.ico')
    if os.path.exists(icon_rel):
        return icon_rel
    return os.path.abspath('logo.ico')

def apply_window_icon():
    if sys.platform != 'win32':
        return
    icon_path = get_icon_path()
    if not os.path.exists(icon_path):
        return

    try:
        user32 = ctypes.windll.user32
        pid = os.getpid()
        
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        LR_LOADFROMFILE = 0x0010
        IMAGE_ICON = 1

        user32.LoadImageW.argtypes = [
            wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
            ctypes.c_int, ctypes.c_int, wintypes.UINT
        ]
        user32.LoadImageW.restype = wintypes.HANDLE

        user32.SendMessageW.argtypes = [
            wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
        ]
        user32.SendMessageW.restype = wintypes.LPARAM

        h_icon = user32.LoadImageW(0, os.path.abspath(icon_path), IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
        if not h_icon:
            return

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def enum_windows_callback(hwnd, lParam):
            window_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            if window_pid.value == pid and user32.IsWindowVisible(hwnd):
                user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon)
                user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon)
            return True

        cb = WNDENUMPROC(enum_windows_callback)
        user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
        user32.EnumWindows.restype = wintypes.BOOL
        user32.EnumWindows(cb, 0)
    except Exception:
        pass

def delayed_icon_setter():
    # Retry applying icon as the webview window initializes
    for _ in range(8):
        time.sleep(0.5)
        apply_window_icon()

def on_show(icon, item):
    if webview.windows:
        window = webview.windows[0]
        window.show()
        window.restore()

def on_quit(icon, item):
    icon.stop()
    if webview.windows:
        webview.windows[0].destroy()
    sys.exit(0)

def setup_tray():
    icon_path = get_icon_path()
    try:
        image = Image.open(icon_path)
    except Exception:
        image = Image.new('RGB', (64, 64), color='white')
        
    menu = pystray.Menu(
        pystray.MenuItem(_('tray_show_hide'), on_show),
        pystray.MenuItem(_('tray_exit'), on_quit)
    )
    
    icon = pystray.Icon("WhisperApp", image, "Whisper Audio/Video Utility", menu)
    icon.run()

from ui import custom_css

main.launch(css=custom_css, **get_gradio_launch_kwargs(prevent_thread_lock=True))

tray_thread = threading.Thread(target=setup_tray, daemon=True)
tray_thread.start()

icon_thread = threading.Thread(target=delayed_icon_setter, daemon=True)
icon_thread.start()

window = webview.create_window("🎙️ Whisper Audio/Video Transcription App", main.local_url, width=1280, height=1280)
webview.start()
