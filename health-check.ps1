$ErrorActionPreference = 'Continue'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$localConfig = Join-Path $appDir 'ronin.local.ps1'
if (Test-Path $localConfig) {
    . $localConfig
}

function Get-AppSettings {
    $settingsPath = Join-Path $appDir 'data\settings.json'
    if (-not (Test-Path $settingsPath)) {
        return $null
    }
    try {
        return Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

$appSettings = Get-AppSettings

function Find-ExistingPath {
    param([string[]]$Candidates)
    foreach ($candidate in $Candidates) {
        if ($candidate -and (Test-Path $candidate)) {
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

function Get-ShortcutStatus {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $shortcutPath = Join-Path $desktop 'Ronin.lnk'
    if (-not (Test-Path -LiteralPath $shortcutPath)) {
        return [pscustomobject]@{
            Ready = $false
            Text = "missing ($shortcutPath)"
        }
    }

    try {
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $expectedTarget = [System.IO.Path]::GetFullPath((Join-Path $appDir 'launch-ronin.vbs'))
        $actualTarget = [System.IO.Path]::GetFullPath($shortcut.TargetPath)
        if ($actualTarget.Equals($expectedTarget, [System.StringComparison]::OrdinalIgnoreCase)) {
            return [pscustomobject]@{
                Ready = $true
                Text = "ready ($shortcutPath)"
            }
        }
        return [pscustomobject]@{
            Ready = $false
            Text = "points elsewhere ($actualTarget)"
        }
    } catch {
        return [pscustomobject]@{
            Ready = $false
            Text = "could not inspect ($shortcutPath)"
        }
    }
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

$python = Find-Python
$pythonw = Find-Pythonw
$ollama = Find-Ollama
$modelDir = Resolve-ModelDir
$modelName = Resolve-ModelName
$cDefaultModels = Join-Path $env:USERPROFILE '.ollama\models'
$settingsReady = Test-Path -LiteralPath (Join-Path $appDir 'data\settings.json')
$localOverrideReady = Test-Path -LiteralPath $localConfig
$shortcutStatus = Get-ShortcutStatus
$cDrive = Get-PSDrive C -ErrorAction SilentlyContinue
$dDrive = Get-PSDrive D -ErrorAction SilentlyContinue
$apiReady = $false
$roninModel = $false
$ollamaVersion = 'not available'

try {
    $version = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2
    $apiReady = $true
    $ollamaVersion = $version.version
} catch {}

if ($ollama -and $apiReady) {
    try {
        $modelList = Invoke-OllamaList -Ollama $ollama -ModelDir $modelDir
        if ($null -ne $modelList) {
            $modelPattern = "(?m)^$([regex]::Escape($modelName))(?::latest)?\s"
            $roninModel = [bool]($modelList -match $modelPattern)
        }
    } catch {}
}

Write-Host ''
Write-Host 'SilentScabbard health check' -ForegroundColor DarkYellow
Write-Host ''
Write-Host "App folder:       $appDir"
Write-Host "Python:           $(if ($python) { $python } else { 'missing' })"
Write-Host "Pythonw:          $(if ($pythonw) { $pythonw } else { 'missing' })"
Write-Host "Ollama:           $(if ($ollama) { $ollama } else { 'missing' })"
Write-Host "Ollama API:       $(if ($apiReady) { 'ready' } else { 'not ready' })"
Write-Host "Ollama version:   $ollamaVersion"
Write-Host "Model name:       $modelName"
Write-Host "Model directory:  $modelDir"
Write-Host "Model present:    $(if ($roninModel) { 'yes' } else { 'no' })"
Write-Host "Settings file:    $(if ($settingsReady) { 'ready' } else { 'missing' })"
Write-Host "Local override:   $(if ($localOverrideReady) { 'ready' } else { 'missing' })"
Write-Host "Desktop shortcut: $($shortcutStatus.Text)"
Write-Host "C model cache:    $(Get-DirectorySizeGB $cDefaultModels) GB ($cDefaultModels)"

Get-PSDrive C,D -ErrorAction SilentlyContinue |
    Select-Object Name,@{Name='FreeGB';Expression={[math]::Round($_.Free / 1GB, 2)}} |
    Format-Table -AutoSize

Write-Host 'Expected install file: START_HERE_WINDOWS.bat'
Write-Host 'Expected repair file:  REPAIR_INSTALL_WINDOWS.bat'
Write-Host 'Expected launch file:  launch-ronin.vbs'
Write-Host ''

if ($cDrive -and $cDrive.Free -lt 8GB) {
    Write-Host "Warning: C: has only $([math]::Round($cDrive.Free / 1GB, 2)) GB free. Keep models on D: when possible." -ForegroundColor Yellow
}
if ($dDrive -and $dDrive.Free -lt 10GB) {
    Write-Host "Warning: D: has only $([math]::Round($dDrive.Free / 1GB, 2)) GB free." -ForegroundColor Yellow
}
if ((Test-Path 'D:\') -and $modelDir -notlike 'D:\*') {
    Write-Host "Warning: D: exists, but model directory is not on D: $modelDir" -ForegroundColor Yellow
}
if ($modelDir -like 'C:\Users\*\.ollama*') {
    Write-Host "Warning: model directory points at the default C cache: $modelDir" -ForegroundColor Yellow
}

if (-not $python -or -not $pythonw -or -not $ollama -or -not $roninModel -or -not $settingsReady -or -not $localOverrideReady -or -not $shortcutStatus.Ready) {
    Write-Host 'Health: needs setup or repair.' -ForegroundColor Yellow
    Write-Host 'Run REPAIR_INSTALL_WINDOWS.bat to refresh settings and the shortcut without deleting local data.' -ForegroundColor Yellow
    Write-Host 'Run START_HERE_WINDOWS.bat if the local model is missing and needs to be created.' -ForegroundColor Yellow
    exit 1
}

Write-Host 'Health: ready.' -ForegroundColor Green
