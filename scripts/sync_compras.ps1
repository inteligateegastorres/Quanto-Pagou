# Quanto Pagou - sincronizacao com a API Compras.gov.br.
#
# Roda o ingest contra dadosabertos.compras.gov.br (sem --fixture) com window
# splitting recursivo: se uma janela inteira falhar com erro transitorio
# (backend JPA caindo), divide em metades e tenta cada uma. Janelas que falham
# mesmo com 1 dia ficam como snapshot 'failed' em raw.snapshots — pipeline
# segue. Em seguida refaz os marts.
#
# Postgres precisa estar no ar (use scripts/dev_up.ps1 para subir).
#
# Desde 2026-05-18 (PLANO §19.11): o endpoint /modulo-contratos exige
# codigoOrgao obrigatorio. O spider agora itera analytics.orgao_federal
# (esfera=F + status_ativo). Rode `python -m ingest orgaos` antes para
# popular o cadastro de orgaos (idempotente, ~30s).
#
# Uso:
#   pwsh scripts/sync_compras.ps1                          # ultimos 7 dias, todos orgaos federais
#   pwsh scripts/sync_compras.ps1 -Days 30                 # ultimos 30 dias
#   pwsh scripts/sync_compras.ps1 -Start 2026-04-01 -End 2026-04-30
#   pwsh scripts/sync_compras.ps1 -Orgaos "26298,20000"    # so estes orgaos
#   pwsh scripts/sync_compras.ps1 -OrgaosLimit 5           # smoke test (5 primeiros)
#   pwsh scripts/sync_compras.ps1 -MaxPages 2              # smoke test (2 paginas por janela)
#   pwsh scripts/sync_compras.ps1 -NoSplit                 # 1 tentativa por orgao, sem split de data
#   pwsh scripts/sync_compras.ps1 -MinWindowDays 7         # nao divide abaixo de 7 dias
#   pwsh scripts/sync_compras.ps1 -SkipBuild               # nao refaz marts
#
# Logs ficam em .dev/sync_compras.log. Snapshots brutos em snapshots/compras_gov_br/.

[CmdletBinding()]
param(
    [int]$Days = 7,
    [string]$Start,
    [string]$End,
    [int]$PageSize = 500,
    [Nullable[int]]$MaxPages,
    [string]$Orgaos = "all",
    [Nullable[int]]$OrgaosLimit,
    [switch]$NoSplit,
    [int]$MinWindowDays = 1,
    [switch]$SkipBuild
)

# Veja comentario em dev_up.ps1: Stop dispara NativeCommandError em PS 5.1
# quando comandos nativos escrevem em stderr (warnings benignos do docker).
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$devDir = Join-Path $root ".dev"
New-Item -ItemType Directory -Force -Path $devDir | Out-Null
$logFile = Join-Path $devDir "sync_compras.log"

function Say($msg, $color = "Cyan") {
    Write-Host "==> $msg" -ForegroundColor $color
}

function Need-Cmd($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "comando nao encontrado: $name"
    }
}

# ---------- resolve janela ----------

if ($Start -or $End) {
    if (-not ($Start -and $End)) {
        throw "-Start e -End devem ser usados juntos (ou nenhum, para usar -Days)"
    }
    try { $startDate = [datetime]::ParseExact($Start, "yyyy-MM-dd", $null) }
    catch { throw "-Start invalido: '$Start' (esperado YYYY-MM-DD)" }
    try { $endDate = [datetime]::ParseExact($End, "yyyy-MM-dd", $null) }
    catch { throw "-End invalido: '$End' (esperado YYYY-MM-DD)" }
} else {
    if ($Days -lt 1) { throw "-Days deve ser >= 1" }
    $endDate = (Get-Date).Date
    $startDate = $endDate.AddDays(-$Days)
    $Start = $startDate.ToString("yyyy-MM-dd")
    $End = $endDate.ToString("yyyy-MM-dd")
}

if ($startDate -gt $endDate) { throw "Start ($Start) > End ($End)" }

# ---------- pre-flight ----------

Say "verificando dependencias..."
Need-Cmd "docker"
Need-Cmd "python"

Say "checando postgres (quantopagou-postgres)..." DarkGray
docker exec quantopagou-postgres pg_isready -U quantopagou -d quantopagou *> $null
if ($LASTEXITCODE -ne 0) {
    throw "postgres nao esta no ar. Rode .\scripts\dev_up.ps1 antes."
}

# ---------- ingest ----------

$argsList = @(
    "-m","uv","run","python","-m","ingest",
    $Start, $End,
    "--page-size", "$PageSize",
    "--orgaos", $Orgaos
)
if ($null -ne $OrgaosLimit) {
    $argsList += @("--orgaos-limit", "$OrgaosLimit")
}
if ($null -ne $MaxPages) {
    $argsList += @("--max-pages", "$MaxPages")
}
if ($NoSplit) {
    $argsList += "--no-split"
} else {
    $argsList += @("--min-window-days", "$MinWindowDays")
}

$totalDays = ($endDate - $startDate).Days + 1
$splitDesc = if ($NoSplit) { "no-split" } else { "split min=${MinWindowDays}d" }
$orgaosDesc = if ($null -ne $OrgaosLimit) { "orgaos=$Orgaos limit=$OrgaosLimit" } else { "orgaos=$Orgaos" }
$windowDesc = "$Start -> $End (${totalDays}d, page_size=$PageSize, $orgaosDesc, $splitDesc"
if ($null -ne $MaxPages) { $windowDesc += ", max_pages=$MaxPages" }
$windowDesc += ")"

Say "ingest API Compras.gov.br: $windowDesc" Cyan
Say "log completo em: $logFile" DarkGray

# Roda em foreground com tee pra log: queremos ver progresso no console + persistir.
# 2>&1 merge no PowerShell + passagem por Out-Host preserva a saida ao vivo.
$started = Get-Date
& python @argsList 2>&1 | Tee-Object -FilePath $logFile | Out-Host
$ingestExit = $LASTEXITCODE
$elapsed = ((Get-Date) - $started).TotalSeconds

# Exit codes do CLI ingest:
#   0 = sucesso total ou parcial (alguma janela ingerida)
#   2 = nada ingerido (todas janelas falharam)
#   outro = erro inesperado
if ($ingestExit -eq 2) {
    Say "ingest: TODAS as janelas falharam apos $([int]$elapsed)s. Log: $logFile" Red
    Say "API Compras.gov.br pode estar com backend caido. Tente -MinWindowDays 1 ou aguarde." DarkGray
    if ($SkipBuild) { exit 2 }
    Say "pulando build_marts (sem dados novos)" DarkGray
    exit 2
} elseif ($ingestExit -ne 0) {
    throw "ingest falhou inesperado (exit=$ingestExit) apos $([int]$elapsed)s. Log: $logFile"
}

Say "ingest ok em $([int]$elapsed)s (sucessos parciais sao normais; veja sumario acima)" Green

# ---------- build_marts ----------

if ($SkipBuild) {
    Say "pulando analytics.build_marts (-SkipBuild)" DarkGray
} else {
    Say "rodando analytics.build_marts (canonicalizacao + refresh views)..."
    $started = Get-Date
    & python -m uv run python -m analytics.build_marts 2>&1 | Tee-Object -FilePath $logFile -Append | Out-Host
    $buildExit = $LASTEXITCODE
    $elapsed = ((Get-Date) - $started).TotalSeconds
    if ($buildExit -ne 0) {
        throw "build_marts falhou (exit=$buildExit) apos $([int]$elapsed)s. Log: $logFile"
    }
    Say "build_marts ok em $([int]$elapsed)s" Green
}

# ---------- resumo ----------

Write-Host ""
Say "sincronizacao concluida" Green
Write-Host "  janela    : $Start -> $End"
Write-Host "  log       : $logFile"
Write-Host "  snapshots : snapshots/compras_gov_br/"
if (-not $SkipBuild) {
    Write-Host ""
    Write-Host "Marts atualizados. API e frontend ja refletem os novos dados." -ForegroundColor DarkGray
}
