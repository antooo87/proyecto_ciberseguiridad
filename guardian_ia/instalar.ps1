<#
Instalador del Guardián IA para Windows (no necesita permisos de administrador).

Uso, en PowerShell y dentro de la carpeta guardian_ia:
    powershell -ExecutionPolicy Bypass -File .\instalar.ps1

Opciones:
    -Entorno C:\venvs\guardian   dónde crear el entorno virtual (si no, lo elige solo)
    -Modelo qwen3.5:4b           modelo de Ollama que se comprueba (por defecto qwen3.5:9b)
    -DescargarModelo             si falta el modelo, descargarlo con "ollama pull" (unos 6 GB el de 9b)
    -SinOllama                   no comprobar Ollama

Qué hace:
  1. Busca Python 3.11 o más nuevo (con el lanzador "py" o con "python").
  2. Crea el entorno virtual (la "mochila" con las librerías del proyecto). Si la carpeta tiene una ruta larga y
     Windows no tiene activadas las rutas largas, lo crea en %LOCALAPPDATA%\GuardianIA\entorno: Windows no deja
     crear archivos de más de 260 caracteres y Streamlit se quedaría a medias ("No module named streamlit.proto").
  3. Instala el Guardián con la web y las pruebas (pip install -e ".[web,dev]").
  4. Crea guardian.cmd en esta carpeta para usarlo sin activar nada: .\guardian demo, .\guardian web...
  5. Comprueba Ollama y el modelo, y pasa el médico (guardian doctor).
Se puede volver a ejecutar cuando quieras: reutiliza el entorno y solo instala lo que falte.
#>
[CmdletBinding()]
param(
    [string]$Entorno = "",
    [string]$Modelo = "qwen3.5:9b",
    [switch]$DescargarModelo,
    [switch]$SinOllama
)

$ErrorActionPreference = "Stop"
$Proyecto = $PSScriptRoot
Set-Location $Proyecto

function Paso([string]$texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }
function Bien([string]$texto) { Write-Host "    OK  $texto" -ForegroundColor Green }
function Aviso([string]$texto) { Write-Host "    !   $texto" -ForegroundColor Yellow }
function Fallo([string]$texto) {
    Write-Host "    X   $texto" -ForegroundColor Red
    exit 1
}
function Ejecutar([string]$programa, [string[]]$argumentos) {
    # Sin redirigir los errores: en Windows PowerShell 5.1, redirigirlos convierte cualquier aviso en un fallo
    & $programa @argumentos
    if ($LASTEXITCODE -ne 0) { Fallo "Ha fallado: $programa $($argumentos -join ' ')" }
}

if (-not (Test-Path (Join-Path $Proyecto "pyproject.toml"))) {
    Fallo "Este script tiene que estar en la carpeta guardian_ia (la que tiene pyproject.toml)."
}

# 1. Python ------------------------------------------------------------------------------------------------
Paso "Buscando Python 3.11 o más nuevo"
$candidatos = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($v in @("3.13", "3.12", "3.11", "3.14")) { $candidatos += , @("py", "-$v") }
}
if (Get-Command python -ErrorAction SilentlyContinue) { $candidatos += , @("python") }
$python = $null
foreach ($c in $candidatos) {
    $extra = @()
    if ($c.Count -gt 1) { $extra = @($c[1..($c.Count - 1)]) }
    $programa = $c[0]
    try {
        # El "python" de la Microsoft Store es un atajo que no funciona: devuelve error y se salta
        $version = & $programa @extra -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
    } catch {
        continue
    }
    if ($LASTEXITCODE -ne 0 -or -not $version) { continue }
    $partes = "$version".Trim().Split(".")
    if ([int]$partes[0] -eq 3 -and [int]$partes[1] -ge 11) {
        $python = @{ Programa = $programa; Extra = $extra; Version = "$version".Trim() }
        break
    }
}
if (-not $python) {
    Fallo ("No encuentro Python 3.11 o más nuevo. Instálalo desde https://www.python.org/downloads/ " +
           "(marca 'Add python.exe to PATH') y vuelve a ejecutar este script.")
}
Bien "Python $($python.Version) ($($python.Programa) $($python.Extra -join ' '))"

# 2. Entorno virtual -----------------------------------------------------------------------------------------
Paso "Preparando el entorno virtual"
$rutasLargas = $false
try {
    $rutasLargas = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled `
        -ErrorAction Stop).LongPathsEnabled -eq 1
} catch { }
$entornoLocal = Join-Path $Proyecto ".venv"
if (-not $Entorno) {
    if ($rutasLargas -or $entornoLocal.Length -le 80) {
        $Entorno = $entornoLocal
    } else {
        $Entorno = Join-Path $env:LOCALAPPDATA "GuardianIA\entorno"
        Aviso ("La carpeta del proyecto tiene una ruta larga ($($entornoLocal.Length) caracteres) y Windows corta " +
               "los archivos de más de 260: el entorno irá en $Entorno")
    }
}
$pythonEntorno = Join-Path $Entorno "Scripts\python.exe"
if (Test-Path $pythonEntorno) {
    Bien "Ya existe en ${Entorno}: se reutiliza"
} else {
    $extra = $python.Extra
    Ejecutar $python.Programa (@($extra) + @("-m", "venv", $Entorno))
    if (-not (Test-Path $pythonEntorno)) { Fallo "No he podido crear el entorno en $Entorno" }
    Bien "Creado en $Entorno"
}

# 3. Librerías -----------------------------------------------------------------------------------------------
Paso "Instalando el Guardián y sus librerías (la primera vez tarda unos minutos)"
Ejecutar $pythonEntorno @("-m", "pip", "install", "--upgrade", "pip", "--quiet", "--disable-pip-version-check")
Ejecutar $pythonEntorno @("-m", "pip", "install", "--editable", ".[web,dev]", "--disable-pip-version-check")
Bien "Instalado"

# 4. Lanzador ------------------------------------------------------------------------------------------------
Paso "Creando el lanzador guardian.cmd"
if ($Entorno -eq $entornoLocal) {
    $rutaPython = '%~dp0.venv\Scripts\python.exe'
} elseif ($Entorno.StartsWith($env:LOCALAPPDATA, [System.StringComparison]::OrdinalIgnoreCase)) {
    $rutaPython = '%LOCALAPPDATA%' + $Entorno.Substring($env:LOCALAPPDATA.Length) + '\Scripts\python.exe'
} else {
    $rutaPython = $pythonEntorno
}
$lineas = @(
    "@echo off",
    "rem Lanzador del Guardian IA (lo crea instalar.ps1). Ejemplos: guardian demo, guardian web, guardian servicio",
    "setlocal"
)
if ($rutaPython -match '[^\x00-\x7F]') { $lineas += "chcp 65001 >nul" }  # rutas con tildes o "ª"
$lineas += @(
    'if not defined GUARDIAN_REGISTRO set "GUARDIAN_REGISTRO=%~dp0registro"',
    "`"$rutaPython`" -m guardian %*"
)
$lanzador = Join-Path $Proyecto "guardian.cmd"
[System.IO.File]::WriteAllText($lanzador, (($lineas -join "`r`n") + "`r`n"), (New-Object System.Text.UTF8Encoding $false))
Bien "Creado $lanzador"

# 5. Ollama --------------------------------------------------------------------------------------------------
if ($SinOllama) {
    Aviso "Sin comprobar Ollama (-SinOllama)"
} else {
    Paso "Comprobando Ollama y el modelo $Modelo"
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        Aviso ("Ollama no está instalado. Sin él funcionan la extensión, el escudo, la aduana y el verificador, " +
               "pero no el chat ni la detección con IA. Descárgalo de https://ollama.com/download")
    } else {
        $modelos = (& ollama list | Out-String)
        if ($LASTEXITCODE -ne 0) {
            Aviso "Ollama está instalado pero no responde: ábrelo desde el menú Inicio y vuelve a probar."
        } elseif ($modelos -match [regex]::Escape($Modelo)) {
            Bien "Ollama responde y tiene el modelo $Modelo"
        } elseif ($DescargarModelo) {
            Ejecutar "ollama" @("pull", $Modelo)
            Bien "Modelo $Modelo descargado"
        } else {
            Aviso "Falta el modelo $Modelo. Descárgalo con: ollama pull $Modelo   (o repite con -DescargarModelo)"
        }
    }
}

# 6. Médico --------------------------------------------------------------------------------------------------
Paso "Pasando el médico (guardian doctor)"
$argumentosDoctor = @("-m", "guardian", "doctor")
if ($SinOllama) { $argumentosDoctor += "--sin-ollama" }
& $pythonEntorno @argumentosDoctor
$codigo = $LASTEXITCODE

Write-Host ""
Write-Host "Listo. Desde esta carpeta, sin activar nada:" -ForegroundColor Green
Write-Host "    .\guardian demo        los cuatro módulos en un minuto (no necesita Ollama)"
Write-Host "    .\guardian web         la web, solo en este PC"
Write-Host "    .\guardian servicio    el servicio para la extensión del navegador"
Write-Host "    .\guardian informe     lo que ha hecho el Guardián estos días"
Write-Host "    .\guardian --help      todo lo demás"
exit $codigo
