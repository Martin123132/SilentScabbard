$ErrorActionPreference = 'Stop'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$localConfig = Join-Path $appDir 'ronin.local.ps1'
$settingsPath = Join-Path $appDir 'data\settings.json'

function Get-AppSettings {
    if (-not (Test-Path -LiteralPath $settingsPath)) {
        return $null
    }
    try {
        return Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

$appSettings = Get-AppSettings
if (Test-Path -LiteralPath $localConfig) {
    . $localConfig
}

function Find-ExistingPath {
    param([string[]]$Candidates)
    foreach ($candidate in $Candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

function Find-Python {
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    return Find-ExistingPath @(
        $env:RONIN_PYTHON,
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
        $(if ($cmd) { $cmd.Source } else { $null })
    )
}

function Find-Pythonw {
    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    return Find-ExistingPath @(
        $env:RONIN_PYTHONW,
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\pythonw.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\pythonw.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\pythonw.exe'),
        $(if ($cmd) { $cmd.Source } else { $null })
    )
}

function Find-Ollama {
    $cmd = Get-Command ollama.exe -ErrorAction SilentlyContinue
    return Find-ExistingPath @(
        $env:RONIN_OLLAMA_EXE,
        $(if ($appSettings -and $appSettings.ollama_exe) { $appSettings.ollama_exe } else { $null }),
        'D:\AI\Ollama\app\ollama.exe',
        (Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'),
        $(if ($cmd) { $cmd.Source } else { $null })
    )
}

function Resolve-ModelDir {
    if ($env:RONIN_OLLAMA_MODELS) {
        return $env:RONIN_OLLAMA_MODELS
    }
    if ($env:OLLAMA_MODELS) {
        return $env:OLLAMA_MODELS
    }
    if ($appSettings -and $appSettings.ollama_models) {
        return $appSettings.ollama_models
    }
    if (Test-Path 'D:\') {
        return 'D:\AI\Ollama\models'
    }
    return (Join-Path $appDir 'data\ollama-models')
}

function Resolve-ModelName {
    if ($env:RONIN_MODEL_NAME) {
        return $env:RONIN_MODEL_NAME
    }
    if ($appSettings -and $appSettings.model_name) {
        return $appSettings.model_name
    }
    return 'ronin'
}

function Wait-Ollama {
    param([int]$Seconds = 20)

    for ($i = 0; $i -lt $Seconds; $i++) {
        try {
            Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2 | Out-Null
            return $true
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    return $false
}

function Write-LocalOverride {
    param(
        [string]$Ollama,
        [string]$ModelDir,
        [string]$ModelName
    )

    @"
`$env:RONIN_OLLAMA_EXE = '$Ollama'
`$env:RONIN_OLLAMA_MODELS = '$ModelDir'
`$env:OLLAMA_MODELS = '$ModelDir'
`$env:RONIN_MODEL_NAME = '$ModelName'
"@ | Set-Content -LiteralPath $localConfig -Encoding UTF8
}

Write-Host ''
Write-Host 'SilentScabbard repair' -ForegroundColor DarkYellow
Write-Host 'This refreshes local settings, D-drive model path config, and the Desktop shortcut.' -ForegroundColor Gray
Write-Host 'It does not delete memory, vault, sessions, skins, or model files.' -ForegroundColor Gray
Write-Host ''

$python = Find-Python
$pythonw = Find-Pythonw
$ollama = Find-Ollama
$modelDir = Resolve-ModelDir
$modelName = Resolve-ModelName
$api = if ($appSettings -and $appSettings.ollama_api) { $appSettings.ollama_api } else { 'http://127.0.0.1:11434' }

if (-not $python) {
    Write-Host 'Python 3.11+ was not found.' -ForegroundColor Red
    Write-Host 'Install Python from https://www.python.org/downloads/windows/ then run repair again.'
    exit 1
}
if (-not $pythonw) {
    Write-Host 'pythonw.exe was not found. Repair will continue, but the app may open a console window.' -ForegroundColor Yellow
}
if (-not $ollama) {
    Write-Host 'Ollama was not found.' -ForegroundColor Red
    Write-Host 'Install Ollama from https://ollama.com/download/windows/ then run repair again.'
    exit 1
}

if ((Test-Path 'D:\') -and $modelDir -notlike 'D:\*') {
    Write-Host "D: exists, but model storage is not on D: $modelDir" -ForegroundColor Yellow
    Write-Host 'Repair will preserve the configured path. Change it in Settings if this is not intended.' -ForegroundColor Yellow
}
if ($modelDir -like 'C:\Users\*\.ollama*') {
    Write-Host "Warning: model storage points at the default C cache: $modelDir" -ForegroundColor Yellow
}

New-Item -ItemType Directory -Force -Path (Join-Path $appDir 'data') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $appDir 'data\sessions') | Out-Null
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null

Write-LocalOverride -Ollama $ollama -ModelDir $modelDir -ModelName $modelName
$env:RONIN_OLLAMA_EXE = $ollama
$env:RONIN_OLLAMA_MODELS = $modelDir
$env:OLLAMA_MODELS = $modelDir
$env:RONIN_MODEL_NAME = $modelName

@{
    model_name = $modelName
    ollama_exe = $ollama
    ollama_models = $modelDir
    ollama_api = $api
} | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $settingsPath -Encoding UTF8

Write-Host "Python: $python"
Write-Host "Pythonw: $(if ($pythonw) { $pythonw } else { 'not found' })"
Write-Host "Ollama: $ollama"
Write-Host "Models: $modelDir"
Write-Host "Model name: $modelName"
Write-Host ''

Write-Host 'Refreshing Desktop shortcut...'
& (Join-Path $appDir 'install-shortcut.ps1') | Out-Host

try {
    Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2 | Out-Null
} catch {
    Write-Host ''
    Write-Host 'Starting local Ollama service for health check...'
    Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden
    if (-not (Wait-Ollama -Seconds 45)) {
        Write-Host 'Ollama did not become ready in time. Health check will report what still needs attention.' -ForegroundColor Yellow
    }
}

Write-Host ''
Write-Host 'Running health check...'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $appDir 'health-check.ps1')
$healthExit = $LASTEXITCODE

if ($healthExit -ne 0) {
    Write-Host ''
    Write-Host 'Repair finished, but health still needs attention.' -ForegroundColor Yellow
    Write-Host 'If the model is missing, run START_HERE_WINDOWS.bat once to build/download it into the configured model folder.' -ForegroundColor Yellow
    exit $healthExit
}

Write-Host ''
Write-Host 'Repair complete. SilentScabbard is ready.' -ForegroundColor Green
exit 0
