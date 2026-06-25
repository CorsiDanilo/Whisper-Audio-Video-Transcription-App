from ui import demo, custom_css
from security_utils import get_gradio_launch_kwargs

if __name__ == "__main__":
    demo.launch(css=custom_css, inbrowser=True, **get_gradio_launch_kwargs(debug=True))
