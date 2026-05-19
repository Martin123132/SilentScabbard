param(
    [string]$Manifest = 'assets\skin_manifest.json',
    [switch]$CheckOnly,
    [double]$CloseAfter = 0
)

$ErrorActionPreference = 'Stop'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$localConfig = Join-Path $appDir 'ronin.local.ps1'
if (Test-Path $localConfig) {
    . $localConfig
}

function Find-Python {
    param([switch]$PreferConsole)

    if ($PreferConsole) {
        $candidates = @(
            $env:RONIN_PYTHON,
            (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
            (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
            (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
            $env:RONIN_PYTHONW
        )
    } else {
        $candidates = @(
            $env:RONIN_PYTHONW,
            $env:RONIN_PYTHON,
            (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\pythonw.exe'),
            (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\pythonw.exe'),
            (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\pythonw.exe')
        )
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    throw 'Python 3 was not found. Install Python 3.11+ or set RONIN_PYTHONW.'
}

$preview = Join-Path $appDir 'preview_skin.pyw'
if (-not (Test-Path $preview)) {
    throw "Preview tool was not found: $preview"
}

$manifestPath = $Manifest
if (-not [System.IO.Path]::IsPathRooted($manifestPath)) {
    $manifestPath = Join-Path $appDir $manifestPath
}

$preferConsole = $CheckOnly -or ($CloseAfter -gt 0)
$python = Find-Python -PreferConsole:$preferConsole
$previewArgs = @($preview, '--manifest', $manifestPath)
if ($CheckOnly) {
    $previewArgs += '--check-only'
}
if ($CloseAfter -gt 0) {
    $previewArgs += @('--close-after', ([string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0}', $CloseAfter)))
}

if ($preferConsole) {
    & $python @previewArgs
    exit $LASTEXITCODE
}

Start-Process -FilePath $python -ArgumentList @("`"$preview`"", '--manifest', "`"$manifestPath`"") -WorkingDirectory $appDir
