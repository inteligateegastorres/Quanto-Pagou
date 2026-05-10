"""Probe v2: refina exploracao apos probe inicial.

Querido Diario (api/* devolveu HTML do frontend; tentar /api/v1/...);
Curitiba (transparencia derruba conexao; dadosabertos retorna HTML — vamos
escrapear catalogo ou tentar root); TCE-PR (sem subdominio dadosabertos).
"""

from __future__ import annotations

import re
import time

import httpx

CANDIDATES = [
    # ---------- Querido Diario ----------
    # API oficial documentada esta em /api/v1/
    ("QD-cities", "https://queridodiario.ok.org.br/api/v1/cities", {"city_name": "Curitiba", "level": 1}),
    ("QD-gazettes", "https://queridodiario.ok.org.br/api/v1/gazettes", {"territory_ids": "4106902", "size": 3}),
    ("QD-openapi", "https://queridodiario.ok.org.br/api/v1/openapi.json", {}),
    # Doc swagger
    ("QD-docs", "https://queridodiario.ok.org.br/api/v1/docs", {}),
    # ---------- Curitiba ----------
    # Root do portal de transparencia
    ("CWB-trans-root", "https://transparencia.curitiba.pr.gov.br", {}),
    ("CWB-trans-novo", "https://transparencia.curitiba.pr.gov.br/Home", {}),
    # Dados abertos catalogo
    ("CWB-dados-root", "https://dadosabertos.curitiba.pr.gov.br/", {}),
    ("CWB-licitacoes", "https://www.curitiba.pr.gov.br/dadosabertos/dataset/licitacoes-em-andamento", {}),
    ("CWB-contratos", "https://www.curitiba.pr.gov.br/dadosabertos/dataset/contratos", {}),
    # ---------- TCE-PR ----------
    ("TCE-root", "https://www.tce.pr.gov.br/", {}),
    ("TCE-dados-abertos", "https://www.tce.pr.gov.br/dados-abertos", {}),
    ("TCE-portal", "https://servicos.tce.pr.gov.br/tcepr/", {}),
]


def main() -> None:
    with httpx.Client(
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=True,
        headers={
            "Accept": "application/json, text/html",
            "User-Agent": "Mozilla/5.0 (compatible; QuantoPagouProbe/0.1)",
        },
    ) as c:
        for label, url, params in CANDIDATES:
            print(f"\n[{label}] GET {url}")
            t0 = time.monotonic()
            try:
                r = c.get(url, params=params)
            except Exception as e:
                print(f"  FAIL  {type(e).__name__}: {str(e)[:120]}")
                continue
            elapsed = time.monotonic() - t0
            ctype = r.headers.get("content-type", "")
            print(f"  HTTP {r.status_code} ({elapsed:.1f}s) ct={ctype[:40]} bytes={len(r.content)}")
            if r.status_code != 200:
                print(f"    body: {r.text[:200]!r}")
                continue

            if "json" in ctype.lower():
                try:
                    data = r.json()
                    print("    JSON OK")
                    if isinstance(data, dict):
                        print(f"    keys: {sorted(data.keys())[:12]}")
                        # OpenAPI?
                        if "openapi" in data or "swagger" in data:
                            paths = list((data.get("paths") or {}).keys())[:15]
                            print(f"    PATHS: {paths}")
                        else:
                            preview = {k: v for k, v in list(data.items())[:5]}
                            print(f"    sample: {str(preview)[:300]}")
                    elif isinstance(data, list):
                        print(f"    list len: {len(data)}")
                        if data:
                            print(f"    sample: {str(data[0])[:300]}")
                except Exception as e:
                    print(f"    JSON parse fail: {e}")
                    print(f"    body: {r.text[:200]!r}")
            else:
                # HTML — extrair links a datasets
                body = r.text
                links = re.findall(
                    r'href="([^"]*\.(?:csv|json|xml|zip|geojson|xlsx?))"',
                    body,
                    re.IGNORECASE,
                )
                if links:
                    print(f"    links a dados ({len(links)}):")
                    for L in list(dict.fromkeys(links))[:10]:
                        print(f"      {L}")
                # Procura tambem por links a datasets/contratos no HTML
                ds_links = re.findall(
                    r'href="([^"]*(?:dataset|contrato|licitac|compra)[^"]*)"',
                    body,
                    re.IGNORECASE,
                )
                if ds_links:
                    print(f"    links a paginas dataset/contrato/licit ({len(ds_links)}):")
                    for L in list(dict.fromkeys(ds_links))[:10]:
                        print(f"      {L}")
                if not links and not ds_links:
                    snippet = re.sub(r"\s+", " ", body[:500])
                    print(f"    HTML: {snippet[:200]!r}")


if __name__ == "__main__":
    main()
