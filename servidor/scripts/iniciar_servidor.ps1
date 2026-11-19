# SortiBandLLM - levanta el PC-SERVIDOR con un solo clic (lo llama INICIAR_SERVIDOR.bat).
# Hace: instalar si falta -> Mosquitto -> MySQL (XAMPP) -> API + dashboard -> abre el navegador.
# Lo que ya esta corriendo no se vuelve a iniciar.
# (Sin tildes a proposito: PowerShell 5 las muestra mal en scripts.)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

# Rutas de los programas (cambiar aqui si se instalaron en otro lugar)
$mosquittoExe = "C:\Program Files\mosquitto\mosquitto.exe"
$xampp = "C:\xampp"
$python = "$raiz\.venv\Scripts\python.exe"
# En el PC de desarrollo el entorno puede estar en la carpeta de arriba (proyecto-final\.venv)
if (-not (Test-Path $python) -and (Test-Path "$raiz\..\.venv\Scripts\python.exe")) {
    $python = (Resolve-Path "$raiz\..\.venv\Scripts\python.exe").Path
}

function Paso($texto) { Write-Host "`n== $texto" -ForegroundColor Cyan }

# Devuelve $true si algo escucha en ese puerto de este PC
function PuertoAbierto([int]$puerto) {
    $cliente = New-Object System.Net.Sockets.TcpClient
    try {
        $intento = $cliente.BeginConnect("127.0.0.1", $puerto, $null, $null)
        if (-not $intento.AsyncWaitHandle.WaitOne(500)) { return $false }
        $cliente.EndConnect($intento)   # lanza error si la conexion fallo (evita falsos OK)
        return $true
    } catch { return $false } finally { $cliente.Close() }
}

# Espera hasta que el puerto responda (o se acabe el tiempo)
function EsperarPuerto([int]$puerto, [int]$segundos) {
    for ($i = 0; $i -lt $segundos; $i++) {
        if (PuertoAbierto $puerto) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

Write-Host "SortiBandLLM - iniciando el PC-SERVIDOR" -ForegroundColor Green

# --- 1. Instalacion (solo la primera vez) ---
Paso "1/5 Instalacion"
if (-not (Test-Path $python) -or -not (Test-Path "$raiz\.env")) {
    Write-Host "No esta instalado: se ejecuta el instalador (pide permiso de administrador una vez)."
    & powershell -ExecutionPolicy Bypass -File "$raiz\scripts\instalar_servidor.ps1"
    if (-not (Test-Path $python)) { throw "La instalacion no termino. Revisa los mensajes de arriba." }
} else {
    Write-Host "Ya instalado."
}

# --- 2. Broker MQTT (Mosquitto, puerto 1883) ---
Paso "2/5 Broker MQTT (Mosquitto)"
if (PuertoAbierto 1883) {
    Write-Host "Ya estaba corriendo."
} else {
    if (-not (Test-Path $mosquittoExe)) { throw "No se encontro Mosquitto en $mosquittoExe" }
    Start-Process -FilePath $mosquittoExe -ArgumentList "-c `"$raiz\server\mosquitto\mosquitto.conf`"" -WindowStyle Minimized
    if (EsperarPuerto 1883 10) { Write-Host "Iniciado (ventana minimizada)." } else { throw "Mosquitto no respondio en el puerto 1883." }
}

# --- 3. Base de datos (MySQL de XAMPP, puerto 3306) ---
Paso "3/5 Base de datos (MySQL de XAMPP)"
if (PuertoAbierto 3306) {
    Write-Host "Ya estaba corriendo."
} else {
    $mysqld = "$xampp\mysql\bin\mysqld.exe"
    if (-not (Test-Path $mysqld)) { throw "No se encontro MySQL en $mysqld (XAMPP)" }
    Start-Process -FilePath $mysqld -ArgumentList "--defaults-file=`"$xampp\mysql\bin\my.ini`" --standalone" -WorkingDirectory "$xampp\mysql" -WindowStyle Hidden
    if (EsperarPuerto 3306 20) { Write-Host "Iniciado." } else { throw "MySQL no respondio en el puerto 3306." }
}

# --- 4. API + dashboard (puerto 8000) ---
Paso "4/5 API y dashboard"
if (PuertoAbierto 8000) {
    Write-Host "Ya estaba corriendo."
} else {
    # Ventana propia: ahi se ven los mensajes del servidor. Cerrarla = apagar la API.
    Start-Process -FilePath "cmd.exe" -WorkingDirectory $raiz -ArgumentList "/k title SortiBandLLM - API y dashboard && `"$python`" -m server.api.main"
    if (EsperarPuerto 8000 30) { Write-Host "Iniciado (ventana 'SortiBandLLM - API y dashboard')." } else { throw "La API no respondio en el puerto 8000. Mira su ventana para ver el error." }
}

# --- 5. Abrir el dashboard y mostrar la IP ---
Paso "5/5 Listo"
Start-Process "http://localhost:8000"
# La IP que usan el Arduino y el PC-IA es la de la zona WiFi TARRO (siempre 192.168.137.1).
# La del WiFi normal (por donde este PC sale a internet) solo sirve a equipos de esa misma red.
$tarro = Get-NetIPAddress -AddressFamily IPv4 -IPAddress "192.168.137.1" -ErrorAction SilentlyContinue
$ipWifi = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -match "^(Wi-?Fi|WLAN)" -and $_.IPAddress -notlike "169.*" -and $_.IPAddress -ne "192.168.137.1" } | Select-Object -First 1).IPAddress
if ($tarro) {
    $ip = "192.168.137.1"
    Write-Host "Zona WiFi TARRO encendida. IP de este PC-SERVIDOR en TARRO: $ip" -ForegroundColor Green
} else {
    $ip = "192.168.137.1"
    Write-Host "[AVISO] La zona WiFi TARRO esta APAGADA: el Arduino y el PC-IA no van a conectarse." -ForegroundColor Yellow
    Write-Host "        Encenderla: Configuracion > Red e Internet > Zona con cobertura inalambrica movil (2,4 GHz)." -ForegroundColor Yellow
}
if ($ipWifi) { Write-Host "(IP en el WiFi normal: $ipWifi; NO usarla en el Arduino ni en el PC-IA si estan en TARRO)" }
Write-Host "Dashboard: http://localhost:8000   (desde otro equipo en TARRO: http://${ip}:8000)" -ForegroundColor Green
Write-Host "  - PC-IA (ia\.env):          MQTT_HOST=$ip   y   SERVER_URL=http://${ip}:8000"
Write-Host "  - Arduino (secrets.h):      MQTT_HOST `"$ip`""
Write-Host "`nPara apagar todo: DETENER_SERVIDOR.bat"
