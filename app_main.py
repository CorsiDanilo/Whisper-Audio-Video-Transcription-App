import webview
import threading
import sys
import os
import pystray
from PIL import Image

from config import get_translation as _
from main import demo as main 
from security_utils import get_gradio_launch_kwargs

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
        pystray.MenuItem(_('tray_show_hide'), on_show),
        pystray.MenuItem(_('tray_exit'), on_quit)
    )
    
    icon = pystray.Icon("WhisperApp", image, "Whisper Audio/Video Utility", menu)
    icon.run()

from ui import custom_css

main.launch(css=custom_css, **get_gradio_launch_kwargs(prevent_thread_lock=True))
tray_thread = threading.Thread(target=setup_tray, daemon=True)
tray_thread.start()

webview.create_window("🎙️ Whisper Audio/Video Transcription App", main.local_url)
webview.start()
