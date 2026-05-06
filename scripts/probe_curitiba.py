"""Probe Prefeitura de Curitiba — descobrir endpoints estruturados de compras.

Curitiba historicamente tem reputacao de boa transparencia. Tentamos:
- Portal de Transparencia (frontend tem tabelas, pode ter export CSV)
- dadosabertos.curitiba.pr.gov.br (CKAN ou similar?)
- e-Compras Curitiba via licitacoes-e do Banco do Brasil (federacao)

Objetivo: descobrir se ha endpoint JSON com itens de contratos +
classificacao (CATMAT/CATSER ou codigo local) + valor pago.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

# Candidatos por ordem de probabilidade de sucesso
CANDIDATES = [
    # CKAN-style (padrao de portais de dados abertos brasileiros)
    "https://dadosabertos.curitiba.pr.gov.br/api/3/action/site_read",
    "https://dadosabertos.curitiba.pr.gov.br/api/3/action/package_list",
    "https://dadosabertos.curitiba.pr.gov.br/api/3/action/package_search?q=licitacao&rows=10",
    "https://dadosabertos.curitiba.pr.gov.br/api/3/action/package_search?q=contrato&rows=10",
    "https://dadosabertos.curitiba.pr.gov.br/api/3/action/package_search?q=compras&rows=10",
    # Portal de transparencia (talvez tenha API REST)
    "https://transparencia.curitiba.pr.gov.br/api/v1/contratos",
    "https://transparencia.curitiba.pr.gov.br/api/contratos",
    # PMC outros padroes
    "https://www.curitiba.pr.gov.br/dadosabertos/api",
]


def main() -> None:
    out_dir = Path("data/fixtures")
    out_dir.mkdir(parents=True, exist_ok=True)

    sample_collected: dict[str, object] = {}

    with httpx.Client(
        timeout=httpx.Timeout(60.0, connect=15.0),
        follow_redirects=True,
        headers={"Accept": "application/json", "User-Agent": "QuantoPagouProbe/0.1"},
    ) as c:
        for url in CANDIDATES:
            print(f"\nGET {url}")
            t0 = time.monotonic()
            try:
                r = c.get(url)
            except Exception as e:
                print(f"  FAIL  {type(e).__name__}: {e}")
                continue
            elapsed = time.monotonic() - t0
            ctype = r.headers.get("content-type", "")
            print(f"  HTTP {r.status_code}  ({elapsed:.1f}s)  ct={ctype[:40]}  bytes={len(r.content)}")
            if r.status_code != 200:
                print(f"    body: {r.text[:200]!r}")
                continue
            if "json" in ctype.lower():
                try:
                    data = r.json()
                    if isinstance(data, dict):
                        # CKAN: result.success indica resposta valida
                        if "result" in data:
                            result = data["result"]
                            print(f"    CKAN result type: {type(result).__name__}")
                            if isinstance(result, list):
                                print(f"    list len: {len(result)}")
                                if result and len(result) > 0:
                                    print(f"    first: {result[:5]}")
                            elif isinstance(result, dict):
                                if "results" in result:
                                    res_list = result["results"]
                                    print(f"    results len: {len(res_list)}")
                                    for r2 in res_list[:5]:
                                        if isinstance(r2, dict):
                                            print(f"      - {r2.get('title','?')!r}")
                                            print(f"        {r2.get('name','?')}")
                                            for res_item in (r2.get("resources") or [])[:3]:
                                                print(
                                                    f"          [{res_item.get('format','?')}] "
                                                    f"{res_item.get('name','?')[:60]} "
                                                    f"{res_item.get('url','')[:80]}"
                                                )
                                else:
                                    print(f"    keys: {sorted(result.keys())[:15]}")
                                    print(f"    sample: {json.dumps(result, ensure_ascii=False)[:300]}")
                        else:
                            print(f"    keys: {sorted(data.keys())[:10]}")
                            print(f"    body: {json.dumps(data, ensure_ascii=False)[:300]}")
                        sample_collected[url] = data
                    elif isinstance(data, list):
                        print(f"    array len: {len(data)}")
                        if data:
                            print(f"    sample: {json.dumps(data[0], ensure_ascii=False)[:300]}")
                except Exception as e:
                    print(f"    nao-json valido: {e}")
                    print(f"    body: {r.text[:300]!r}")
            else:
                print(f"    body (nao-json): {r.text[:300]!r}")

    if sample_collected:
        out = out_dir / "curitiba_probe_sample.json"
        out.write_text(
            json.dumps(sample_collected, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nSalvou amostras em {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
