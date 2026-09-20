@echo off
rem 双击本脚本，为绿色版 MediaDesk 在桌面创建快捷方式
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1" %*
if errorlevel 1 (
  echo 创建失败：请确认已先运行 scripts\portable_build.py 生成 dist\MediaDesk
  pause
) else (
  echo.
  pause
)