# Troubleshooting

Run `CHECK_INSTALL_WINDOWS.bat` first. It prints the paths SilentScabbard is using and whether the local model is ready.

## Python Missing

Install Python 3.11 or newer from:

<https://www.python.org/downloads/windows/>

Then run `START_HERE_WINDOWS.bat` again.

## Ollama Missing

Install Ollama for Windows from:

<https://ollama.com/download/windows>

Then run `START_HERE_WINDOWS.bat` again.

## Ronin Model Missing

Run:

```powershell
.\setup-windows.ps1
```

The first run may download the small base model through Ollama.

## C Drive Model Cache Is Growing

Set a larger model directory before setup:

```powershell
$env:RONIN_OLLAMA_MODELS = 'D:\AI\Ollama\models'
.\setup-windows.ps1
```

`CHECK_INSTALL_WINDOWS.bat` reports the size of `C:\Users\<you>\.ollama\models`.

## App Opens But Does Not Answer

Run `CHECK_INSTALL_WINDOWS.bat` and confirm:

- Ollama API is `ready`
- Ronin model is `present`
- model directory points to the intended drive

If Ollama was just installed, wait a minute and run setup again.
