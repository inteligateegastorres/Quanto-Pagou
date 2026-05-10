"""Probe focado: estrutura do endpoint de itens do PNCP.

Retry agressivo (10x, backoff ate 90s, timeout 180s) — endpoint existe (deu
timeout, nao 404), entao com persistencia e tempo deve responder.

Pega 1 contratacao real do listing de /contratacoes/publicacao,
extrai cnpj/ano/seq, e bate em /v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens.
"""

from __future__ import annotations

import json
import time

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

BASE = "https://pncp.gov.br/api/consulta"


class _Retry(Exception):
    pass


@retry(
    retry=retry_if_exception_type(_Retry),
    wait=wait_exponential(multiplier=2, min=4, max=90),
    stop=stop_after_attempt(10),
    reraise=True,
)
def get_with_retry(client: httpx.Client, path: str, params: dict | None = None) -> dict:
    try:
        r = client.get(BASE + path, params=params)
    except httpx.TimeoutException as e:
        print(f"    timeout retry: {e}")
        raise _Retry from e
    except httpx.HTTPError as e:
        print(f"    http retry: {e}")
        raise _Retry from e
    if r.status_code in (502, 503, 504, 408, 429, 500):
        print(f"    {r.status_code} retry")
        raise _Retry()
    if r.status_code == 404:
        return {"_404": True, "_body": r.text[:300]}
    if r.status_code != 200:
        print(f"    HTTP {r.status_code}: {r.text[:200]}")
        return {"_status": r.status_code, "_body": r.text[:200]}
    try:
        return r.json()
    except Exception:
        return {"_nonjson": r.text[:200]}


def main() -> None:
    with httpx.Client(timeout=httpx.Timeout(180.0, connect=20.0)) as c:
        print("=" * 70)
        print("Step 1: pega 1 contratacao pra extrair cnpj/ano/seq")
        print("=" * 70)
        listing = get_with_retry(
            c,
            "/v1/contratacoes/publicacao",
            params={
                "dataInicial": "20260301",
                "dataFinal": "20260330",
                "codigoModalidadeContratacao": 6,  # pregao eletronico
                "pagina": 1,
                "tamanhoPagina": 10,
            },
        )
        if "_404" in listing or "_status" in listing or "_nonjson" in listing:
            print(f"FAIL listing: {listing}")
            return
        rows = listing.get("data") or []
        if not rows:
            print("Sem contratacoes na janela.")
            return
        print(f"Achei {len(rows)} contratacoes; tentando itens da primeira que tiver dados completos...")

        for idx, sample in enumerate(rows):
            cnpj = sample.get("orgaoEntidade", {}).get("cnpj")
            ano = sample.get("anoCompra")
            seq = sample.get("sequencialCompra")
            modalidade = sample.get("modalidadeNome")
            objeto = (sample.get("objetoCompra") or "")[:80]
            if not (cnpj and ano and seq):
                continue
            print(f"\nTentativa {idx+1}: cnpj={cnpj} ano={ano} seq={seq}")
            print(f"  modalidade: {modalidade}")
            print(f"  objeto    : {objeto!r}")

            print("\n  GET /v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens")
            t0 = time.monotonic()
            try:
                items = get_with_retry(
                    c, f"/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens"
                )
            except Exception as e:
                print(f"  FAIL apos retries ({time.monotonic()-t0:.1f}s): {e}")
                continue
            elapsed = time.monotonic() - t0
            print(f"  OK em {elapsed:.1f}s")
            if "_404" in items:
                print(f"    404: {items['_body']!r}")
                continue
            print(f"  type: {type(items).__name__}")
            if isinstance(items, list):
                print(f"  array len={len(items)}")
                if items:
                    print(f"  sample keys: {sorted(items[0].keys())}")
                    print(
                        f"  sample (500c): {json.dumps(items[0], ensure_ascii=False)[:500]}"
                    )
                    if len(items) > 1:
                        print(
                            f"  sample 2 (300c): {json.dumps(items[1], ensure_ascii=False)[:300]}"
                        )
                    return  # achou — pode parar
            elif isinstance(items, dict):
                print(f"  dict keys: {sorted(items.keys())[:15]}")
                print(f"  body (300c): {json.dumps(items, ensure_ascii=False)[:300]}")
                if not items.get("_404"):
                    return


if __name__ == "__main__":
    main()
