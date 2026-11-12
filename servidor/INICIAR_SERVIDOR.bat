@echo off
rem SortiBandLLM - doble clic para levantar el PC-SERVIDOR (broker, base de datos, API y dashboard).
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\iniciar_servidor.ps1"
echo.
pause
