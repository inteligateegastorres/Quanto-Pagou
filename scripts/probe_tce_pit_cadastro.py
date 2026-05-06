"""Probe TCE-PR PIT — descobrir como obter credencial de acesso a API."""

from __future__ import annotations

import re
import time

import httpx

# Pages onde geralmente esta a info de credenciamento
CANDIDATES = [
    "https://pit.tce.pr.gov.br/Cadastro",
    "https://pit.tce.pr.gov.br/Conta/Cadastro",
    "https://pit.tce.pr.gov.br/Conta/Login",
    "https://pit.tce.pr.gov.br/Account/Register",
    "https://pit.tce.pr.gov.br/swagger",
    "https://pit.tce.pr.gov.br/swagger/index.html",
    "https://pit.tce.pr.gov.br/swagger/v1/swagger.json",
    "https://pit.tce.pr.gov.br/api/swagger",
    "https://pit.tce.pr.gov.br/api/swagger/v1/swagger.json",
    # Documentacao no site do TCE
    "https://www.tce.pr.gov.br/sistemas-de-informacao/pit",
    "https://www.tce.pr.gov.br/conteudo/pit-plataforma-de-integracao-tecnologica",
    # Search no site (via Google work-around: site:tce.pr.gov.br PIT cadastro — nao posso aqui, vou listar paginas conhecidas)
    "https://www1.tce.pr.gov.br/multimidia/2024/3/pdf/00367562.pdf",  # eventualmente publicaram doc
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
        for url in CANDIDATES:
            print(f"\nGET {url}")
            t0 = time.monotonic()
            try:
                r = c.get(url)
            except Exception as e:
                print(f"  FAIL  {type(e).__name__}: {str(e)[:120]}")
                continue
            elapsed = time.monotonic() - t0
            ctype = r.headers.get("content-type", "")
            final = str(r.url)
            print(f"  HTTP {r.status_code} ({elapsed:.1f}s) ct={ctype[:40]} bytes={len(r.content)}")
            if final != url:
                print(f"    redirect -> {final}")
            if r.status_code != 200:
                print(f"    body: {r.text[:200]!r}")
                continue

            if "json" in ctype.lower():
                # OpenAPI/swagger?
                try:
                    data = r.json()
                    if "openapi" in data or "swagger" in data:
                        paths = list((data.get("paths") or {}).keys())
                        print(f"    SWAGGER paths ({len(paths)}):")
                        for p in paths[:30]:
                            print(f"      {p}")
                    else:
                        print(f"    keys: {sorted(data.keys())[:10]}")
                except Exception:
                    print(f"    body: {r.text[:300]!r}")
            else:
                body = r.text
                # Extrair texto util para encontrar info de cadastro
                snippet = re.sub(r"<[^>]+>", " ", body)
                snippet = re.sub(r"\s+", " ", snippet)[:1500]
                # Procura linhas que mencionam cadastro/token/credencial
                lower = snippet.lower()
                hot_phrases = [
                    "cadastro", "credencia", "token", "acesso", "registr",
                    "login", "autenti", "api"
                ]
                hits = [p for p in hot_phrases if p in lower]
                print(f"    palavras-chave encontradas: {hits}")
                if hits:
                    # Mostra primeiros 800 chars do snippet
                    print(f"    texto: {snippet[:800]!r}")
                else:
                    print(f"    texto (primeiro 200c): {snippet[:200]!r}")


if __name__ == "__main__":
    main()
