$ErrorActionPreference = 'Stop'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$localConfig = Join-Path $appDir 'ronin.local.ps1'

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

    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    return $null
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

    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
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

function Wait-Ollama {
    param([int]$Seconds = 30)

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

function Get-DirectorySizeGB {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return 0
    }
    $files = Get-ChildItem -LiteralPath $Path -Recurse -File -Force -ErrorAction SilentlyContinue
    if (-not $files) {
        return 0
    }
    $bytes = ($files | Measure-Object -Property Length -Sum).Sum
    return [math]::Round($bytes / 1GB, 4)
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

Write-Host ''
Write-Host 'SilentScabbard / Ronin setup' -ForegroundColor DarkYellow
Write-Host 'Local-only. No API key needed.' -ForegroundColor Gray
Write-Host 'Tip: keep the repo on a drive with space. Model files can be a few GB.' -ForegroundColor Gray
Write-Host 'If setup has already run and something moved, use REPAIR_INSTALL_WINDOWS.bat.' -ForegroundColor Gray
Write-Host ''

$python = Find-Python
if (-not $python) {
    Write-Host 'Python 3.11+ was not found.' -ForegroundColor Red
    Write-Host 'Install Python from https://www.python.org/downloads/windows/ then run this again.'
    exit 1
}

$pythonw = Find-Pythonw
if (-not $pythonw) {
    Write-Host 'pythonw.exe was not found, but python.exe is available.' -ForegroundColor Yellow
    Write-Host 'The app can still launch, but a console window may appear.'
}

$ollama = Find-Ollama
if (-not $ollama) {
    Write-Host 'Ollama was not found.' -ForegroundColor Red
    Write-Host 'Install Ollama from https://ollama.com/download/windows then run this again.'
    exit 1
}

$modelDir = Resolve-ModelDir
$modelName = if ($env:RONIN_MODEL_NAME) { $env:RONIN_MODEL_NAME } else { 'ronin' }
$cDrive = Get-PSDrive C -ErrorAction SilentlyContinue
$cDefaultModels = Join-Path $env:USERPROFILE '.ollama\models'
if ($cDrive -and $cDrive.Free -lt 8GB) {
    Write-Host "Warning: C: has only $([math]::Round($cDrive.Free / 1GB, 2)) GB free. SilentScabbard will keep model storage off C: when possible." -ForegroundColor Yellow
}
if ((Get-DirectorySizeGB $cDefaultModels) -gt 0.1) {
    Write-Host "Warning: default C model cache is not empty: $cDefaultModels" -ForegroundColor Yellow
}
if ($modelDir -like 'C:\Users\*\.ollama*') {
    Write-Host "Warning: model directory appears to be on C: $modelDir" -ForegroundColor Yellow
}
if ($modelDir -like 'C:\*') {
    Write-Host "Warning: model directory is on C:. Set RONIN_OLLAMA_MODELS to a larger drive if needed." -ForegroundColor Yellow
}
if ((Test-Path 'D:\') -and $modelDir -notlike 'D:\*') {
    Write-Host "D: exists, but model directory is not on D: $modelDir" -ForegroundColor Yellow
}

New-Item -ItemType Directory -Force -Path (Join-Path $appDir 'data') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $appDir 'data\sessions') | Out-Null
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null

@"
`$env:RONIN_OLLAMA_EXE = '$ollama'
`$env:RONIN_OLLAMA_MODELS = '$modelDir'
`$env:OLLAMA_MODELS = '$modelDir'
`$env:RONIN_MODEL_NAME = '$modelName'
"@ | Set-Content -LiteralPath $localConfig -Encoding UTF8

$env:RONIN_OLLAMA_EXE = $ollama
$env:RONIN_OLLAMA_MODELS = $modelDir
$env:OLLAMA_MODELS = $modelDir
$env:RONIN_MODEL_NAME = $modelName

Write-Host "Python: $python"
Write-Host "Pythonw: $(if ($pythonw) { $pythonw } else { 'not found' })"
Write-Host "Ollama: $ollama"
Write-Host "Models: $modelDir"
Write-Host "Model name: $modelName"
Write-Host ''
Write-Host 'Setup will not delete memory, vault, sessions, skins, or existing model files.' -ForegroundColor Gray
Write-Host ''

try {
    Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2 | Out-Null
} catch {
    Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden
    if (-not (Wait-Ollama -Seconds 60)) {
        Write-Host 'Ollama did not become ready in time. Try running setup again in a minute.' -ForegroundColor Red
        exit 1
    }
}

$modelList = Invoke-OllamaList -Ollama $ollama -ModelDir $modelDir
if ($null -eq $modelList) {
    Write-Host 'Ollama did not answer the model list request in time. Try running setup again in a minute.' -ForegroundColor Red
    exit 1
}
$modelPattern = "(?m)^$([regex]::Escape($modelName))(?::latest)?\s"
if ($modelList -notmatch $modelPattern) {
    Write-Host "Creating the local $modelName model. First run may download the small base model." -ForegroundColor DarkYellow
    Write-Host 'This can take a while, and the model files will be stored in the model directory above.' -ForegroundColor Gray
    & $ollama create $modelName -f (Join-Path $appDir 'Modelfile')
} else {
    Write-Host "$modelName model already exists." -ForegroundColor Green
}

$settingsPath = Join-Path $appDir 'data\settings.json'
@{
    model_name = $modelName
    ollama_exe = $ollama
    ollama_models = $modelDir
    ollama_api = 'http://127.0.0.1:11434'
} | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $settingsPath -Encoding UTF8

& (Join-Path $appDir 'install-shortcut.ps1') | Out-Host
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $appDir 'health-check.ps1') | Out-Host
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'Done. Double-click the Ronin shortcut on your Desktop.' -ForegroundColor Green
Write-Host 'If paths or the shortcut ever drift, run REPAIR_INSTALL_WINDOWS.bat.' -ForegroundColor Green
