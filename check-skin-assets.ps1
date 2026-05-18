$ErrorActionPreference = 'Stop'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetsDir = Join-Path $appDir 'assets'
$manifestPath = Join-Path $assetsDir 'skin_manifest.json'

function Resolve-AssetPath {
    param([string]$RelativePath)
    $combined = Join-Path $assetsDir $RelativePath
    $resolvedParent = Resolve-Path -LiteralPath (Split-Path -Parent $combined) -ErrorAction SilentlyContinue
    if (-not $resolvedParent) {
        return $combined
    }
    return Join-Path $resolvedParent.Path (Split-Path -Leaf $combined)
}

function Test-InAssets {
    param([string]$Path)
    $assetRoot = (Resolve-Path -LiteralPath $assetsDir).Path
    $full = [System.IO.Path]::GetFullPath($Path)
    return $full.StartsWith($assetRoot, [System.StringComparison]::OrdinalIgnoreCase)
}

Write-Host ''
Write-Host 'SilentScabbard skin check' -ForegroundColor DarkYellow
Write-Host ''

if (-not (Test-Path $manifestPath)) {
    Write-Host "Missing manifest: $manifestPath" -ForegroundColor Red
    exit 1
}

try {
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
} catch {
    Write-Host "Manifest is not valid JSON: $manifestPath" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

$width = [int]$manifest.width
$height = [int]$manifest.height
$fallbackFile = if ($manifest.fallback_file) { [string]$manifest.fallback_file } else { 'ronin_skin.png' }
$fallbackPath = Resolve-AssetPath $fallbackFile
$errors = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]

if ($width -le 0 -or $height -le 0) {
    $errors.Add('Manifest width and height must be positive numbers.')
}

if (-not (Test-InAssets $fallbackPath)) {
    $errors.Add("Fallback file escapes assets folder: $fallbackFile")
} elseif (-not (Test-Path $fallbackPath)) {
    $warnings.Add("Fallback file is missing: $fallbackFile")
}

$layers = @($manifest.layers)
if (-not $layers -or $layers.Count -eq 0) {
    $errors.Add('Manifest has no layers.')
}

Write-Host "Manifest:       $manifestPath"
Write-Host "Canvas:         ${width}x${height}"
Write-Host "Fallback:       $fallbackFile"
Write-Host ''

$enabledCount = 0
foreach ($layer in $layers) {
    $enabled = if ($null -eq $layer.enabled) { $true } else { [bool]$layer.enabled }
    $required = if ($null -eq $layer.required) { $true } else { [bool]$layer.required }
    $name = if ($layer.name) { [string]$layer.name } else { [string]$layer.file }
    $file = [string]$layer.file
    if (-not $enabled) {
        Write-Host "disabled       $name -> $file"
        continue
    }

    $enabledCount += 1
    if (-not $file) {
        $errors.Add("Layer '$name' has no file.")
        continue
    }

    $path = Resolve-AssetPath $file
    if (-not (Test-InAssets $path)) {
        $errors.Add("Layer '$name' escapes assets folder: $file")
        continue
    }

    if (Test-Path $path) {
        Write-Host "ok             $name -> $file"
    } elseif ($required) {
        Write-Host "missing        $name -> $file" -ForegroundColor Red
        $errors.Add("Required layer missing: $file")
    } else {
        Write-Host "optional miss  $name -> $file" -ForegroundColor Yellow
    }
}

if ($enabledCount -eq 0) {
    $errors.Add('Manifest has no enabled layers.')
}

Write-Host ''
foreach ($warning in $warnings) {
    Write-Host "Warning: $warning" -ForegroundColor Yellow
}

if ($errors.Count -gt 0) {
    foreach ($errorText in $errors) {
        Write-Host "Error: $errorText" -ForegroundColor Red
    }
    Write-Host ''
    Write-Host 'Skin health: needs repair.' -ForegroundColor Yellow
    exit 1
}

Write-Host 'Skin health: ready.' -ForegroundColor Green
