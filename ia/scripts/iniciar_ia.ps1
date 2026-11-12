# SortiBandLLM - levanta el PC-IA con un solo clic (lo llaman INICIAR_IA.bat e INICIAR_IA_SIN_CAMARA.bat).
# Hace: instalar si falta -> .env con la IP del servidor -> comprobar que llega al servidor -> vision.
# Uso: iniciar_ia.ps1 [-Simular]   (-Simular = sin camara, manzanas dibujadas)
# (Sin tildes a proposito: PowerShell 5 las muestra mal en scripts.)
param([switch]$Simular)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
$envArchivo = "$raiz\.env"

function Paso($texto) { Write-Host "`n== $texto" -ForegroundColor Cyan }

# Lee un valor del .env (o "" si no esta)
function LeerEnv($clave) {
    if (-not (Test-Path $envArchivo)) { return "" }
    $linea = Get-Content $envArchivo | Where-Object { $_ -match "^$clave=" } | Select-Object -First 1
    if ($linea) { return ($linea -replace "^$clave=", "").Trim() } else { return "" }
}

# Escribe (o agrega) un valor en el .env
function EscribirEnv($clave, $valor) {
    $lineas = @(Get-Content $envArchivo)
    if ($lineas -match "^$clave=") { $lineas = $lineas -replace "^$clave=.*", "$clave=$valor" } else { $lineas += "$clave=$valor" }
    Set-Content $envArchivo $lineas -Encoding UTF8
}

# Devuelve $true si responde ese host y puerto
function PuertoAbierto([string]$hostDestino, [int]$puerto) {
    $cliente = New-Object System.Net.Sockets.TcpClient
    try {
        $intento = $cliente.BeginConnect($hostDestino, $puerto, $null, $null)
        if (-not $intento.AsyncWaitHandle.WaitOne(2000)) { return $false }
        $cliente.EndConnect($intento)   # lanza error si la conexion fallo (evita falsos OK)
        return $true
    } catch { return $false } finally { $cliente.Close() }
}

function PedirIp {
    $ip = Read-Host "IP del PC-SERVIDOR (la muestra INICIAR_SERVIDOR.bat en ese PC)"
    $ip = $ip.Trim()
    if ($ip) {
        EscribirEnv "MQTT_HOST" $ip
        EscribirEnv "SERVER_URL" "http://${ip}:8000"
        Write-Host "Guardado en ia\.env: MQTT_HOST=$ip y SERVER_URL=http://${ip}:8000"
    }
}

Write-Host "SortiBandLLM - iniciando el PC-IA" -ForegroundColor Green

# --- 1. Entorno de Python ---
Paso "1/4 Entorno de Python"
$python = "$raiz\.venv\Scripts\python.exe"
# En el PC de desarrollo el entorno puede estar en la carpeta de arriba (proyecto-final\.venv)
if (-not (Test-Path $python) -and (Test-Path "$raiz\..\.venv\Scripts\python.exe")) {
    $python = (Resolve-Path "$raiz\..\.venv\Scripts\python.exe").Path
}
if (-not (Test-Path $python)) {
    Write-Host "Primera vez: se crea el entorno y se instalan las librerias."
    Write-Host "PyTorch pesa ~2,5 GB: puede tardar 10-20 minutos." -ForegroundColor Yellow
    py -3.12 -m venv "$raiz\.venv"
    $python = "$raiz\.venv\Scripts\python.exe"
    $env:PYTHONUTF8 = "1"   # evita un error de pip con tildes en Windows
    & $python -m pip install -q --upgrade pip
    & $python -m pip install -r "$raiz\requirements.txt" -r "$raiz\requirements-ia.txt"
    if ($LASTEXITCODE -ne 0) { throw "Fallo la instalacion de las librerias. Revisa los mensajes de arriba." }
}
Write-Host "Listo ($python)"

# --- 2. Configuracion (.env) ---
Paso "2/4 Configuracion (.env)"
if (-not (Test-Path $envArchivo)) {
    Copy-Item "$raiz\.env.example" $envArchivo
    Write-Host "Se creo ia\.env a partir de .env.example."
    PedirIp
}
Write-Host "Servidor: MQTT_HOST=$(LeerEnv 'MQTT_HOST')   SERVER_URL=$(LeerEnv 'SERVER_URL')"

# --- 3. Comprobar que llega al PC-servidor ---
Paso "3/4 Conexion con el PC-servidor"
for ($intento = 1; $intento -le 3; $intento++) {
    $mqttHost = LeerEnv "MQTT_HOST"; if (-not $mqttHost) { $mqttHost = "localhost" }
    $url = LeerEnv "SERVER_URL"; if (-not $url) { $url = "http://localhost:8000" }
    $uri = [Uri]$url
    $okMqtt = PuertoAbierto $mqttHost 1883
    $okApi = PuertoAbierto $uri.Host $uri.Port
    Write-Host ("Broker MQTT ({0}:1883): {1}" -f $mqttHost, $(if ($okMqtt) {"OK"} else {"NO responde"}))
    Write-Host ("API ({0}): {1}" -f $url, $(if ($okApi) {"OK"} else {"NO responde"}))
    if ($okMqtt -and $okApi) { break }
    Write-Host "No se llega al servidor. Revisa que INICIAR_SERVIDOR.bat este corriendo en el otro PC y que los dos esten en la misma red." -ForegroundColor Yellow
    if ($intento -eq 3) { break }
    Write-Host "Si la IP cambio, escribela; si no, solo Enter para reintentar."
    PedirIp
}
if (-not ($okMqtt -and $okApi)) {
    $seguir = Read-Host "Seguir igual? La vision esperara al broker (s/n)"
    if ($seguir -notmatch "^[sS]") { exit 1 }
}

# --- 4. Vision ---
Paso "4/4 Vision"
$modo = if ($Simular) { "sin camara (manzanas dibujadas)" } else { "con la webcam $(LeerEnv 'CAMERA_INDEX')" }
Write-Host "Motor: $(LeerEnv 'VISION_MOTOR')   Modo: $modo"
Write-Host "En la ventana de la camara: tecla q = cerrar la vision. En esta ventana: Ctrl+C." -ForegroundColor Green
$argumentos = @("-m", "vision.clasificador")
if ($Simular) { $argumentos += "--simular" }
& $python @argumentos
