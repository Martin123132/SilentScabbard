$ErrorActionPreference = 'Stop'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$localConfig = Join-Path $appDir 'ronin.local.ps1'
if (Test-Path $localConfig) {
    . $localConfig
}

function Find-Python {
    $candidates = @(
        $env:RONIN_PYTHON,
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe')
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }

    return $null
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

function Get-DriveFreeGb {
    param([string]$Drive)
    $driveInfo = Get-PSDrive -Name $Drive -ErrorAction SilentlyContinue
    if (-not $driveInfo) {
        return $null
    }
    return [math]::Round($driveInfo.Free / 1GB, 2)
}

function Invoke-OllamaList {
    param(
        [string]$Ollama,
        [string]$ModelDir,
        [int]$TimeoutSeconds = 12
    )

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $Ollama
    $startInfo.Arguments = 'list'
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.EnvironmentVariables['OLLAMA_MODELS'] = $ModelDir

    $process = [System.Diagnostics.Process]::Start($startInfo)
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        try {
            $process.Kill()
        } catch {}
        return $null
    }

    return $process.StandardOutput.ReadToEnd()
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

$modelDir = $env:OLLAMA_MODELS
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null

$app = Join-Path $appDir 'ronin_desktop.pyw'
if (-not (Test-Path $app)) {
    Write-Host "App file is missing: $app" -ForegroundColor Red
    Write-Host 'Reinstall the release zip, then use START_HERE_WINDOWS.BAT or REPAIR_INSTALL_WINDOWS.BAT.' -ForegroundColor Yellow
    exit 1
}

$python = Find-Python
$ollama = Find-Ollama
$modelName = if ($env:RONIN_MODEL_NAME) { $env:RONIN_MODEL_NAME } else { 'ronin' }

$cFree = Get-DriveFreeGb 'C'
if ($null -ne $cFree -and $cFree -lt 8) {
    Write-Host "Warning: C: has only $cFree GB free." -ForegroundColor Yellow
}

if (-not $ollama) {
    Write-Host 'Ollama was not found. Install Ollama first: https://ollama.com/download/windows/' -ForegroundColor Red
    Write-Host 'Tip: run REPAIR_INSTALL_WINDOWS.BAT after installing Ollama to refresh launch settings.' -ForegroundColor Gray
    exit 1
}

if (-not (Test-Path $modelDir)) {
    Write-Host "Model directory does not exist and could not be created: $modelDir" -ForegroundColor Red
    exit 1
}

if (-not $python) {
    Write-Host 'Python is missing, but this script still uses Ollama directly.' -ForegroundColor Yellow
    Write-Host 'If the UI cannot start from this folder, install Python 3.11+ and run REPAIR_INSTALL_WINDOWS.BAT.' -ForegroundColor Gray
}

Write-Host "Ollama: $ollama"
Write-Host "Model cache: $modelDir"
Write-Host "Model: $modelName"

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

$modelList = Invoke-OllamaList -Ollama $ollama -ModelDir $modelDir
if ($null -ne $modelList) {
    $modelPattern = '(?m)^' + [regex]::Escape($modelName) + '(?::latest)?\s'
    if (-not ($modelList -match $modelPattern)) {
        Write-Host "Model '$modelName' was not found in '$modelDir'." -ForegroundColor Yellow
        Write-Host 'Run START_HERE_WINDOWS.BAT to build the local model before using run mode.' -ForegroundColor Yellow
    }
}

& $ollama run $modelName
