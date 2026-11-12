# SortiBandLLM - apaga el PC-SERVIDOR (lo llama DETENER_SERVIDOR.bat).
# Detiene la API, Mosquitto (si se inicio como programa) y MySQL de XAMPP.
# Si Mosquitto esta instalado como servicio de Windows, el servicio se deja corriendo.
# (Sin tildes a proposito: PowerShell 5 las muestra mal en scripts.)

Write-Host "SortiBandLLM - deteniendo el PC-SERVIDOR" -ForegroundColor Yellow

# API: el proceso de Python que corre server.api.main (y su ventana)
$api = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "server\.api\.main" }
foreach ($p in $api) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
$ventanas = Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | Where-Object { $_.CommandLine -match "server\.api\.main" }
foreach ($p in $ventanas) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
Write-Host "API y dashboard: detenidos"

# Mosquitto iniciado como programa (no toca el servicio de Windows)
$servicio = Get-Service mosquitto -ErrorAction SilentlyContinue
$mosq = Get-CimInstance Win32_Process -Filter "Name='mosquitto.exe'" | Where-Object { $_.CommandLine -match "mosquitto\.conf" -and $_.CommandLine -notmatch " run" }
foreach ($p in $mosq) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
if ($servicio -and $servicio.Status -eq "Running") { Write-Host "Mosquitto: queda corriendo como servicio de Windows" } else { Write-Host "Mosquitto: detenido" }

# MySQL de XAMPP: se apaga de forma ordenada (mysqladmin shutdown).
# NUNCA matarlo a la fuerza de entrada: eso dania sus tablas internas (error "wrong checksum").
$mysqladmin = "C:\xampp\mysql\bin\mysqladmin.exe"
if (Get-Process mysqld -ErrorAction SilentlyContinue) {
    if (Test-Path $mysqladmin) { & $mysqladmin -u root shutdown 2>$null }
    for ($i = 0; $i -lt 30 -and (Get-Process mysqld -ErrorAction SilentlyContinue); $i++) { Start-Sleep -Seconds 1 }
    if (Get-Process mysqld -ErrorAction SilentlyContinue) {
        Write-Host "MySQL no se apago solo en 30 s: apagarlo desde el panel de XAMPP (Stop)." -ForegroundColor Yellow
    } else {
        Write-Host "MySQL: detenido"
    }
} else {
    Write-Host "MySQL: no estaba corriendo"
}
Write-Host "`nListo." -ForegroundColor Green
