$ErrorActionPreference = 'Stop'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$localConfig = Join-Path $appDir 'ronin.local.ps1'
if (Test-Path $localConfig) {
    . $localConfig
}

function Find-Python {
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    $candidates = @(
        $env:RONIN_PYTHON,
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
        $(if ($cmd) { $cmd.Source } else { $null })
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }
    return $null
}

function Find-Pythonw {
    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    $candidates = @(
        $env:RONIN_PYTHONW,
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\pythonw.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\pythonw.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\pythonw.exe'),
        $(if ($cmd) { $cmd.Source } else { $null })
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }
    return $null
}

function Find-Ollama {
    $cmd = Get-Command ollama.exe -ErrorAction SilentlyContinue
    $candidates = @(
        $env:RONIN_OLLAMA_EXE,
        'D:\AI\Ollama\app\ollama.exe',
        (Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'),
        $(if ($cmd) { $cmd.Source } else { $null })
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }
    return $null
}

function Resolve-ModelDir {
    if ($env:RONIN_OLLAMA_MODELS) {
        return $env:RONIN_OLLAMA_MODELS
    }
    if ($env:OLLAMA_MODELS) {
        return $env:OLLAMA_MODELS
    }
    if (Test-Path 'D:\') {
        return 'D:\AI\Ollama\models'
    }
    return (Join-Path $appDir 'data\ollama-models')
}

if (-not $env:OLLAMA_MODELS) {
    $env:OLLAMA_MODELS = Resolve-ModelDir
}

$modelDir = $env:OLLAMA_MODELS
if (Test-Path 'D:\') {
    if ($modelDir -notlike 'D:\*') {
        Write-Host "Note: D: exists but model cache is not on D: $modelDir" -ForegroundColor Yellow
    }
    if ($modelDir -like 'C:\Users\*\.ollama*') {
        Write-Host "Warning: model cache is on default C cache: $modelDir" -ForegroundColor Yellow
    }
}

Write-Host 'Preparing SilentScabbard launch...' -ForegroundColor DarkYellow
$python = Find-Python
$pythonw = Find-Pythonw
$ollama = Find-Ollama

if (-not $python) {
    Write-Host 'Python 3 was not found. Install Python 3.11+ and run setup/repair again.' -ForegroundColor Red
    Write-Host 'Download: https://www.python.org/downloads/windows/' -ForegroundColor Gray
    exit 1
}

if (-not $ollama) {
    Write-Host 'Ollama was not found. Install Ollama and run setup/repair before launching.' -ForegroundColor Red
    Write-Host 'Download: https://ollama.com/download/windows/' -ForegroundColor Gray
    exit 1
}

if (-not (Test-Path $modelDir)) {
    New-Item -ItemType Directory -Force -Path $modelDir | Out-Null
}

Write-Host "Python: $python"
Write-Host "Launch runtime: $(if ($pythonw) { $pythonw } else { "$python (fallback)" })"
Write-Host "Ollama: $ollama"
Write-Host "Model cache: $modelDir"

$app = Join-Path $appDir 'ronin_desktop.pyw'

if ($pythonw) {
    if ($pythonw -eq $python) {
        Write-Host 'pythonw.exe was not found; launching with python.exe. A console window may appear.' -ForegroundColor Yellow
    }
    Start-Process -FilePath $pythonw -ArgumentList "`"$app`"" -WorkingDirectory $appDir -WindowStyle Hidden
} else {
    Start-Process -FilePath $python -ArgumentList "`"$app`"" -WorkingDirectory $appDir -WindowStyle Minimized
}
