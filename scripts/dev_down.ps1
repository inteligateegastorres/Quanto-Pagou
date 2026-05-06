# Quanto Pagou - derruba a stack local (oposto de dev_up.ps1).
#
# Uso:
#   pwsh scripts/dev_down.ps1            # para API + Frontend; postgres continua
#   pwsh scripts/dev_down.ps1 -All       # para tudo, incluindo postgres (preserva volume)
#   pwsh scripts/dev_down.ps1 -Wipe      # para tudo + apaga volume (perde dados)
#
# Estrategia: tenta matar a arvore do PID registrado e, como rede de seguranca,
# tambem mata o que estiver escutando nas portas conhecidas (npm.cmd e um
# wrapper que termina antes do node real, deixando o servidor "orfao").

[CmdletBinding()]
param(
    [switch]$All,
    [switch]$Wipe,
    [int]$ApiPort = 8000,
    [int]$WebPort = 3000
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$devDir = Join-Path $root ".dev"
$pidsFile = Join-Path $devDir "pids.json"

function Say($msg, $color = "Cyan") {
    Write-Host "==> $msg" -ForegroundColor $color
}

function Stop-PidIfAlive($processId, $label) {
    if (-not $processId) { return }
    try {
        $p = Get-Process -Id $processId -ErrorAction Stop
        Say "matando $label (pid=$processId, $($p.ProcessName))..."
        # Mata a arvore inteira (npm spawna node, uvicorn pode ter workers).
        try { taskkill /PID $processId /T /F *> $null } catch {}
    } catch {}
}

function Stop-OnPort($port, $label) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $conns) { return $false }
    foreach ($c in $conns) {
        $procId = $c.OwningProcess
        if ($procId -eq 0 -or $procId -eq 4) { continue }  # System
        try {
            $p = Get-Process -Id $procId -ErrorAction Stop
            Say "matando $label na porta $port (pid=$procId, $($p.ProcessName))..."
            taskkill /PID $procId /T /F *> $null
        } catch {}
    }
    return $true
}

if (Test-Path $pidsFile) {
    $pids = Get-Content $pidsFile | ConvertFrom-Json
    Stop-PidIfAlive $pids.web "frontend (pid registrado)"
    Stop-PidIfAlive $pids.api "API (pid registrado)"
    Remove-Item $pidsFile -ErrorAction SilentlyContinue
}

# Fallback: pega o que estiver escutando nas portas (npm.cmd vira orfao).
$gotApi = Stop-OnPort $ApiPort "API"
$gotWeb = Stop-OnPort $WebPort "frontend"
if (-not $gotApi -and -not $gotWeb -and -not (Test-Path $pidsFile)) {
    Say "nada rodando nas portas $ApiPort/$WebPort" DarkGray
}

if ($Wipe) {
    Say "derrubando postgres + apagando volume (--wipe)..." Yellow
    docker compose down -v *> $null
} elseif ($All) {
    Say "parando postgres (volume preservado)..."
    docker compose stop *> $null
} else {
    Say "postgres continua rodando (use -All para parar tudo)" DarkGray
}

Say "ok" Green
