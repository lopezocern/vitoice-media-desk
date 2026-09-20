# 创建桌面快捷方式的绿色版工具：双击即用
# 用法:  powershell -ExecutionPolicy Bypass -File create_shortcut.ps1  [目标exe路径]
param(
    [string]$Target = (Join-Path $PSScriptRoot "..\dist\MediaDesk\MediaDesk.exe"),
    [string]$Name = "MediaDesk",
    [string]$Icon = (Join-Path $PSScriptRoot "..\dist\MediaDesk\logo.ico")
)
$exePath = (Resolve-Path $Target -ErrorAction Stop).Path
$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = Join-Path $desktop ($Name + ".lnk")
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($lnk)
$s.TargetPath = $exePath
$s.WorkingDirectory = [System.IO.Path]::GetDirectoryName($exePath)
if ($Icon -and (Test-Path $Icon)) { $s.IconLocation = $Icon }
$s.Save()
Write-Host ("已创建桌面快捷方式: {0}  →  {1}" -f $lnk, $exePath)