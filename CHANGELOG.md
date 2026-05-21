# Changelog

## 0.8.0

- Added in-app Skin Tools from Settings.
- Skin Tools can check the active skin, launch preview, import layered artwork, switch full/layered profiles, and open the layer folder.
- Skin actions reuse the existing Windows helper scripts so command-line and in-app behavior stay aligned.

## 0.7.0

- Added `repair-windows.ps1` and `REPAIR_INSTALL_WINDOWS.bat` for one-click install repair.
- Repair refreshes settings, local path overrides, model folder config, and the Desktop shortcut without deleting local data.
- Repair starts the local Ollama service when needed so health checks can verify the model.
- Health checks now report settings, local override, Desktop shortcut, low-drive-space, and risky C-cache path warnings.
- Setup messaging now points users toward repair and makes the no-delete behavior clearer.

## 0.6.0

- Added layered skin import tooling for `room.png`, `foreground.png`, and optional `samurai.png`.
- Added `import-layered-skin.ps1` and `IMPORT_LAYERED_SKIN_WINDOWS.bat`.
- Import validates PNG files before changing installed layers.
- Existing installed layer files are backed up to local runtime data before replacement.
- Successful imports activate the layered profile and open the skin preview.
- Skin check/profile scripts now return explicit exit codes for reliable automation.

## 0.5.0

- Added standalone Tkinter skin preview tooling.
- Added `preview-skin.ps1` and `PREVIEW_SKIN_WINDOWS.bat`.
- Preview supports active and alternate manifests without changing the live skin profile.
- Preview shows canvas details, fallback status, ordered layer status, and missing required/optional assets.

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
