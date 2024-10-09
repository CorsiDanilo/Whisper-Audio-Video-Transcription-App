# 🎙️ Whisper Audio/Video Transcription App
![demo](https://github.com/user-attachments/assets/c8e0aa99-0e50-4758-9ce9-08102646d71c)

## 📝 Description
This project is a transcription app built using the [Faster Whisper model](https://github.com/SYSTRAN/faster-whisper), which transcribes audio and video files into text. It is powered by Gradio for a user-friendly web interface and supports audio or video file uploads for transcription.

## ✨ Features
- 🎧 Transcribe both audio and video files (e.g., MP3, MP4, AVI, etc.)
- ⚖️ Supports multiple model sizes for performance vs. accuracy balance
- 🚀 GPU support for faster transcription using CUDA
- 🎥 Extracts audio from video files automatically
- 🔍 High-precision transcription with options for beam search and other configurations
- 🖥️ Simple UI built with Gradio for easy access and use
- ⬇️ Download the transcript in `.txt` format
- 🎛️ Tuning the model parameters via the interface

## Demo
💻 You can try the Colab version [here](https://colab.research.google.com/drive/16vi9-BhRZZs-ck6KTCkb92gpC8_GXako?usp=sharing) (remember to select GPU in 'Runtime Type' for faster execution ⚡)

## 🛠️ To do/fix
- [ ] 🖥️ AMD Support (if you have an AMD graphics card contact me 📩)
- [ ] You tell me! 🙂

## 📋 Requirements
- 🐍 [Python 3.11+](https://apps.microsoft.com/detail/9ncvdn91xzqp)
- 🔥 [PyTorch](https://pytorch.org) + [CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit) (CUDA version if using GPU)
- 🎬 [FFmpeg](https://www.ffmpeg.org) (must be installed and added to your system's PATH)
- 🖼️ [Gradio](https://www.gradio.app)

## 📦 Installation
### Step 1: Clone the repository

```
git clone https://github.com/CorsiDanilo/whisper-utility.git

```

### Step 2: Set up a virtual environment (optional but recommended):
```
python3 -m venv .venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`

```

### Step 3: Install the required dependencies
```
pip install -r requirements.py
```

### Step 4: Install FFmpeg (if not already installed):
- 🐧 Linux: Install via your package manager (e.g., `sudo apt install ffmpeg`)
- 🍎 macOS: Install via Homebrew (`brew install ffmpeg`)
- 🖥️ Windows: [Download FFmpeg](https://ffmpeg.org/download.html) and add it to your system's PATH.
    - Follow [this guide](https://phoenixnap.com/kb/ffmpeg-windows) to ensure it's in your system's PATH.

### (OPTIONAL) Step 5: Install Pythorch and CUDA Toolkit for NVIDIA GPU
- Download and install [PyTorch](https://pytorch.org/get-started/locally/), in `Compute Platform`
select the last version.
- Download and install [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads).
    - 🐧 Linux: follow [this guide](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/).
    - 🖥️ Windows: follow [this guide](https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/index.html).

## 🚀 Usage
Run the application:
```
python whisper.py 
```
The Gradio interface will open in your default web browser. From there, you can upload an audio or video file, and the transcription will be displayed.

💡 **REMEMBER**: When you are done click `Clear and Close` if you want to clean up the temporary files folder.

## 🎛️ Interface Guide
- **Upload an audio or video file**: Accepts audio formats like MP3, WAV, and video formats like MP4, AVI.
- **Transcribe**: Click this button to start the transcription process.
- **Close and Clear**: This button clears the folder where the file was temporarily stored and closes the application.

## ⚙️ Model Configuration
- **Language**: Set the transcription language. Default is Italian 🇮🇹 (`it`), but you can change it to English 🇬🇧 (`en`) or other languages.
- **Model Size**: By default, the large version of the Whisper model is used (`large-v3`), but you can switch to `small-v3` for smaller, faster models.
- **Device**: The model automatically selects the device based on GPU availability (`cuda` or `cpu`).
- **Beam Size**: Set beam size for decoding. Default is `4`, but you can reduce it to `1` for faster inference.

## 🛠️ Troubleshooting
- If you get the following error: 
    ```
    Could not locate cudnn_ops_infer64_8.dll. Please make sure it is in your library path!
    ```
    Download the missing dll from [here](https://github.com/Purfview/whisper-standalone-win/releases/tag/libs) and put it into the `bin` folder of your `CUDA` installation folder.
    - 🗂️ The usual path is: `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\vXX.X\bin`.

## 📄 License
This project is licensed under the MIT License. See the [LICENSE](https://github.com/CorsiDanilo/whisper-utility/blob/main/LICENSE) file for details.

## 🙏 Acknowledgments
- [Faster Whisper](https://github.com/SYSTRAN/faster-whisper) by Guillaume Klein
- [Gradio](https://www.gradio.app/) for the UI interface

