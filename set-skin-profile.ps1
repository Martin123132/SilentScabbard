param(
    [ValidateSet('full', 'layered')]
    [string]$SkinProfile = 'full',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetsDir = Join-Path $appDir 'assets'
$activeManifest = Join-Path $assetsDir 'skin_manifest.json'

$sourceManifest = switch ($SkinProfile) {
    'full' { Join-Path $assetsDir 'skin_manifest.full.json' }
    'layered' { Join-Path $assetsDir 'skin_manifest.layered.example.json' }
}

if (-not (Test-Path $sourceManifest)) {
    throw "Missing skin profile: $sourceManifest"
}

Copy-Item -LiteralPath $sourceManifest -Destination $activeManifest -Force

if ($SkinProfile -eq 'layered' -and -not $Force) {
    & (Join-Path $appDir 'check-skin-assets.ps1')
    if ($LASTEXITCODE -ne 0) {
        Copy-Item -LiteralPath (Join-Path $assetsDir 'skin_manifest.full.json') -Destination $activeManifest -Force
        Write-Host ''
        Write-Host 'Layered profile was not ready. Restored full skin profile.' -ForegroundColor Yellow
        exit 1
    }
} else {
    & (Join-Path $appDir 'check-skin-assets.ps1')
}

Write-Host ''
Write-Host "Active skin profile: $SkinProfile" -ForegroundColor Green
