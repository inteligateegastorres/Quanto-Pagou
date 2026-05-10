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
    [int]$ApiPort = 8001,
    [int]$WebPort = 3001
)

# Continue (nao Stop): em Windows PowerShell 5.1 com Stop, qualquer escrita em
# stderr de comando nativo (ex.: warnings benignos do docker) vira NativeCommandError
# e aborta o script. Usamos throw + checks de $LASTEXITCODE explicitos.
$ErrorActionPreference = "Continue"
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

# Daemon do Docker Desktop esta no ar?
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERRO: Docker Desktop nao esta rodando." -ForegroundColor Red
    Write-Host "Abra o Docker Desktop (icone da bandeja ou menu Iniciar)," -ForegroundColor Yellow
    Write-Host "aguarde a baleia ficar verde, e rode novamente." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# ---------- postgres ----------

if ($Fresh) {
    Say "modo --fresh: derrubando container + volume" Yellow
    docker compose down -v *> $null
}

Say "subindo postgres (docker compose up -d)..."
docker compose up -d *> $null
if ($LASTEXITCODE -ne 0) { throw "docker compose up falhou (exit=$LASTEXITCODE)" }

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

# Aplicar migrations idempotentes na ordem (analytics + resilience + tce_pr + escolas + manchetes + perf indexes)
foreach ($sqlFile in @("sql/001_analytics.sql", "sql/002_resilience.sql", "sql/003_tce_pr.sql", "sql/004_escolas.sql", "sql/005_manchetes.sql", "sql/006_perf_indexes.sql")) {
    Say "aplicando $sqlFile..."
    Get-Content $sqlFile -Raw | docker exec -i quantopagou-postgres psql -U quantopagou -d quantopagou -q *> $null
    if ($LASTEXITCODE -ne 0) { throw "psql $sqlFile falhou (exit=$LASTEXITCODE)" }
}

# ---------- python deps ----------

if (-not (Test-Path ".venv")) {
    Say "instalando deps Python (uv sync)..."
    python -m uv sync *> $null
    if ($LASTEXITCODE -ne 0) { throw "uv sync falhou (exit=$LASTEXITCODE)" }
}

# ---------- ingest + build_marts ----------

$rawCount = (docker exec quantopagou-postgres psql -U quantopagou -d quantopagou -t -A -c "SELECT COUNT(*) FROM raw.compras" 2>$null).Trim()
if ($rawCount -eq "" -or $rawCount -eq "0" -or $Fresh) {
    Say "ingerindo fixture sintetica (raw.compras vazio)..."
    python -m uv run python -m ingest --fixture data/fixtures/compras_sample.jsonl 2026-04-15 2026-04-15 *> $null
    if ($LASTEXITCODE -ne 0) { throw "ingest falhou (exit=$LASTEXITCODE) - veja .dev/ ou rode sem redirect para diagnosticar" }
} else {
    Say "raw.compras ja tem $rawCount linhas (use -Fresh para resetar)" DarkGray
}

Say "rodando analytics.build_marts (canonicalizacao + refresh)..."
python -m uv run python -m analytics.build_marts *> $null
if ($LASTEXITCODE -ne 0) { throw "analytics.build_marts falhou (exit=$LASTEXITCODE)" }

Say "rodando analytics.manchetes refresh (Camadas 2 e 3)..."
python -m uv run python -m analytics.manchetes refresh *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "    aviso: manchetes refresh falhou (exit=$LASTEXITCODE) - nao bloqueia stack" -ForegroundColor Yellow
}

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
        -WindowStyle Hidden -PassThru -ErrorAction Stop
    $pids.api = $proc.Id
    Write-Pids $pids
    Wait-Tcp $ApiPort "API"
}

# ---------- frontend ----------

if (-not $SkipFront) {
    if (-not (Test-Path "frontend/node_modules/next")) {
        Say "instalando deps do frontend (npm install)..."
        Push-Location frontend
        npm install --silent *> $null
        $npmExit = $LASTEXITCODE
        Pop-Location
        if ($npmExit -ne 0) { throw "npm install falhou (exit=$npmExit)" }
    }

    if (Process-Alive $pids.web) {
        Say "frontend ja rodando (pid=$($pids.web))" DarkGray
    } else {
        Say "subindo Next.js dev na porta $WebPort (log: .dev/web.log)..."
        Remove-Item -ErrorAction SilentlyContinue $webLog
        # npm.cmd no Windows; fallback npm.
        $npmCmdInfo = Get-Command npm.cmd -ErrorAction SilentlyContinue
        if ($npmCmdInfo) { $npmCmd = $npmCmdInfo.Source }
        else { $npmCmd = (Get-Command npm).Source }
        $proc = Start-Process -FilePath $npmCmd `
            -ArgumentList @("--prefix","frontend","run","dev","--","-p","$WebPort") `
            -RedirectStandardOutput $webLog -RedirectStandardError "$webLog.err" `
            -WindowStyle Hidden -PassThru -ErrorAction Stop
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
