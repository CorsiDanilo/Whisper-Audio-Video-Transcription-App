import webview

from whisper import demo as whisper  # CHANGE THIS LINE

whisper.launch(prevent_thread_lock=True)

# pyinstaller app.py --collect-data gradio --collect-data gradio_client --additional-hooks-dir=./hooks --runtime-hook ./runtime_hook.py

webview.create_window("Gradio App", demo.local_url)  # Change the title if needed
webview.start()