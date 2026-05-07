"""Probe CIA-TCE: ha cadastro publico ou e restrito a servidor/jurisdicionado?"""

from __future__ import annotations

import re
import time

import httpx

CANDIDATES = [
    # SSO entrypoint
    ("CIA-sso", "https://cia.tce.pr.gov.br/sso"),
    ("CIA-root", "https://cia.tce.pr.gov.br/"),
    # Cadastro
    ("CIA-novocadastro", "https://cia.tce.pr.gov.br/Cadastro/Novo"),
    ("CIA-novousuario", "https://cia.tce.pr.gov.br/NovoUsuario"),
    ("CIA-cidadao", "https://cia.tce.pr.gov.br/Cadastro/Cidadao"),
    ("CIA-publico", "https://cia.tce.pr.gov.br/PrimeiroAcesso"),
    # Doc oficial
    ("TCE-pit-doc", "https://www1.tce.pr.gov.br/conteudo/pit-plataforma-de-integracao-tecnologica/364"),
    ("TCE-busca-pit", "https://www.tce.pr.gov.br/buscar?q=PIT"),
    # E-Sfinge - sistema de envio publico do TCE
    ("ESFINGE", "https://servicos.tce.pr.gov.br/tcepr/Esfinge"),
    # Portal de servicos TCE
    ("TCE-servicos", "https://servicos.tce.pr.gov.br/"),
    # Pagina de "como usar" os dados abertos
    ("TCE-dados-busca", "https://www.tce.pr.gov.br/Pesquisa/?q=dados+abertos"),
]


def main() -> None:
    with httpx.Client(
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=True,
        headers={
            "Accept": "text/html, application/json",
            "User-Agent": "Mozilla/5.0 (compatible; QuantoPagouProbe/0.1)",
        },
    ) as c:
        for label, url in CANDIDATES:
            print(f"\n[{label}] GET {url}")
            t0 = time.monotonic()
            try:
                r = c.get(url)
            except Exception as e:
                print(f"  FAIL {type(e).__name__}: {str(e)[:120]}")
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
            body = r.text
            text = re.sub(r"<[^>]+>", " ", body)
            text = re.sub(r"\s+", " ", text)
            # Procurar palavras chave
            keywords = [
                "primeiro acesso", "primeiro-acesso", "novo usuario", "cadastro",
                "cidadao", "servidor", "jurisdicionado", "vinculo", "vínculo",
                "publico", "público", "credenciamento", "auto-cadastro",
                "auto cadastro", "ainda nao", "ainda não", "criar conta",
                "esqueci a senha", "esqueceu", "nao tenho",
            ]
            hits = [k for k in keywords if k in text.lower()]
            print(f"    hot words: {hits}")
            # Extrair pequena janela de cada match
            for hit in hits[:6]:
                idx = text.lower().find(hit)
                if idx > 0:
                    snippet = text[max(0, idx - 80) : idx + 200]
                    print(f"    [{hit!r}]: {snippet!r}")
            # Procurar menções a quem pode/nao pode acessar
            if "PIT" in text or "Plataforma de Integra" in text:
                idx = text.find("PIT")
                if idx > 0:
                    snippet = text[max(0, idx - 80) : idx + 400]
                    print(f"    PIT context: {snippet!r}")


if __name__ == "__main__":
    main()
