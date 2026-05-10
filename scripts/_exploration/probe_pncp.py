"""Probe da API PNCP (Portal Nacional de Contratacoes Publicas).

Lei 14.133/2021 obriga publicacao no PNCP — backend independente do Compras.gov.br.
Tenta varios endpoints candidatos para descobrir granularidade e estrutura.
"""

from __future__ import annotations

import json
import time

import httpx

# Candidatos baseados no padrao publico documentado do PNCP.
# Se o usuario decidir adotar, mover constantes para src/ingest/pncp.py.
BASE = "https://pncp.gov.br/api/consulta"

PROBES: list[tuple[str, dict]] = [
    # 1. Contratos por data de publicacao (sucessor mais provavel do que tinhamos)
    (
        "/v1/contratos",
        {
            "dataInicial": "20260401",
            "dataFinal": "20260430",
            "pagina": 1,
            "tamanhoPagina": 10,
        },
    ),
    # 2. Contratos por data de vigencia (mesmo filtro do Compras.gov.br)
    (
        "/v1/contratos/atualizacao",
        {
            "dataInicial": "20260401",
            "dataFinal": "20260430",
            "pagina": 1,
            "tamanhoPagina": 10,
        },
    ),
    # 3. Contratacoes publicadas (licitacoes/dispensas)
    (
        "/v1/contratacoes/publicacao",
        {
            "dataInicial": "20260401",
            "dataFinal": "20260430",
            "codigoModalidadeContratacao": 6,  # pregao eletronico
            "pagina": 1,
            "tamanhoPagina": 10,
        },
    ),
    # 4. Atas de registro de preco
    (
        "/v1/atas",
        {
            "dataInicial": "20260401",
            "dataFinal": "20260430",
            "pagina": 1,
            "tamanhoPagina": 10,
        },
    ),
    # 5. Variantes com hifen na data e formato YYYY-MM-DD (alguns endpoints PNCP usam isso)
    (
        "/v1/contratos",
        {
            "dataInicial": "2026-04-01",
            "dataFinal": "2026-04-30",
            "pagina": 1,
            "tamanhoPagina": 10,
        },
    ),
    # 6. Healthcheck/raiz da API consulta
    ("/v1/", {}),
    ("", {}),
]


def probe(endpoint: str, params: dict) -> tuple[bool, dict | None]:
    url = BASE + endpoint
    t0 = time.monotonic()
    try:
        with httpx.Client(
            timeout=httpx.Timeout(60.0, connect=15.0),
            follow_redirects=True,
            headers={"Accept": "application/json"},
        ) as c:
            r = c.get(url, params=params)
    except Exception as e:
        print(f"  FAIL  ({time.monotonic()-t0:.1f}s)  {type(e).__name__}: {e}")
        return False, None
    elapsed = time.monotonic() - t0
    body = r.text[:200]
    print(f"  HTTP {r.status_code}  ({elapsed:.1f}s)  bytes={len(r.content)}")
    if r.status_code != 200:
        print(f"    body: {body!r}")
        return False, None
    try:
        data = r.json()
    except Exception:
        print(f"    nao-json: {body!r}")
        return False, None
    if isinstance(data, dict):
        keys = sorted(data.keys())
        print(f"    keys: {keys[:12]}")
        # Padroes comuns: paginas, total, data, content, items, resultado
        for arr_key in ("data", "content", "items", "resultado", "result"):
            if arr_key in data and isinstance(data[arr_key], list):
                arr = data[arr_key]
                print(f"    {arr_key}: len={len(arr)}")
                if arr:
                    sample = arr[0]
                    print(f"    sample keys: {sorted(sample.keys())[:15]}")
                    print(
                        f"    sample (200c): "
                        f"{json.dumps(sample, ensure_ascii=False)[:300]}"
                    )
                break
    elif isinstance(data, list):
        print(f"    array: len={len(data)}")
        if data:
            print(f"    sample keys: {sorted(data[0].keys())[:15]}")
    return True, data


def main() -> None:
    print(f"Probe PNCP @ {BASE}")
    print("=" * 60)
    for endpoint, params in PROBES:
        print(f"\nGET {endpoint}  params={params}")
        probe(endpoint, params)


if __name__ == "__main__":
    main()
