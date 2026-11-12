@echo off
rem SortiBandLLM - doble clic para levantar el PC-IA (camara + IA). Tecla q en la ventana de la camara = cerrar.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\iniciar_ia.ps1"
echo.
pause
