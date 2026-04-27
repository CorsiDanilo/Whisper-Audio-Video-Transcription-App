"""
Source: https://github.com/whitphx/gradio-pyinstaller-example

To generate .exe file: 
pyinstaller app_main.py --collect-data gradio --collect-data gradio_client --additional-hooks-dir=./hooks --runtime-hook ./runtime_hook.py --add-data --noconfirm --icon=logo.ico --distpath=./dist/whisper_with_cmd --name=Whisper
pyinstaller app_main.py --collect-data gradio --collect-data gradio_client --additional-hooks-dir=./hooks --runtime-hook ./runtime_hook.py --noconsole --noconfirm --icon=logo.ico --distpath=./dist/whisper_no_cmd --name=Whisper

Or simply run the following command:
pyinstaller --noconfirm whisper.spec

Troubleshooting:
1 - PyInstaller cannot check for assembly dependencies
    Solution:
        Source: https://stackoverflow.com/questions/59638691/pyinstaller-cannot-check-for-assembly-dependencies
        Navigate to your python directory -> Lib -> site-packages -> Pyinstaller. Open compat.py and look for the following:

            if is_win:
                try:
                    from win32ctypes.pywin32 import pywintypes  # noqa: F401
                    from win32ctypes.pywin32 import win32api
                except ImportError:
                    # This environment variable is set by setup.py
                    # - It's not an error for pywin32 to not be installed at that point
                    if not os.environ.get('PYINSTALLER_NO_PYWIN32_FAILURE'):
                        raise SystemExit('PyInstaller cannot check for assembly dependencies.\n'
                                    'Please install pywin32-ctypes.\n\n'
                                    'pip install pywin32-ctypes\n')

        Change both of those import statements to import the modules themselves instead of trying to grab them from win32ctypes.pywin32.

            #from win32ctypes.pywin32 import pywintypes  # noqa: F401
            #from win32ctypes.pywin32 import win32api
            import pywintypes
            import win32api

        And install:
        
            pip install pypiwin32

2 - FileNotFoundError: [Errno 2] No such file or directory: '...\\app\\_internal\\safehttpx\\version.txt'
    Solution:
        Navigate to your python directory -> Lib -> site-packages, copy the safehttpx folder and paste it into your python directory -> dist -> app -> _internal

3 - failed:Load model 'C:...\\app\\_internal\\faster_whisper\\assets\\silero_encoder_v5.onnx' failed. File doesn't exist
    Solution:
        Navigate to your python directory -> Lib -> site-packages, copy the faster_whisper folder and paste it into your python directory -> dist -> app -> _internal
"""

import webview
import threading
import sys
import os
import pystray
from PIL import Image

from main import demo as main 

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
    if hasattr(sys, '_MEIPASS'):
        icon_path = os.path.join(sys._MEIPASS, 'logo.ico')
    else:
        icon_path = 'logo.ico'
        
    try:
        image = Image.open(icon_path)
    except FileNotFoundError:
        image = Image.new('RGB', (64, 64), color = 'white')
        
    menu = pystray.Menu(
        pystray.MenuItem('Mostra / Nascondi App', on_show),
        pystray.MenuItem('Esci', on_quit)
    )
    
    icon = pystray.Icon("WhisperApp", image, "Whisper Audio/Video Utility", menu)
    icon.run()

main.launch(prevent_thread_lock=True)

tray_thread = threading.Thread(target=setup_tray, daemon=True)
tray_thread.start()

webview.create_window("🎙️ Whisper Audio/Video Transcription App", main.local_url)
webview.start()