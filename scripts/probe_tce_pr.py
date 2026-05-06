"""Probe TCE-PR — Tribunal de Contas do Estado do Parana.

Buscamos: API REST com contratos/licitacoes do estado + municipios PR
fiscalizados pelo TCE-PR.

TCE-PR usa o sistema 'e-Sfinge' (envio de dados pelos jurisdicionados)
e 'Sistema de Informacoes Municipais' (SIM-AM).

Candidatos:
- servicos.tce.pr.gov.br/tcepr (sistemas web; podem expor JSON em rotas)
- www1.tce.pr.gov.br/conteudo/dados-abertos (catalogo)
- API/feed RSS de fiscalizacoes
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

CANDIDATES = [
    # Padrao tipico de portais de governo BR
    "https://www1.tce.pr.gov.br/conteudo/dados-abertos",
    # Possiveis CKANs/APIs
    "https://dadosabertos.tce.pr.gov.br/api/3/action/package_list",
    "https://dadosabertos.tce.pr.gov.br/api/3/action/package_search?q=contrato",
    "https://dadosabertos.tce.pr.gov.br/api/3/action/package_search?q=licitacao",
    # Servicos
    "https://servicos.tce.pr.gov.br/tcepr/api/contratos",
    "https://servicos.tce.pr.gov.br/tcepr/dados-abertos/api",
    # SIM-AM exposicoes
    "https://servicos.tce.pr.gov.br/tcepr/SIMAM/api",
    # Variante https://transparencia.tce.pr.gov.br
    "https://transparencia.tce.pr.gov.br/api",
    "https://transparencia.tce.pr.gov.br/api/v1/dados",
]


def main() -> None:
    out_dir = Path("data/fixtures")
    out_dir.mkdir(parents=True, exist_ok=True)

    sample_collected: dict[str, object] = {}

    with httpx.Client(
        timeout=httpx.Timeout(45.0, connect=15.0),
        follow_redirects=True,
        headers={
            "Accept": "application/json, text/html",
            "User-Agent": "QuantoPagouProbe/0.1",
        },
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
                        if "result" in data:
                            result = data["result"]
                            if isinstance(result, list):
                                print(f"    CKAN list len: {len(result)}")
                                if result:
                                    print(f"    first: {result[:5]}")
                            elif isinstance(result, dict) and "results" in result:
                                res_list = result["results"]
                                print(f"    CKAN results: {len(res_list)}")
                                for r2 in res_list[:5]:
                                    if isinstance(r2, dict):
                                        print(f"      - {r2.get('title','?')[:80]!r}")
                                        for res_item in (r2.get("resources") or [])[:2]:
                                            print(
                                                f"          [{res_item.get('format','?')}] "
                                                f"{res_item.get('url','')[:80]}"
                                            )
                            else:
                                print(f"    keys: {sorted(data.keys())[:10]}")
                                print(f"    body: {json.dumps(data, ensure_ascii=False)[:300]}")
                        else:
                            print(f"    keys: {sorted(data.keys())[:10]}")
                            print(f"    body: {json.dumps(data, ensure_ascii=False)[:300]}")
                        sample_collected[url] = data
                    elif isinstance(data, list):
                        print(f"    array len: {len(data)}")
                        if data:
                            print(f"    sample: {json.dumps(data[0], ensure_ascii=False)[:300]}")
                            sample_collected[url] = data[:3]
                except Exception as e:
                    print(f"    nao-json valido: {e}")
                    print(f"    body: {r.text[:300]!r}")
            elif "html" in ctype.lower():
                # Pode ser pagina de catalogo. Procurar links a JSON/CSV.
                body = r.text
                snippet = body[:500].replace("\n", " ").replace("\r", " ")
                print(f"    HTML preview: {snippet!r}")
                # Procura links a CSV/JSON/datasets
                import re
                links = re.findall(r'href="([^"]*\.(?:csv|json|xml|zip))"', body, re.IGNORECASE)
                if links:
                    print(f"    links a dados encontrados ({len(links)}):")
                    for L in links[:10]:
                        print(f"      {L}")
            else:
                print(f"    body: {r.text[:300]!r}")

    if sample_collected:
        out = out_dir / "tce_pr_probe_sample.json"
        out.write_text(
            json.dumps(sample_collected, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nSalvou amostras em {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
