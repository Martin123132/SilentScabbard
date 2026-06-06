# SilentScabbard

SilentScabbard is a local Windows desktop shell for Ronin, a stoic samurai AI that runs through Ollama. No API key is needed.

The current build is intentionally small: a Tkinter desktop UI, local memory, session logs, and a curated vault for useful exchanges.

## One-Click Windows Setup

1. Install Python 3.11+ if needed.
2. Install Ollama if needed: <https://ollama.com/download/windows>
3. Download or clone this repo.
4. Double-click `START_HERE_WINDOWS.bat`.

The setup script:

- finds Python and Ollama
- keeps model storage on `D:\AI\Ollama\models` when a D drive exists
- creates the local `ronin` model from `Modelfile`
- creates a Desktop shortcut named `Ronin`
- does not delete local memory, vault, sessions, skins, or existing model files
- provides dependency-check messaging on launch for missing Python/Ollama before the app starts
- health check now validates launch script and app file presence to catch shortcut/packaging drift

First setup may download the small `llama3.2:3b` base model through Ollama.

To inspect the install without launching the app:

```powershell
.\health-check.ps1
```

Or double-click `CHECK_INSTALL_WINDOWS.bat`.

To repair settings, the Desktop shortcut, and local path config without rebuilding the model or deleting local data, double-click `REPAIR_INSTALL_WINDOWS.bat`.

If something fails, see `TROUBLESHOOTING.md`.

## Release Zip

Maintainers can build a clean release zip from tracked files only:

```powershell
.\make-release-zip.ps1
```

The zip is written to `dist` and excludes runtime data, local memory, session logs, model files, and local override config.

## Manual Run

Open the desktop app:

```powershell
.\launch-ronin.ps1
```

Or run the model in a terminal:

```powershell
.\run-ronin.ps1
```

If your repo is somewhere else, run the same scripts from that folder.

## Local Paths

The app resolves paths dynamically:

- app folder: folder containing `ronin_desktop.pyw`
- local app data: `data`
- memory file: `data\memory.json`
- settings file: `data\settings.json`
- vault file: `data\vault.json`
- session logs: `data\sessions`

Ollama settings can be overridden with:

```powershell
$env:RONIN_OLLAMA_EXE = 'D:\AI\Ollama\app\ollama.exe'
$env:RONIN_OLLAMA_MODELS = 'D:\AI\Ollama\models'
```

For a permanent local override, use the Settings window or create `ronin.local.ps1`. This file is ignored by Git.

## Settings

Click the gear button in the top bar to open Settings.

Settings can edit:

- Ollama executable path
- model storage path
- model name
- local Ollama API URL
- character-surface layout toggle (Surface mode: on by default)
- Stoic Riddle mode toggle (default off)

The Settings window can also run a health check, run **Repair Install** (with health summary), open Skin Tools, open the Vault, open the local data folder, and rebuild the local model from `Modelfile`.

If you change Surface layout, save first and use `Restart App` to re-launch the app with the new layout immediately.

At startup, the top-mode banner shows:

- Surface mode
- Persona mode
- Ollama status and the model drive letter, with color cues for connection state (ready/starting/failing).
- If dependencies are misconfigured, the status and meaning area also shows the next setup step and points users to **Settings → Repair Install**.

## Skin Assets

The current app can load artwork from `assets\skin_manifest.json`.

Right now the manifest draws the existing `assets\ronin_skin.png` as one full-window layer. Future art can be split into replaceable PNG layers such as room, samurai, and foreground without changing the Python UI code.

See `assets\README.md` for the layer format.

Useful skin commands:

```powershell
.\check-skin-assets.ps1
.\preview-skin.ps1
.\preview-skin.ps1 -Manifest assets\skin_manifest.layered.example.json
.\import-layered-skin.ps1 -SourceFolder D:\Path\To\LayerPngs
.\set-skin-profile.ps1 -SkinProfile full
.\set-skin-profile.ps1 -SkinProfile layered
```

For a double-click check, use `CHECK_SKIN_WINDOWS.bat`.

For a double-click preview, use `PREVIEW_SKIN_WINDOWS.bat`.

For double-click import, use `IMPORT_LAYERED_SKIN_WINDOWS.bat` and choose a folder containing `room.png`, `foreground.png`, and optional `samurai.png`.

For double-click profile switching, use `USE_FULL_SKIN_WINDOWS.bat` or `USE_LAYERED_SKIN_WINDOWS.bat`.

Inside Ronin, open Settings and click `Skin Tools` to check the active skin, preview it, import layered artwork, switch profiles, or open the layer folder.

## Memory

Memory is explicit-only. Ronin remembers only when you tell it to.

Examples:

```text
remember this: I like short answers
my name is Martin
call me Ollet
forget everything
```

The Memory button toggles whether saved memory is included in prompts. Session logs still continue either way.

## Ronin Vault

The vault is a curated archive for useful exchanges. It is separate from memory: saving something to the vault does not automatically inject it into future prompts.

Commands:

```text
save this
vault this
save this: title | tag-one, tag-two
tag this: useful, local
search vault: words to find
vault
```

Open the Vault from Settings, or use the `vault` command. From there you can search, save the last exchange, delete selected items, or promote a selected vault title into memory.

## Rebuild The Personality

Edit:

```text
Modelfile
```

Then run:

```powershell
$env:OLLAMA_MODELS = 'D:\AI\Ollama\models'
& 'D:\AI\Ollama\app\ollama.exe' create ronin -f '.\Modelfile'
```

## Privacy

SilentScabbard is local-first. Runtime data is stored in the local `data` folder and is ignored by Git by default.
