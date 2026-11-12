@echo off
rem SortiBandLLM - PC-IA sin camara: dibuja manzanas falsas para probar el sistema.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\iniciar_ia.ps1" -Simular
echo.
pause
