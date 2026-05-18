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

Write-Host ''
Write-Host 'SilentScabbard / Ronin setup' -ForegroundColor DarkYellow
Write-Host 'Local-only. No API key needed.' -ForegroundColor Gray
Write-Host 'Tip: keep the repo on a drive with space. Model files can be a few GB.' -ForegroundColor Gray
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
"@ | Set-Content -LiteralPath $localConfig -Encoding UTF8

$env:RONIN_OLLAMA_EXE = $ollama
$env:RONIN_OLLAMA_MODELS = $modelDir
$env:OLLAMA_MODELS = $modelDir

Write-Host "Python: $python"
Write-Host "Pythonw: $(if ($pythonw) { $pythonw } else { 'not found' })"
Write-Host "Ollama: $ollama"
Write-Host "Models: $modelDir"
Write-Host ''

try {
    Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2 | Out-Null
} catch {
    Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden
    if (-not (Wait-Ollama -Seconds 30)) {
        Write-Host 'Ollama did not become ready in time. Try running setup again in a minute.' -ForegroundColor Red
        exit 1
    }
}

$modelList = (& $ollama list) -join "`n"
if ($modelList -notmatch '(?m)^ronin(?::latest)?\s') {
    Write-Host 'Creating the local ronin model. First run may download the small base model.' -ForegroundColor DarkYellow
    Write-Host 'This can take a while, and the model files will be stored in the model directory above.' -ForegroundColor Gray
    & $ollama create ronin -f (Join-Path $appDir 'Modelfile')
} else {
    Write-Host 'Ronin model already exists.' -ForegroundColor Green
}

& (Join-Path $appDir 'install-shortcut.ps1') | Out-Host
& (Join-Path $appDir 'health-check.ps1') | Out-Host

Write-Host ''
Write-Host 'Done. Double-click the Ronin shortcut on your Desktop.' -ForegroundColor Green
