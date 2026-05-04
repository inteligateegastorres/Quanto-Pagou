"""Probe da API Compras.gov.br: tenta varias datas para achar uma que responde."""

from __future__ import annotations

import time

import httpx

BASE = "https://dadosabertos.compras.gov.br"

# (endpoint, params extras alem de pagina/tamanho)
ENDPOINTS = [
    (
        "/modulo-contratos/1_consultarContratos",
        {"dataVigenciaInicialMin": "2025-08-12", "dataVigenciaInicialMax": "2025-08-12"},
    ),
    (
        "/modulo-contratos/2_consultarContratosItem",
        {"dataVigenciaInicialMin": "2025-08-12", "dataVigenciaInicialMax": "2025-08-12"},
    ),
    (
        "/modulo-contratacoes/2_consultarItensContratacoes_PNCP_14133",
        {"dataInicial": "2025-08-12", "dataFinal": "2025-08-12"},
    ),
    (
        "/modulo-legado/4_consultarItensPregoes",
        {"dataResultado": "2024-11-01"},
    ),
    (
        "/modulo-arp/2_consultarARPItem",
        {"dataAssinaturaMin": "2025-08-12", "dataAssinaturaMax": "2025-08-12"},
    ),
]


def probe(endpoint: str, extras: dict) -> bool:
    t0 = time.monotonic()
    params = {"pagina": 1, "tamanhoPagina": 10, **extras}
    try:
        with httpx.Client(timeout=httpx.Timeout(120.0, connect=15.0)) as c:
            r = c.get(BASE + endpoint, params=params)
    except Exception as e:
        print(f"{endpoint}  FAIL  ({time.monotonic()-t0:.1f}s)  {type(e).__name__}: {e}")
        return False
    elapsed = time.monotonic() - t0
    if r.status_code != 200:
        print(f"{endpoint}  HTTP {r.status_code}  ({elapsed:.1f}s)  {r.text[:140]!r}")
        return False
    data = r.json()
    print(
        f"{endpoint}  OK  ({elapsed:.1f}s)  total={data.get('totalRegistros')}  "
        f"recebidos={len(data.get('resultado') or [])}"
    )
    if data.get("resultado"):
        s = data["resultado"][0]
        print(f"  amostra keys: {sorted(s.keys())[:10]}...")
    return True


def main() -> None:
    for ep, extras in ENDPOINTS:
        probe(ep, extras)


if __name__ == "__main__":
    main()
