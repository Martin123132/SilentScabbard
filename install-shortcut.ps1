$ErrorActionPreference = 'Stop'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'Ronin.lnk'
$launcher = Join-Path $appDir 'launch-ronin.vbs'
$icon = Join-Path $appDir 'assets\ronin_skin.png'
$ollamaIcon = 'D:\AI\Ollama\app\app.ico'

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcher
$shortcut.Arguments = ''
$shortcut.WorkingDirectory = $appDir
$shortcut.Description = 'Open the local Ronin AI desktop app'
if (Test-Path $ollamaIcon) {
    $shortcut.IconLocation = $ollamaIcon
} elseif (Test-Path $icon) {
    $shortcut.IconLocation = $icon
}
$shortcut.Save()

Write-Output $shortcutPath
