# Changelog

## 0.4.0

- Added skin profile tooling for full and layered artwork modes.
- Added `check-skin-assets.ps1` and `CHECK_SKIN_WINDOWS.bat`.
- Added `set-skin-profile.ps1`, `USE_FULL_SKIN_WINDOWS.bat`, and `USE_LAYERED_SKIN_WINDOWS.bat`.
- Added a layered manifest template and `assets\layers` drop-folder docs.
- Added required-layer handling so incomplete layered skins fall back safely.

## 0.3.0

- Added optional layered skin loading through `assets\skin_manifest.json`.
- Added `assets\README.md` with the artwork replacement workflow.
- Kept `assets\ronin_skin.png` as the current full-window fallback layer.
- Preserved plain fallback rendering if no usable skin assets are found.

## 0.2.0

- Added a Settings window behind the gear button.
- Added editable Ollama executable, model storage, model name, and API URL settings.
- Persisted app settings to `data\settings.json`.
- Wrote local overrides to `ronin.local.ps1` when settings are saved.
- Added in-app health check, data-folder shortcut, Vault shortcut, and model rebuild action.
- Updated command-line health and run scripts to respect the configured model name.

## 0.1.0

Initial public foundation for SilentScabbard / Ronin.

- Local Tkinter desktop UI with the current Ronin skin.
- Ollama-backed `ronin` model using the included `Modelfile`.
- Explicit-only local memory under `data\memory.json`.
- Session logs under `data\sessions`.
- Ronin Vault under `data\vault.json` for curated saved exchanges.
- One-click Windows setup via `START_HERE_WINDOWS.bat`.
- Desktop shortcut installer.
- D-drive friendly Ollama model storage defaults.
- Health check tooling for install diagnostics.
