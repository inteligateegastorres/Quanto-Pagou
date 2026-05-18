#!/usr/bin/env bash
# Quanto Pagou - sincronizacao com a API Compras.gov.br.
#
# Roda o ingest contra dadosabertos.compras.gov.br (sem --fixture) com window
# splitting recursivo: se uma janela inteira falhar com erro transitorio
# (backend JPA caindo), divide em metades e tenta cada uma. Janelas que falham
# mesmo com 1 dia ficam como snapshot 'failed' em raw.snapshots — pipeline segue.
#
# Postgres precisa estar no ar (use scripts/dev_up.sh para subir).
#
# Desde 2026-05-18 (PLANO §19.11): o endpoint /modulo-contratos exige
# codigoOrgao obrigatorio. O spider agora itera analytics.orgao_federal
# (esfera=F + status_ativo). Rode `python -m ingest orgaos` antes para
# popular o cadastro de orgaos (idempotente, ~30s).
#
# Uso:
#   bash scripts/sync_compras.sh                   # ultimos 7 dias, todos orgaos federais
#   DAYS=30 bash scripts/sync_compras.sh           # ultimos 30 dias
#   START=2026-04-01 END=2026-04-30 bash scripts/sync_compras.sh
#   ORGAOS="26298,20000" bash scripts/sync_compras.sh   # so estes orgaos
#   ORGAOS_LIMIT=5 bash scripts/sync_compras.sh    # smoke test (5 primeiros)
#   MAX_PAGES=2 bash scripts/sync_compras.sh       # smoke (2 paginas por janela)
#   NO_SPLIT=1 bash scripts/sync_compras.sh        # 1 tentativa por orgao, sem split de data
#   MIN_WINDOW_DAYS=7 bash scripts/sync_compras.sh # nao divide abaixo de 7 dias
#   SKIP_BUILD=1 bash scripts/sync_compras.sh      # nao refaz marts
#
# Logs em .dev/sync_compras.log. Snapshots em snapshots/compras_gov_br/.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

: "${DAYS:=7}"
: "${START:=}"
: "${END:=}"
: "${PAGE_SIZE:=500}"
: "${MAX_PAGES:=}"
: "${ORGAOS:=all}"
: "${ORGAOS_LIMIT:=}"
: "${NO_SPLIT:=0}"
: "${MIN_WINDOW_DAYS:=1}"
: "${SKIP_BUILD:=0}"

DEV_DIR=".dev"
mkdir -p "$DEV_DIR"
LOG_FILE="$DEV_DIR/sync_compras.log"

say() { printf "\033[1;36m==> %s\033[0m\n" "$*"; }
ok()  { printf "\033[1;32m==> %s\033[0m\n" "$*"; }
err() { printf "\033[1;31m==> %s\033[0m\n" "$*" >&2; }
need() { command -v "$1" >/dev/null 2>&1 || { err "comando ausente: $1"; exit 1; }; }

is_iso_date() { [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; }

# ---------- resolve janela ----------
if [ -n "$START" ] || [ -n "$END" ]; then
    if [ -z "$START" ] || [ -z "$END" ]; then
        err "START e END devem ser usados juntos (ou nenhum, para usar DAYS)"
        exit 1
    fi
    is_iso_date "$START" || { err "START invalido: '$START' (esperado YYYY-MM-DD)"; exit 1; }
    is_iso_date "$END"   || { err "END invalido: '$END' (esperado YYYY-MM-DD)"; exit 1; }
else
    if ! [[ "$DAYS" =~ ^[0-9]+$ ]] || [ "$DAYS" -lt 1 ]; then
        err "DAYS deve ser inteiro >= 1 (atual: '$DAYS')"
        exit 1
    fi
    END=$(date +%Y-%m-%d)
    # GNU date vs BSD date (macOS): tenta os dois.
    START=$(date -d "$END - $DAYS days" +%Y-%m-%d 2>/dev/null \
            || date -v-"$DAYS"d -j -f %Y-%m-%d "$END" +%Y-%m-%d)
fi

# ---------- pre-flight ----------
say "verificando dependencias..."
need docker
need python

say "checando postgres (quantopagou-postgres)..."
if ! docker exec quantopagou-postgres pg_isready -U quantopagou -d quantopagou >/dev/null 2>&1; then
    err "postgres nao esta no ar. Rode bash scripts/dev_up.sh antes."
    exit 1
fi

# ---------- ingest ----------
ingest_args=( -m uv run python -m ingest "$START" "$END" --page-size "$PAGE_SIZE" --orgaos "$ORGAOS" )
if [ -n "$ORGAOS_LIMIT" ]; then
    ingest_args+=( --orgaos-limit "$ORGAOS_LIMIT" )
fi
if [ -n "$MAX_PAGES" ]; then
    ingest_args+=( --max-pages "$MAX_PAGES" )
fi
if [ "$NO_SPLIT" = "1" ]; then
    ingest_args+=( --no-split )
    split_desc="no-split"
else
    ingest_args+=( --min-window-days "$MIN_WINDOW_DAYS" )
    split_desc="split min=${MIN_WINDOW_DAYS}d"
fi

orgaos_desc="orgaos=$ORGAOS"
if [ -n "$ORGAOS_LIMIT" ]; then orgaos_desc+=" limit=$ORGAOS_LIMIT"; fi
window_desc="$START -> $END (page_size=$PAGE_SIZE, $orgaos_desc, $split_desc"
if [ -n "$MAX_PAGES" ]; then
    window_desc+=", max_pages=$MAX_PAGES"
fi
window_desc+=")"

say "ingest API Compras.gov.br: $window_desc"
say "log completo em: $LOG_FILE"

started=$(date +%s)
# tee pra log + console; PIPESTATUS preserva exit code do python.
python "${ingest_args[@]}" 2>&1 | tee "$LOG_FILE"
ingest_exit=${PIPESTATUS[0]}
elapsed=$(( $(date +%s) - started ))

# Exit codes: 0 = sucesso (parcial OK), 2 = nada ingerido, outro = inesperado.
if [ "$ingest_exit" -eq 2 ]; then
    err "ingest: TODAS as janelas falharam apos ${elapsed}s. Log: $LOG_FILE"
    err "API Compras.gov.br pode estar com backend caido. Tente MIN_WINDOW_DAYS=1 ou aguarde."
    exit 2
elif [ "$ingest_exit" -ne 0 ]; then
    err "ingest falhou inesperado (exit=$ingest_exit) apos ${elapsed}s. Log: $LOG_FILE"
    exit "$ingest_exit"
fi
ok "ingest ok em ${elapsed}s (sucessos parciais sao normais; veja sumario acima)"

# ---------- build_marts ----------
if [ "$SKIP_BUILD" = "1" ]; then
    say "pulando analytics.build_marts (SKIP_BUILD=1)"
else
    say "rodando analytics.build_marts (canonicalizacao + refresh views)..."
    started=$(date +%s)
    python -m uv run python -m analytics.build_marts 2>&1 | tee -a "$LOG_FILE"
    build_exit=${PIPESTATUS[0]}
    elapsed=$(( $(date +%s) - started ))
    if [ "$build_exit" -ne 0 ]; then
        err "build_marts falhou (exit=$build_exit) apos ${elapsed}s. Log: $LOG_FILE"
        exit "$build_exit"
    fi
    ok "build_marts ok em ${elapsed}s"
fi

# ---------- resumo ----------
echo
ok "sincronizacao concluida"
echo "  janela    : $START -> $END"
echo "  log       : $LOG_FILE"
echo "  snapshots : snapshots/compras_gov_br/"
if [ "$SKIP_BUILD" != "1" ]; then
    echo
    echo "Marts atualizados. API e frontend ja refletem os novos dados."
fi
