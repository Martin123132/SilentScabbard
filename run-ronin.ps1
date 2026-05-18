$ErrorActionPreference = 'Stop'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$localConfig = Join-Path $appDir 'ronin.local.ps1'
if (Test-Path $localConfig) {
    . $localConfig
}

function Find-Ollama {
    $candidates = @(
        $env:RONIN_OLLAMA_EXE,
        'D:\AI\Ollama\app\ollama.exe',
        (Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe')
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    $cmd = Get-Command ollama.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    throw 'Ollama was not found. Install Ollama or set RONIN_OLLAMA_EXE.'
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
$ollama = Find-Ollama

try {
    Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2 | Out-Null
} catch {
    Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden
    for ($i = 0; $i -lt 30; $i++) {
        try {
            Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2 | Out-Null
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
}

& $ollama run ronin
