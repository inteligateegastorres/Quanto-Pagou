# Quanto Pagou - sobe toda a stack local (Postgres + API + Frontend).
#
# Uso:
#   pwsh scripts/dev_up.ps1            # sobe se nao estiver no ar (idempotente)
#   pwsh scripts/dev_up.ps1 -Fresh     # derruba volume do postgres + reseed
#   pwsh scripts/dev_up.ps1 -SkipFront # sobe so backend (postgres + API)
#
# Estado runtime fica em .dev/ (gitignored). Use scripts/dev_down.ps1 para parar.

[CmdletBinding()]
param(
    [switch]$Fresh,
    [switch]$SkipFront,
    [int]$ApiPort = 8000,
    [int]$WebPort = 3000
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$devDir = Join-Path $root ".dev"
New-Item -ItemType Directory -Force -Path $devDir | Out-Null

$pidsFile = Join-Path $devDir "pids.json"
$apiLog   = Join-Path $devDir "api.log"
$webLog   = Join-Path $devDir "web.log"

function Say($msg, $color = "Cyan") {
    Write-Host "==> $msg" -ForegroundColor $color
}

function Need-Cmd($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "comando nao encontrado: $name"
    }
}

function Wait-Tcp($port, $label, $timeoutSec = 60) {
    Say "aguardando $label em http://127.0.0.1:$port ..." DarkGray
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $c = New-Object System.Net.Sockets.TcpClient
            $iar = $c.BeginConnect("127.0.0.1", $port, $null, $null)
            if ($iar.AsyncWaitHandle.WaitOne(500)) {
                $c.EndConnect($iar) | Out-Null
                $c.Close()
                return
            }
            $c.Close()
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    throw "$label nao subiu em ${timeoutSec}s (ver log em .dev/)"
}

function Read-Pids {
    if (Test-Path $pidsFile) { return Get-Content $pidsFile | ConvertFrom-Json }
    return [PSCustomObject]@{ api = $null; web = $null }
}

function Write-Pids($obj) {
    $obj | ConvertTo-Json | Set-Content -Path $pidsFile -Encoding UTF8
}

function Process-Alive($processId) {
    if (-not $processId) { return $false }
    try { Get-Process -Id $processId -ErrorAction Stop | Out-Null; return $true }
    catch { return $false }
}

# ---------- pre-flight ----------

Say "verificando dependencias..."
Need-Cmd "docker"
Need-Cmd "python"
if (-not $SkipFront) { Need-Cmd "npm" }

# ---------- postgres ----------

if ($Fresh) {
    Say "modo --fresh: derrubando container + volume" Yellow
    docker compose down -v 2>&1 | Out-Null
}

Say "subindo postgres (docker compose up -d)..."
docker compose up -d 2>&1 | Out-Null

Say "aguardando postgres healthy..." DarkGray
$deadline = (Get-Date).AddSeconds(60)
do {
    Start-Sleep -Seconds 1
    $ok = $false
    try {
        docker exec quantopagou-postgres pg_isready -U quantopagou -d quantopagou *>$null
        if ($LASTEXITCODE -eq 0) { $ok = $true }
    } catch {}
} while (-not $ok -and (Get-Date) -lt $deadline)
if (-not $ok) { throw "postgres nao ficou healthy em 60s" }

# Aplicar migration analytics (idempotente; sobrescreve materialized views)
Say "aplicando sql/001_analytics.sql..."
Get-Content sql/001_analytics.sql -Raw | docker exec -i quantopagou-postgres psql -U quantopagou -d quantopagou -q *> $null

# ---------- python deps ----------

if (-not (Test-Path ".venv")) {
    Say "instalando deps Python (uv sync)..."
    python -m uv sync
}

# ---------- ingest + build_marts ----------

$rawCount = (docker exec quantopagou-postgres psql -U quantopagou -d quantopagou -t -A -c "SELECT COUNT(*) FROM raw.compras" 2>$null).Trim()
if ($rawCount -eq "" -or $rawCount -eq "0" -or $Fresh) {
    Say "ingerindo fixture sintetica (raw.compras vazio)..."
    python -m uv run python -m ingest --fixture data/fixtures/compras_sample.jsonl 2026-04-15 2026-04-15 *> $null
} else {
    Say "raw.compras ja tem $rawCount linhas (use -Fresh para resetar)" DarkGray
}

Say "rodando analytics.build_marts (canonicalizacao + refresh)..."
python -m uv run python -m analytics.build_marts *> $null

# ---------- API ----------

$pids = Read-Pids
if (Process-Alive $pids.api) {
    Say "API ja rodando (pid=$($pids.api))" DarkGray
} else {
    Say "subindo API FastAPI na porta $ApiPort (log: .dev/api.log)..."
    Remove-Item -ErrorAction SilentlyContinue $apiLog
    $proc = Start-Process -FilePath "python" `
        -ArgumentList @("-m","uv","run","uvicorn","api.main:app","--host","127.0.0.1","--port","$ApiPort","--log-level","warning") `
        -RedirectStandardOutput $apiLog -RedirectStandardError "$apiLog.err" `
        -WindowStyle Hidden -PassThru
    $pids.api = $proc.Id
    Write-Pids $pids
    Wait-Tcp $ApiPort "API"
}

# ---------- frontend ----------

if (-not $SkipFront) {
    if (-not (Test-Path "frontend/node_modules/next")) {
        Say "instalando deps do frontend (npm install)..."
        Push-Location frontend
        npm install --silent
        Pop-Location
    }

    if (Process-Alive $pids.web) {
        Say "frontend ja rodando (pid=$($pids.web))" DarkGray
    } else {
        Say "subindo Next.js dev na porta $WebPort (log: .dev/web.log)..."
        Remove-Item -ErrorAction SilentlyContinue $webLog
        # npm.cmd no Windows; fallback npm.
        $npmCmd = (Get-Command npm.cmd -ErrorAction SilentlyContinue)?.Source
        if (-not $npmCmd) { $npmCmd = (Get-Command npm).Source }
        $proc = Start-Process -FilePath $npmCmd `
            -ArgumentList @("--prefix","frontend","run","dev","--","-p","$WebPort") `
            -RedirectStandardOutput $webLog -RedirectStandardError "$webLog.err" `
            -WindowStyle Hidden -PassThru
        $pids.web = $proc.Id
        Write-Pids $pids
        Wait-Tcp $WebPort "frontend" 90
    }
}

# ---------- pronto ----------

Write-Host ""
Say "stack no ar:" Green
Write-Host "  Postgres : localhost:5433  (user/db: quantopagou)"
Write-Host "  API      : http://127.0.0.1:$ApiPort       (docs: /docs)"
if (-not $SkipFront) {
    Write-Host "  Frontend : http://127.0.0.1:$WebPort"
}
Write-Host ""
Write-Host "Para parar: pwsh scripts/dev_down.ps1" -ForegroundColor DarkGray
Write-Host "Logs:       .dev/api.log .dev/web.log" -ForegroundColor DarkGray
