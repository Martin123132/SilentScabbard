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

First setup may download the small `llama3.2:3b` base model through Ollama.

To inspect the install without launching the app:

```powershell
.\health-check.ps1
```

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
- vault file: `data\vault.json`
- session logs: `data\sessions`

Ollama settings can be overridden with:

```powershell
$env:RONIN_OLLAMA_EXE = 'D:\AI\Ollama\app\ollama.exe'
$env:RONIN_OLLAMA_MODELS = 'D:\AI\Ollama\models'
```

For a permanent local override, create `ronin.local.ps1`. This file is ignored by Git.

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

The gear button opens the vault viewer. From there you can search, save the last exchange, delete selected items, or promote a selected vault title into memory.

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
