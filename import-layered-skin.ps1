param(
    [string]$SourceFolder,
    [switch]$NoPreview
)

$ErrorActionPreference = 'Stop'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetsDir = Join-Path $appDir 'assets'
$layersDir = Join-Path $assetsDir 'layers'
$dataDir = Join-Path $appDir 'data'
$backupRoot = Join-Path $dataDir 'skin_backups'

function Select-SourceFolder {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = 'Choose a folder containing room.png, foreground.png, and optional samurai.png.'
    $dialog.ShowNewFolderButton = $false
    $result = $dialog.ShowDialog()
    if ($result -ne [System.Windows.Forms.DialogResult]::OK -or -not $dialog.SelectedPath) {
        Write-Host 'Layered skin import cancelled.' -ForegroundColor Yellow
        exit 1
    }
    return $dialog.SelectedPath
}

function Resolve-SourceFolder {
    param([string]$Path)

    if (-not $Path) {
        $Path = Select-SourceFolder
    }

    if (-not [System.IO.Path]::IsPathRooted($Path)) {
        $Path = Join-Path (Get-Location).Path $Path
    }

    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue
    if (-not $resolved) {
        throw "Source folder was not found: $Path"
    }

    $item = Get-Item -LiteralPath $resolved.Path
    if (-not $item.PSIsContainer) {
        throw "Source path is not a folder: $($resolved.Path)"
    }

    return $item.FullName
}

function Read-PngInfo {
    param([string]$Path)

    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 24) {
        throw 'file is too small to be a PNG'
    }

    $signature = @(137, 80, 78, 71, 13, 10, 26, 10)
    for ($i = 0; $i -lt $signature.Count; $i++) {
        if ($bytes[$i] -ne $signature[$i]) {
            throw 'file does not have a PNG signature'
        }
    }

    $chunkType = [System.Text.Encoding]::ASCII.GetString($bytes, 12, 4)
    if ($chunkType -ne 'IHDR') {
        throw 'PNG IHDR chunk was not found'
    }

    $width = ([int64]$bytes[16] -shl 24) -bor ([int64]$bytes[17] -shl 16) -bor ([int64]$bytes[18] -shl 8) -bor [int64]$bytes[19]
    $height = ([int64]$bytes[20] -shl 24) -bor ([int64]$bytes[21] -shl 16) -bor ([int64]$bytes[22] -shl 8) -bor [int64]$bytes[23]

    if ($width -le 0 -or $height -le 0) {
        throw 'PNG dimensions must be positive'
    }

    [pscustomobject]@{
        Width = $width
        Height = $height
    }
}

function New-BackupFolder {
    New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    $folder = Join-Path $backupRoot $stamp
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
    return $folder
}

Write-Host ''
Write-Host 'SilentScabbard layered skin import' -ForegroundColor DarkYellow
Write-Host ''

$sourceRoot = Resolve-SourceFolder -Path $SourceFolder
Write-Host "Source: $sourceRoot"
Write-Host ''

$layerSpecs = @(
    [pscustomobject]@{ Name = 'room.png'; Required = $true; RequiredWidth = 1668; RequiredHeight = 936 },
    [pscustomobject]@{ Name = 'foreground.png'; Required = $true; RequiredWidth = 1668; RequiredHeight = 936 },
    [pscustomobject]@{ Name = 'samurai.png'; Required = $false; RequiredWidth = $null; RequiredHeight = $null }
)

$errors = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]
$imports = New-Object System.Collections.Generic.List[object]

foreach ($spec in $layerSpecs) {
    $sourcePath = Join-Path $sourceRoot $spec.Name
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        if ($spec.Required) {
            $errors.Add("Missing required layer: $($spec.Name)")
        } else {
            $destinationPath = Join-Path $layersDir $spec.Name
            if (Test-Path -LiteralPath $destinationPath -PathType Leaf) {
                $warnings.Add("Optional layer not supplied: $($spec.Name). Existing installed file will be left unchanged.")
            } else {
                $warnings.Add("Optional layer not supplied: $($spec.Name)")
            }
        }
        continue
    }

    try {
        $png = Read-PngInfo -Path $sourcePath
    } catch {
        $errors.Add("$($spec.Name) is not a valid PNG: $($_.Exception.Message)")
        continue
    }

    if ($spec.Required -and ($png.Width -ne $spec.RequiredWidth -or $png.Height -ne $spec.RequiredHeight)) {
        $errors.Add("$($spec.Name) must be $($spec.RequiredWidth) x $($spec.RequiredHeight), got $($png.Width) x $($png.Height)")
        continue
    }

    $imports.Add([pscustomobject]@{
        Name = $spec.Name
        Source = $sourcePath
        Destination = Join-Path $layersDir $spec.Name
        Width = $png.Width
        Height = $png.Height
    })
}

foreach ($warning in $warnings) {
    Write-Host "Warning: $warning" -ForegroundColor Yellow
}

if ($errors.Count -gt 0) {
    foreach ($errorText in $errors) {
        Write-Host "Error: $errorText" -ForegroundColor Red
    }
    Write-Host ''
    Write-Host 'Layered skin import stopped before changing installed files.' -ForegroundColor Yellow
    exit 1
}

New-Item -ItemType Directory -Force -Path $layersDir | Out-Null
$backupFolder = $null

foreach ($item in $imports) {
    $sourceFull = [System.IO.Path]::GetFullPath($item.Source)
    $destinationFull = [System.IO.Path]::GetFullPath($item.Destination)

    if ((Test-Path -LiteralPath $item.Destination -PathType Leaf) -and
        -not $sourceFull.Equals($destinationFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        if (-not $backupFolder) {
            $backupFolder = New-BackupFolder
        }
        Copy-Item -LiteralPath $item.Destination -Destination (Join-Path $backupFolder $item.Name) -Force
        Write-Host "Backed up existing $($item.Name) to $backupFolder"
    }

    if (-not $sourceFull.Equals($destinationFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        Copy-Item -LiteralPath $item.Source -Destination $item.Destination -Force
    }
    Write-Host "Installed $($item.Name) ($($item.Width) x $($item.Height))"
}

Write-Host ''
Write-Host 'Activating layered skin profile...'
& (Join-Path $appDir 'set-skin-profile.ps1') -SkinProfile layered
if ($LASTEXITCODE -ne 0) {
    throw "Layered profile activation failed with exit code $LASTEXITCODE"
}

if (-not $NoPreview) {
    Write-Host ''
    Write-Host 'Opening skin preview...'
    $previewArgs = @()
    if ($env:RONIN_PREVIEW_CLOSE_AFTER) {
        $previewArgs += @('-CloseAfter', $env:RONIN_PREVIEW_CLOSE_AFTER)
    }
    & (Join-Path $appDir 'preview-skin.ps1') @previewArgs
}

Write-Host ''
Write-Host 'Layered skin import complete.' -ForegroundColor Green
