"""Probe focado: /Dados/DadosConsulta/Consolidado do PIT TCE-PR.

Sugerido pelo usuario. Estrategia:
1. GET direto e ver se redireciona para SSO ou se abre publica.
2. Se abre publica como HTML, parsear o JS/HTML pra descobrir
   endpoints AJAX que ela usa (fetch/axios/jquery).
3. Listar todos URLs internos que aparecem na pagina.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import httpx

URL = "https://pit.tce.pr.gov.br/Dados/DadosConsulta/Consolidado"
BASE = "https://pit.tce.pr.gov.br"

# User-Agent de browser real para passar por possiveis filtros
HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
}


def get(c: httpx.Client, url: str, **params: object) -> httpx.Response | None:
    t0 = time.monotonic()
    try:
        r = c.get(url, params=params, headers=HEADERS)
    except Exception as e:
        print(f"  FAIL {type(e).__name__}: {str(e)[:120]}")
        return None
    elapsed = time.monotonic() - t0
    ctype = r.headers.get("content-type", "")
    print(f"  HTTP {r.status_code} ({elapsed:.1f}s) ct={ctype[:40]} bytes={len(r.content)}")
    if str(r.url) != url:
        print(f"    redirect -> {r.url}")
    return r


def main() -> None:
    out_dir = Path("data/fixtures")
    out_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=httpx.Timeout(45.0, connect=15.0), follow_redirects=True) as c:
        print(f"\n=== GET {URL}")
        r = get(c, URL)
        if not r or r.status_code != 200:
            return

        body = r.text
        # Salva HTML completo para analise offline
        out_file = out_dir / "pit_consolidado_page.html"
        out_file.write_text(body, encoding="utf-8")
        print(f"  HTML salvo em {out_file}  ({out_file.stat().st_size} bytes)")

        # 1. URLs absolutas dentro do dominio
        urls = re.findall(r'https?://pit\.tce\.pr\.gov\.br[/a-zA-Z0-9_/?=&%.-]*', body)
        urls += re.findall(r'href="(/[^"]+)"', body)
        urls += re.findall(r"action=\"(/[^\"]+)\"", body)
        urls = list(dict.fromkeys(urls))[:30]
        print(f"\n  URLs internas no HTML ({len(urls)} unique):")
        for u in urls:
            print(f"    {u}")

        # 2. Referencias a fetch/ajax/url em JS
        ajax_patterns = [
            r"\$\.(?:get|post|ajax)\s*\(\s*['\"]([^'\"]+)['\"]",
            r"fetch\s*\(\s*['\"]([^'\"]+)['\"]",
            r"url\s*:\s*['\"]([^'\"]{5,200})['\"]",
            r"baseUrl\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"endpoint\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"action\s*=\s*['\"](/[^'\"]+)['\"]",
        ]
        ajax_hits = []
        for pat in ajax_patterns:
            ajax_hits.extend(re.findall(pat, body, re.IGNORECASE))
        ajax_hits = list(dict.fromkeys(ajax_hits))
        if ajax_hits:
            print(f"\n  Referencias AJAX/fetch ({len(ajax_hits)}):")
            for hit in ajax_hits[:30]:
                print(f"    {hit}")

        # 3. Existe arquivo .js que carrega o behavior?
        js_files = re.findall(r'src="([^"]+\.js[^"]*)"', body)
        js_files = list(dict.fromkeys(js_files))
        if js_files:
            print(f"\n  Arquivos JS referenciados ({len(js_files)}):")
            for js in js_files[:10]:
                print(f"    {js}")

        # 4. IDs de elementos (input, select) que podem indicar filtros
        ids = re.findall(r'id="([^"]+)"', body)
        ids = list(dict.fromkeys(ids))
        # filtra ids "interessantes"
        interesting = [i for i in ids if any(
            k in i.lower() for k in
            ("ano", "exercicio", "orgao", "municipio", "tipo", "modalidade", "valor", "cnpj", "filtro")
        )]
        if interesting:
            print(f"\n  IDs de filtro detectados ({len(interesting)}):")
            for i in interesting[:20]:
                print(f"    {i}")

        # 5. Mostra trecho do <body> que parece ter filtros/select
        body_only = re.search(r'<body[^>]*>(.*)</body>', body, re.DOTALL | re.IGNORECASE)
        if body_only:
            text = re.sub(r"<script.*?</script>", " ", body_only.group(1), flags=re.DOTALL)
            text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            print("\n  Texto visivel da pagina (primeiros 1500 chars):")
            print(f"    {text[:1500]!r}")

        # Tenta seguir cada JS interno baixando-o pra ver chamadas
        for js in js_files[:5]:
            js_url = js if js.startswith("http") else BASE + js
            print(f"\n=== {js_url}")
            jr = get(c, js_url)
            if jr and jr.status_code == 200 and len(jr.text) < 200000:
                jbody = jr.text
                hits = []
                for pat in ajax_patterns:
                    hits.extend(re.findall(pat, jbody, re.IGNORECASE))
                hits = list(dict.fromkeys(hits))[:20]
                if hits:
                    print(f"  fetch/ajax ({len(hits)}):")
                    for h in hits:
                        print(f"    {h}")


if __name__ == "__main__":
    main()
