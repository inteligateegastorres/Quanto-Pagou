"""Probe v3: vai direto nos endpoints concretos descobertos no v2."""

from __future__ import annotations

import re
import time

import httpx

CANDIDATES = [
    # ---------- Querido Diario ----------
    # Subdominios comuns para API
    ("QD-api-subdom", "https://api.queridodiario.ok.org.br/", {}),
    ("QD-api-cities", "https://api.queridodiario.ok.org.br/cities", {"city_name": "Curitiba", "level": 1}),
    ("QD-api-gazettes", "https://api.queridodiario.ok.org.br/gazettes", {"territory_ids": "4106902", "size": 3}),
    ("QD-api-docs", "https://api.queridodiario.ok.org.br/docs", {}),
    ("QD-api-openapi", "https://api.queridodiario.ok.org.br/openapi.json", {}),
    # Backend.queridodiario? Dataset HuggingFace?
    ("QD-backend", "https://backend.queridodiario.ok.org.br/", {}),
    # Se nada disso, procurar no HTML do frontend mencao a endpoint
    ("QD-frontend", "https://queridodiario.ok.org.br/", {}),
    # ---------- Curitiba ----------
    # Pegar HTML completo do catalogo e procurar dataset real
    ("CWB-catalogo-full", "https://dadosabertos.curitiba.pr.gov.br/", {}),
    # Tentar paths comuns de portal de transparencia que viram links nos catalogos
    ("CWB-trans-paginicial", "http://www.transparencia.curitiba.pr.gov.br/", {}),  # http
    ("CWB-cwbnet", "https://transparencia.curitiba.pr.gov.br/Pages/Inicial.aspx", {}),
    # API CKAN da prefeitura, padrao .br comum:
    ("CWB-ckan-action", "https://dadosabertos.curitiba.pr.gov.br/api/3/action/group_list", {}),
    # ---------- TCE-PR ----------
    # Link real descoberto no v2:
    ("TCE-pit-contratos", "https://pit.tce.pr.gov.br/ContratoConsulta/Consulta", {}),
    ("TCE-pit-licitacao", "https://pit.tce.pr.gov.br/Licitacao", {}),
    ("TCE-pit-root", "https://pit.tce.pr.gov.br/", {}),
    # Talvez tenha API REST por tras
    ("TCE-pit-api", "https://pit.tce.pr.gov.br/api", {}),
    ("TCE-mural-mun", "https://www.tce.pr.gov.br/fiscalizado/mural-de-licitacoes-cadastro-de-licitacoes-municipais/", {}),
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
            final_url = str(r.url)
            print(f"  HTTP {r.status_code} ({elapsed:.1f}s) ct={ctype[:40]} bytes={len(r.content)}")
            if final_url != url and final_url != url + "/":
                print(f"    redirect -> {final_url}")
            if r.status_code != 200 and r.status_code != 301 and r.status_code != 302:
                print(f"    body: {r.text[:200]!r}")
                continue

            if "json" in ctype.lower():
                try:
                    data = r.json()
                    print(f"    JSON ok")
                    if isinstance(data, dict):
                        if "openapi" in data or "swagger" in data:
                            paths = list((data.get("paths") or {}).keys())
                            print(f"    OPENAPI! paths ({len(paths)}):")
                            for p in paths[:25]:
                                print(f"      {p}")
                        else:
                            print(f"    keys: {sorted(data.keys())[:12]}")
                            print(f"    body: {str(data)[:400]}")
                    elif isinstance(data, list):
                        print(f"    list len: {len(data)}")
                        if data:
                            print(f"    sample: {str(data[0])[:300]}")
                except Exception as e:
                    print(f"    JSON parse fail: {e}")
            else:
                body = r.text
                # Procura referencias a APIs no JS embutido
                api_refs = re.findall(
                    r'(?:https?://)?[a-zA-Z0-9_.-]*queridodiario\.ok\.org\.br[/a-zA-Z0-9_-]*',
                    body,
                )
                api_refs += re.findall(
                    r'fetch\(["\']([^"\']{3,200})["\']',
                    body,
                )
                api_refs += re.findall(
                    r'apiUrl["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                    body,
                    re.IGNORECASE,
                )
                api_refs += re.findall(
                    r'baseURL["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                    body,
                    re.IGNORECASE,
                )
                if api_refs:
                    print(f"    refs a API ({len(api_refs)}):")
                    for ref in list(dict.fromkeys(api_refs))[:10]:
                        print(f"      {ref}")
                # Datasets em listas
                ds_links = re.findall(
                    r'href="([^"]*(?:dataset|contrato|licitac|compra|empenho|api)[^"]*)"',
                    body,
                    re.IGNORECASE,
                )
                if ds_links:
                    print(f"    links de interesse ({len(ds_links)}):")
                    for L in list(dict.fromkeys(ds_links))[:15]:
                        print(f"      {L}")
                # Datasets via formato
                fmt_links = re.findall(
                    r'href="([^"]*\.(?:csv|json|xml|zip|geojson|xlsx?))"',
                    body,
                    re.IGNORECASE,
                )
                if fmt_links:
                    print(f"    arquivos diretos ({len(fmt_links)}):")
                    for L in list(dict.fromkeys(fmt_links))[:10]:
                        print(f"      {L}")

                if not (api_refs or ds_links or fmt_links):
                    snippet = re.sub(r"\s+", " ", body[:500])
                    print(f"    HTML: {snippet[:300]!r}")


if __name__ == "__main__":
    main()
