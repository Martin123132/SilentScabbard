$ErrorActionPreference = 'Stop'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$localConfig = Join-Path $appDir 'ronin.local.ps1'
if (Test-Path $localConfig) {
    . $localConfig
}

function Find-Pythonw {
    $candidates = @(
        $env:RONIN_PYTHONW,
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\pythonw.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\pythonw.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\pythonw.exe')
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    $python = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }

    throw 'Python 3 was not found. Install Python 3.11+ or set RONIN_PYTHONW.'
}

if (-not $env:OLLAMA_MODELS) {
    if ($env:RONIN_OLLAMA_MODELS) {
        $env:OLLAMA_MODELS = $env:RONIN_OLLAMA_MODELS
    } elseif (Test-Path 'D:\') {
        $env:OLLAMA_MODELS = 'D:\AI\Ollama\models'
    } else {
        $env:OLLAMA_MODELS = Join-Path $appDir 'data\ollama-models'
    }
}

New-Item -ItemType Directory -Force -Path $env:OLLAMA_MODELS | Out-Null

$pythonw = Find-Pythonw
$app = Join-Path $appDir 'ronin_desktop.pyw'
Start-Process -FilePath $pythonw -ArgumentList "`"$app`"" -WorkingDirectory $appDir -WindowStyle Hidden
