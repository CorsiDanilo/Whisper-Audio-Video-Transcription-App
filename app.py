"""
Source: https://github.com/whitphx/gradio-pyinstaller-example

To generate .exe file: 
pyinstaller app.py --collect-data gradio --collect-data gradio_client --additional-hooks-dir=./hooks --runtime-hook ./runtime_hook.py

Troubleshooting:
1 - PyInstaller cannot check for assembly dependencies
    Solution:
        - Source: https://stackoverflow.com/questions/59638691/pyinstaller-cannot-check-for-assembly-dependencies
        Navigate to your python directory -> Lib -> site-packages -> Pyinstaller. Open compat.py and look for the following:
        ```
            if is_win:
                try:
                    from win32ctypes.pywin32 import pywintypes  # noqa: F401
                    from win32ctypes.pywin32 import win32api
                except ImportError:
                    # This environment variable is set by seutp.py
                    # - It's not an error for pywin32 to not be installed at that point
                    if not os.environ.get('PYINSTALLER_NO_PYWIN32_FAILURE'):
                        raise SystemExit('PyInstaller cannot check for assembly dependencies.\n'
                                    'Please install pywin32-ctypes.\n\n'
                                    'pip install pywin32-ctypes\n')
        ```
        Change both of those import statements to import the modules themselves instead of trying to grab them from win32ctypes.pywin32.
        ```
            #from win32ctypes.pywin32 import pywintypes  # noqa: F401
            #from win32ctypes.pywin32 import win32api
            import pywintypes
            import win32api
        ```
"""
import webview

from whisper_app import demo as whisper_app 

whisper_app.launch(prevent_thread_lock=True)

webview.create_window("🎙️ Whisper Audio/Video Transcription App", whisper_app.local_url)
webview.start()