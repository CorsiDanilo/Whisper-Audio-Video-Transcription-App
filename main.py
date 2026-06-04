from ui import demo
from security_utils import get_gradio_launch_kwargs

if __name__ == "__main__":
    demo.launch(**get_gradio_launch_kwargs(debug=True))
