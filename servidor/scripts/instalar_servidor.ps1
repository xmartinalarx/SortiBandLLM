# SortiBandLLM - instala y configura el PC-SERVIDOR (Windows).
# Deja listos: Mosquitto (broker MQTT), MySQL de XAMPP, el entorno de Python y el .env.
#
# Uso: copiar la carpeta servidor\ a este PC (sin .venv ni data\imagenes) y, desde
# PowerShell dentro de esa carpeta:
#     powershell -ExecutionPolicy Bypass -File scripts\instalar_servidor.ps1
# Pide permiso de administrador una vez (firewall y Mosquitto).
# (Sin tildes a proposito: PowerShell 5 las muestra mal en scripts.)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

# --- Volver a abrir como administrador si hace falta ---
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host "Pidiendo permiso de administrador..."
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-File", "`"$PSCommandPath`""
    exit
}

function Paso($texto) { Write-Host "`n=== $texto ===" -ForegroundColor Cyan }

# --- 1. Programas ---
Paso "1/6 Programas (Python 3.12, Mosquitto, XAMPP)"
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    winget install --id Python.Python.3.12 -e --silent --accept-source-agreements --accept-package-agreements
} else { Write-Host "Python ya instalado" }
if (-not (Test-Path "C:\Program Files\mosquitto\mosquitto.exe")) {
    winget install --id EclipseFoundation.Mosquitto -e --silent --accept-source-agreements --accept-package-agreements
} else { Write-Host "Mosquitto ya instalado" }
if (-not (Test-Path "C:\xampp\mysql\bin\mysqld.exe")) {
    winget install --id ApacheFriends.Xampp.8.2 -e --silent --accept-source-agreements --accept-package-agreements
    if (-not (Test-Path "C:\xampp\mysql\bin\mysqld.exe")) {
        Write-Host "No se pudo instalar XAMPP solo. Descargalo de https://www.apachefriends.org, instalalo en C:\xampp y vuelve a correr este script." -ForegroundColor Yellow
        exit 1
    }
} else { Write-Host "XAMPP ya instalado" }

# --- 2. Mosquitto: aceptar conexiones de la red ---
Paso "2/6 Mosquitto escuchando en la red"
$conf = "C:\Program Files\mosquitto\mosquitto.conf"
if ((Get-Content $conf -Raw) -notmatch "(?m)^listener 1883 0\.0\.0\.0") {
    Add-Content $conf "`r`n# ClasifIoT: aceptar conexiones del Arduino y del PC de la IA`r`nlistener 1883 0.0.0.0`r`nallow_anonymous true`r`n"
}
Set-Service mosquitto -StartupType Automatic
Restart-Service mosquitto
Write-Host "Mosquitto: $((Get-Service mosquitto).Status)"

# --- 3. Firewall ---
Paso "3/6 Firewall (1883 MQTT, 8000 dashboard)"
foreach ($r in @(@("Mosquitto 1883", 1883), @("ClasifIoT web 8000", 8000))) {
    if (-not (Get-NetFirewallRule -DisplayName $r[0] -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $r[0] -Direction Inbound -Action Allow -Protocol TCP -LocalPort $r[1] | Out-Null
    }
    Write-Host "Regla '$($r[0])' lista"
}

# --- 4. Base de datos ---
Paso "4/6 Base de datos clasifiot (MySQL de XAMPP)"
$mysql = "C:\xampp\mysql\bin\mysql.exe"
$vivo = $false
try { & $mysql -u root -e "SELECT 1" 2>$null | Out-Null; $vivo = ($LASTEXITCODE -eq 0) } catch {}
if (-not $vivo) {
    Start-Process "C:\xampp\mysql\bin\mysqld.exe" -ArgumentList "--defaults-file=C:\xampp\mysql\bin\my.ini", "--standalone" -WindowStyle Hidden
    for ($i = 0; $i -lt 30 -and -not $vivo; $i++) {
        Start-Sleep 1
        try { & $mysql -u root -e "SELECT 1" 2>$null | Out-Null; $vivo = ($LASTEXITCODE -eq 0) } catch {}
    }
}
if (-not $vivo) { Write-Host "MySQL no arranco. Abre el panel de XAMPP, aprieta Start en MySQL y vuelve a correr el script." -ForegroundColor Yellow; exit 1 }
Get-Content "$raiz\server\db\schema.sql" -Raw | & $mysql -u root
$clave = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 16 | ForEach-Object { [char]$_ })
& $mysql -u root -e "CREATE USER IF NOT EXISTS 'clasifiot'@'localhost' IDENTIFIED BY '$clave'; ALTER USER 'clasifiot'@'localhost' IDENTIFIED BY '$clave'; GRANT ALL ON clasifiot.* TO 'clasifiot'@'localhost'; FLUSH PRIVILEGES;"
Write-Host "Base y usuario listos"

# --- 5. Entorno de Python y .env ---
Paso "5/6 Entorno de Python"
if (-not (Test-Path "$raiz\.venv")) { py -3.12 -m venv "$raiz\.venv" }
$env:PYTHONUTF8 = "1"
& "$raiz\.venv\Scripts\python.exe" -m pip install -q --upgrade pip
& "$raiz\.venv\Scripts\python.exe" -m pip install -q -r "$raiz\requirements.txt"

$envArchivo = "$raiz\.env"
if (-not (Test-Path $envArchivo)) { Copy-Item "$raiz\.env.example" $envArchivo }
$lineas = Get-Content $envArchivo
$valores = @{ "MQTT_HOST" = "localhost"; "DB_HOST" = "localhost"; "DB_USER" = "clasifiot"; "DB_PASSWORD" = $clave; "DB_NAME" = "clasifiot" }
foreach ($k in $valores.Keys) {
    if ($lineas -match "^$k=") { $lineas = $lineas -replace "^$k=.*", "$k=$($valores[$k])" } else { $lineas += "$k=$($valores[$k])" }
}
Set-Content $envArchivo $lineas -Encoding UTF8
Write-Host ".env listo (clave nueva de la BD guardada ahi)"

# --- 6. IP de este PC ---
Paso "6/6 Datos para el PC de la IA y el Arduino"
$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -match "Wi-?Fi|WLAN" -and $_.IPAddress -notlike "169.*" } | Select-Object -First 1).IPAddress
Write-Host "IP de este PC-SERVIDOR: $ip" -ForegroundColor Green
Write-Host "  - En el PC de la IA (.env):  MQTT_HOST=$ip   y   SERVER_URL=http://${ip}:8000"
Write-Host "  - En el Arduino (secrets.h): MQTT_HOST `"$ip`""
Write-Host "`nPara levantar el servidor y el dashboard:"
Write-Host "  .venv\Scripts\activate"
Write-Host "  python -m server.api.main      (dashboard en http://${ip}:8000)"
