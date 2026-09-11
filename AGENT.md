# AGENT.md

## 1. Executable Commands

* Source CPU dependencies: `python -m pip install -r requirements_cpu.txt`.
* Source NVIDIA/CUDA dependencies: `python -m pip install -r requirements_gpu.txt`.
* Linux/macOS source dependencies: use `requirements_linux.txt` or `requirements_macos.txt` respectively.
* Docker dependencies: use `docker compose --profile cpu up --build` or `docker compose --profile gpu up --build`.
* Core release build: `python tools/build_release.py` (runs PyInstaller with `whisper.spec` and writes to `dist/`).
* Development run: `python main.py` (Gradio server on `127.0.0.1:7860`).
* Automated Docker launcher: Windows `run.bat`; Linux/macOS `chmod +x run.sh && ./run.sh`.
* Lint autofix: `python -m ruff check --fix .` followed by `python -m ruff format .`.
* Read-only lint check: `python -m ruff check .` followed by `python -m ruff format --check .`.
* Full test suite: Not configured; no `tests/` directory or pytest configuration is present.
* Targeted test/single-file validation: use `python -m py_compile path\to\file.py` for a changed Python file.
* Type checking: Not configured; neither mypy nor pyright is configured.

## 2. Operational Boundaries

### Always Do

* Run commands from the repository root because application configuration uses relative `settings/` paths.
* Inspect neighboring code and reuse existing abstractions and conventions.
* For bugs, reproduce the issue with the smallest available harness; otherwise use syntax validation and a relevant manual check.
* Keep the diff limited to files required by the task.
* Run the narrowest relevant validation after changing Python or YAML.

### Ask First

* Adding or upgrading dependencies, requirement files, Docker images, or CUDA runtimes.
* Changing release URLs/versions in `installer/manifest.json` or the packaging workflow.
* Changing persistent configuration keys, public interfaces, authentication, or security behavior.
* Renaming or deleting shared components.

### Never Do

* Never commit secrets, credentials, tokens, `.env` files, or `secrets/gemini.yaml`.
* Never bypass the path validators in `security_utils.py` or clean outside controlled temporary storage.
* Never disable or delete existing checks to make validation pass.
* Never mass-format or broadly refactor files outside the task scope.
* Never manually edit generated `build/`, `dist/`, cache, or user-output files unless explicitly requested.

## 3. Repository-Specific Constraints

* `main.py` is the development and Docker entry point; `app_main.py` is reserved for the PyInstaller desktop package.
* Use `requirements_cpu.txt`/`requirements_gpu.txt` for source installs and `requirements_docker_cpu.txt`/`requirements_docker_gpu.txt` only in Dockerfiles; CI uses Python 3.11 and `uv`.
* FFmpeg must be on `PATH` for source runs; Docker images install it internally. GPU execution requires a working NVIDIA container runtime.
* User configuration is loaded from system AppData before local `settings/`; Gemini credentials must come from `GEMINI_API_KEY` or protected system configuration.
* Non-loopback or shared Gradio launches require both `WHISPER_GRADIO_AUTH_USER` and `WHISPER_GRADIO_AUTH_PASSWORD`.
* Docker persists user outputs in `outputs/` and model weights in the `whisper_models_cache` volume; do not package user data.
