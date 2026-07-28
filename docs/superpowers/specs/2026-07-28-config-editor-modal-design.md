# Design Spec: Config Files Editor Explanation Modal

## Overview
This feature adds a modal window (`gr.Modal`) to the Config Files Editor section in Whisper Utility (`ui.py`). When the user opens the Config Files Editor or clicks the "Explanation" button, a modal popup displays detailed explanations for both `settings/default.yaml` and `secrets/gemini.yaml` localized in the user's active language (Italian or English).

## Components & Structure

### 1. Localization (`settings/locales.yaml`)
New keys added to both `english` and `italian` blocks:
- `config_modal_title`: Title of the modal dialog.
- `config_modal_btn`: Label for the info/explanation button.
- `config_modal_close_btn`: Label for closing the modal.
- `config_modal_default_yaml_title` & `config_modal_default_yaml_desc`: Title & description of `settings/default.yaml`.
- `config_modal_gemini_yaml_title` & `config_modal_gemini_yaml_desc`: Title & description of `secrets/gemini.yaml`.

### 2. User Interface (`ui.py`)
- Inside `config_menu_accordion`:
  - Add `show_config_info_btn = gr.Button(_("config_modal_btn"), variant="secondary", size="sm")` next to `config_file_selector`.
- Add `with gr.Modal(visible=False) as config_modal:`:
  - Header with `config_modal_title`.
  - Markdown section for `settings/default.yaml`.
  - Separator line.
  - Markdown section for `secrets/gemini.yaml`.
  - Button to close the modal (`close_config_modal_btn`).
- Event Listeners:
  - `show_config_info_btn.click` and `config_menu_accordion.select` set modal visibility to `True`.
  - `close_config_modal_btn.click` sets modal visibility to `False`.

## Verification Plan
1. Run `python -m pytest` to verify translations and UI components load cleanly.
2. Launch `python app_main.py` or test UI manually to confirm the modal opens on demand and displays localized content.
