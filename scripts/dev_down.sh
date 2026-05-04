#!/usr/bin/env bash
# Quanto Pagou - derruba a stack local (oposto de dev_up.sh).
#
# Uso:
#   bash scripts/dev_down.sh         # para API + Frontend; postgres continua
#   ALL=1   bash scripts/dev_down.sh # tambem para postgres (preserva volume)
#   WIPE=1  bash scripts/dev_down.sh # para tudo + apaga volume (perde dados)
#
# Estrategia: tenta matar a arvore do PID registrado e, como rede de seguranca,
# tambem mata o que estiver escutando nas portas conhecidas.

set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

: "${ALL:=0}"
: "${WIPE:=0}"
: "${API_PORT:=8000}"
: "${WEB_PORT:=3000}"
PIDS_FILE=".dev/pids.env"

say() { printf "\033[1;36m==> %s\033[0m\n" "$*"; }
warn() { printf "\033[1;33m==> %s\033[0m\n" "$*"; }

stop_pid() {
    local label="$1" pid="$2"
    [ -z "${pid:-}" ] && return
    if kill -0 "$pid" 2>/dev/null; then
        say "matando $label (pid=$pid)..."
        if command -v pkill >/dev/null 2>&1; then
            pkill -P "$pid" 2>/dev/null || true
        fi
        kill "$pid" 2>/dev/null || true
        sleep 0.3
        kill -9 "$pid" 2>/dev/null || true
    fi
}

# Mata o que estiver escutando na porta (rede de seguranca para wrappers orfaos).
stop_port() {
    local label="$1" port="$2" found=0
    if command -v lsof >/dev/null 2>&1; then
        for pid in $(lsof -ti tcp:"$port" 2>/dev/null); do
            say "matando $label na porta $port (pid=$pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 0.2
            kill -9 "$pid" 2>/dev/null || true
            found=1
        done
    elif command -v fuser >/dev/null 2>&1; then
        if fuser -k "$port"/tcp 2>/dev/null; then
            say "matei processo na porta $port"
            found=1
        fi
    fi
    return $((! found))
}

if [ -f "$PIDS_FILE" ]; then
    WEB_PID=$(grep "^web=" "$PIDS_FILE" | cut -d= -f2 || true)
    API_PID=$(grep "^api=" "$PIDS_FILE" | cut -d= -f2 || true)
    stop_pid "frontend" "$WEB_PID"
    stop_pid "API" "$API_PID"
    rm -f "$PIDS_FILE"
fi

stop_port "API" "$API_PORT" || true
stop_port "frontend" "$WEB_PORT" || true

if [ "$WIPE" = "1" ]; then
    warn "derrubando postgres + apagando volume (WIPE=1)..."
    docker compose down -v >/dev/null 2>&1 || true
elif [ "$ALL" = "1" ]; then
    say "parando postgres (volume preservado)..."
    docker compose stop >/dev/null 2>&1 || true
else
    say "postgres continua rodando (use ALL=1 para parar)"
fi

printf "\033[1;32m==> ok\033[0m\n"
