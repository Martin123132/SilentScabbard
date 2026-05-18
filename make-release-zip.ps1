$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$versionFile = Join-Path $repoRoot 'VERSION'
if (-not (Test-Path $versionFile)) {
    throw 'VERSION file was not found.'
}

$version = (Get-Content -LiteralPath $versionFile -Raw).Trim()
if (-not $version) {
    throw 'VERSION is empty.'
}

$git = Get-Command git.exe -ErrorAction SilentlyContinue
if (-not $git) {
    throw 'git.exe was not found. Install Git for Windows to build a release zip.'
}

$files = & $git.Source -C $repoRoot ls-files
if (-not $files) {
    throw 'No tracked files were found. Run this from a Git checkout.'
}

$distDir = Join-Path $repoRoot 'dist'
New-Item -ItemType Directory -Force -Path $distDir | Out-Null

$zipName = "SilentScabbard-v$version.zip"
$zipPath = Join-Path $distDir $zipName
if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("SilentScabbard-release-" + [guid]::NewGuid().ToString('N'))
$packageRoot = Join-Path $tempRoot "SilentScabbard-v$version"
New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null

try {
    foreach ($relative in $files) {
        $source = Join-Path $repoRoot $relative
        if (-not (Test-Path $source)) {
            continue
        }

        $target = Join-Path $packageRoot $relative
        $targetDir = Split-Path -Parent $target
        New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
        Copy-Item -LiteralPath $source -Destination $target -Force
    }

    Compress-Archive -Path $packageRoot -DestinationPath $zipPath -CompressionLevel Optimal
} finally {
    if (Test-Path $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}

Write-Host "Built $zipPath" -ForegroundColor Green
