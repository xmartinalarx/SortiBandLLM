@echo off
rem SortiBandLLM - doble clic para apagar el PC-SERVIDOR.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\detener_servidor.ps1"
echo.
pause
