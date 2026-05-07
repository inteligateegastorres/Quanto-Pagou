#!/usr/bin/env bash
# Quanto Pagou - sobe toda a stack local (Postgres + API + Frontend).
#
# Uso:
#   bash scripts/dev_up.sh            # idempotente
#   FRESH=1 bash scripts/dev_up.sh    # derruba volume do postgres + reseed
#   SKIP_FRONT=1 bash scripts/dev_up.sh
#
# Estado runtime fica em .dev/ (gitignored). Use scripts/dev_down.sh para parar.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

: "${API_PORT:=8000}"
: "${WEB_PORT:=3000}"
: "${FRESH:=0}"
: "${SKIP_FRONT:=0}"

DEV_DIR=".dev"
mkdir -p "$DEV_DIR"
PIDS_FILE="$DEV_DIR/pids.env"
API_LOG="$DEV_DIR/api.log"
WEB_LOG="$DEV_DIR/web.log"

say() { printf "\033[1;36m==> %s\033[0m\n" "$*"; }
warn() { printf "\033[1;33m==> %s\033[0m\n" "$*"; }
ok()   { printf "\033[1;32m==> %s\033[0m\n" "$*"; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "comando ausente: $1"; exit 1; }; }

wait_tcp() {
    local port="$1" label="$2" timeout="${3:-60}"
    say "aguardando $label em http://127.0.0.1:$port ..."
    local deadline=$(( $(date +%s) + timeout ))
    while [ "$(date +%s)" -lt "$deadline" ]; do
        if (echo > "/dev/tcp/127.0.0.1/$port") >/dev/null 2>&1; then return 0; fi
        sleep 0.5
    done
    echo "$label nao subiu em ${timeout}s (ver log em .dev/)" >&2
    exit 1
}

load_pid() { [ -f "$PIDS_FILE" ] && grep "^$1=" "$PIDS_FILE" | cut -d= -f2 || true; }
save_pid() {
    local key="$1" val="$2" tmp="${PIDS_FILE}.tmp"
    : > "$tmp"
    [ -f "$PIDS_FILE" ] && grep -v "^$key=" "$PIDS_FILE" >> "$tmp" || true
    echo "$key=$val" >> "$tmp"
    mv "$tmp" "$PIDS_FILE"
}
alive() { [ -n "${1:-}" ] && kill -0 "$1" 2>/dev/null; }

# ---------- pre-flight ----------
say "verificando dependencias..."
need docker
need python
[ "$SKIP_FRONT" = "1" ] || need npm

# Daemon do Docker no ar? (Desktop no Windows/macOS, ou systemctl no Linux)
if ! docker info >/dev/null 2>&1; then
    echo "ERRO: docker daemon nao esta rodando. Abra o Docker Desktop ou inicie o servico." >&2
    exit 1
fi

# ---------- postgres ----------
if [ "$FRESH" = "1" ]; then
    warn "modo FRESH: derrubando container + volume"
    docker compose down -v >/dev/null 2>&1 || true
fi

say "subindo postgres..."
docker compose up -d >/dev/null

say "aguardando postgres healthy..."
deadline=$(( $(date +%s) + 60 ))
until docker exec quantopagou-postgres pg_isready -U quantopagou -d quantopagou >/dev/null 2>&1; do
    [ "$(date +%s)" -ge "$deadline" ] && { echo "postgres nao healthy em 60s"; exit 1; }
    sleep 1
done

for sql_file in sql/001_analytics.sql sql/002_resilience.sql sql/003_tce_pr.sql; do
    say "aplicando $sql_file (idempotente)..."
    docker exec -i quantopagou-postgres psql -U quantopagou -d quantopagou -q < "$sql_file" >/dev/null
done

# ---------- python deps ----------
if [ ! -d ".venv" ]; then
    say "instalando deps Python (uv sync)..."
    python -m uv sync
fi

# ---------- ingest + build_marts ----------
RAW_COUNT=$(docker exec quantopagou-postgres psql -U quantopagou -d quantopagou -t -A -c "SELECT COUNT(*) FROM raw.compras" 2>/dev/null || echo 0)
RAW_COUNT=$(echo "$RAW_COUNT" | tr -d '[:space:]')
if [ "$RAW_COUNT" = "0" ] || [ "$FRESH" = "1" ]; then
    say "ingerindo fixture sintetica (raw.compras vazio)..."
    python -m uv run python -m ingest --fixture data/fixtures/compras_sample.jsonl 2026-04-15 2026-04-15 >/dev/null
else
    say "raw.compras ja tem $RAW_COUNT linhas (FRESH=1 para resetar)"
fi

say "rodando analytics.build_marts..."
python -m uv run python -m analytics.build_marts >/dev/null

# ---------- API ----------
API_PID=$(load_pid api)
if alive "$API_PID"; then
    say "API ja rodando (pid=$API_PID)"
else
    say "subindo API FastAPI na porta $API_PORT (log: .dev/api.log)..."
    : > "$API_LOG"
    nohup python -m uv run uvicorn api.main:app \
        --host 127.0.0.1 --port "$API_PORT" --log-level warning \
        >"$API_LOG" 2>&1 &
    save_pid api $!
    wait_tcp "$API_PORT" "API"
fi

# ---------- frontend ----------
if [ "$SKIP_FRONT" != "1" ]; then
    if [ ! -d "frontend/node_modules/next" ]; then
        say "instalando deps do frontend (npm install)..."
        (cd frontend && npm install --silent)
    fi
    WEB_PID=$(load_pid web)
    if alive "$WEB_PID"; then
        say "frontend ja rodando (pid=$WEB_PID)"
    else
        say "subindo Next.js dev na porta $WEB_PORT (log: .dev/web.log)..."
        : > "$WEB_LOG"
        nohup npm --prefix frontend run dev -- -p "$WEB_PORT" \
            >"$WEB_LOG" 2>&1 &
        save_pid web $!
        wait_tcp "$WEB_PORT" "frontend" 90
    fi
fi

# ---------- pronto ----------
echo
ok "stack no ar:"
echo "  Postgres : localhost:5433  (user/db: quantopagou)"
echo "  API      : http://127.0.0.1:$API_PORT       (docs: /docs)"
[ "$SKIP_FRONT" = "1" ] || echo "  Frontend : http://127.0.0.1:$WEB_PORT"
echo
echo "Para parar: bash scripts/dev_down.sh"
echo "Logs:       .dev/api.log .dev/web.log"
