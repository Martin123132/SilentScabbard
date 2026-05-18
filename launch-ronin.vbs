Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = scriptDir & "\launch-ronin.ps1"
shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & launcher & """", 0, False
