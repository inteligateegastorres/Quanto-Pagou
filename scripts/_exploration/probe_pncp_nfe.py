"""Probe focado: /v1/instrumentoscobranca/inclusao.

Valida que o endpoint retorna Notas Fiscais Eletronicas com itens
(valorUnitario PAGO, quantidade, descricao, NCM) atreladas a contratos.

Salva uma amostra como data/fixtures/pncp_nfe_sample.json para o
adapter usar como referencia/teste.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

BASE = "https://pncp.gov.br/api/consulta"


class _Retry(Exception):
    pass


@retry(
    retry=retry_if_exception_type(_Retry),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    stop=stop_after_attempt(8),
    reraise=True,
)
def get_with_retry(client: httpx.Client, path: str, params: dict) -> dict:
    try:
        r = client.get(BASE + path, params=params)
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        print(f"    retry: {type(e).__name__}: {e}")
        raise _Retry from e
    if r.status_code in (502, 503, 504, 408, 429, 500):
        print(f"    retry HTTP {r.status_code}")
        raise _Retry()
    if r.status_code != 200:
        return {"_status": r.status_code, "_body": r.text[:300]}
    try:
        return r.json()
    except Exception:
        return {"_nonjson": r.text[:200]}


def main() -> None:
    out_dir = Path("data/fixtures")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "pncp_nfe_sample.json"

    with httpx.Client(timeout=httpx.Timeout(120.0, connect=15.0)) as c:
        # Testa janelas curtas; instrumentos de cobranca ('NFe') tem volume
        # menor que contratos.
        windows = [
            ("20260401", "20260410"),
            ("20260201", "20260228"),
            ("20251201", "20251231"),
        ]
        for start, end in windows:
            print(f"\n=== Janela {start} -> {end} ===")
            t0 = time.monotonic()
            try:
                data = get_with_retry(
                    c,
                    "/v1/instrumentoscobranca/inclusao",
                    params={
                        "dataInicial": start,
                        "dataFinal": end,
                        "tipoInstrumentoCobranca": 1,  # NFe
                        "pagina": 1,
                        "tamanhoPagina": 50,
                    },
                )
            except Exception as e:
                print(f"  FAIL apos retries ({time.monotonic()-t0:.1f}s): {e}")
                continue
            elapsed = time.monotonic() - t0
            if "_status" in data:
                print(f"  HTTP {data['_status']} ({elapsed:.1f}s): {data['_body']!r}")
                continue
            print(f"  OK em {elapsed:.1f}s")
            print(f"  totalRegistros: {data.get('totalRegistros')}")
            print(f"  totalPaginas:   {data.get('totalPaginas')}")
            print(f"  paginasRestantes: {data.get('paginasRestantes')}")
            rows = data.get("data") or []
            print(f"  data[]: {len(rows)}")
            if not rows:
                continue

            # Salva amostra completa da primeira janela com dados.
            if not out_file.exists():
                out_file.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"  salvou amostra em {out_file} ({out_file.stat().st_size} bytes)")

            # Estatistica das NFes
            tem_itens = 0
            sem_itens = 0
            niveis: Counter[str] = Counter()
            n_itens_total = 0
            sample_item = None
            sample_full = None
            for row in rows:
                nfe = row.get("notaFiscalEletronica") or {}
                itens = nfe.get("itens") or []
                if itens:
                    tem_itens += 1
                    n_itens_total += len(itens)
                    if sample_item is None:
                        sample_item = itens[0]
                        sample_full = row
                else:
                    sem_itens += 1
                # Esfera nao vem direto; podemos inferir pelo primeiro digito do CNPJ?
                # Melhor: usar codigoOrgaoSuperior que tem padroes federais.
                codigo_sup = nfe.get("codigoOrgaoSuperiorDestinatario") or "?"
                niveis[codigo_sup[:2] if codigo_sup else "?"] += 1

            print(f"  NFes com itens: {tem_itens}/{len(rows)}  (sem: {sem_itens})")
            print(f"  Total de itens (todas NFes): {n_itens_total}")
            print(f"  Distribuicao por prefixo orgao superior: {dict(niveis.most_common(5))}")
            if sample_item:
                print("\n  AMOSTRA DE ITEM:")
                print(f"    {json.dumps(sample_item, ensure_ascii=False, indent=4)}")
            if sample_full:
                nfe = sample_full.get("notaFiscalEletronica") or {}
                contrato = sample_full.get("recuperarContratoDTO") or {}
                print("\n  Wrapper / contrato:")
                print(f"    chaveNFe : {sample_full.get('chaveNFe')}")
                print(f"    sequencial contrato: {sample_full.get('sequencialContrato')}")
                print(f"    contrato anocontrato/seq: {contrato.get('anoContrato')}/{contrato.get('sequencialContrato')}")
                print(f"    contrato numeroControlePNCP: {contrato.get('numeroControlePNCP')}")
                print(f"    contrato fornecedor: {contrato.get('niFornecedor')} - {contrato.get('nomeRazaoSocialFornecedor')}")
                print(f"    contrato orgao: {contrato.get('orgaoEntidade',{}).get('razaoSocial')}")
                print(f"    NFe nomeEmitente: {nfe.get('nomeEmitente')}")
                print(f"    NFe nomeOrgaoDestinatario: {nfe.get('nomeOrgaoDestinatario')}")
                print(f"    NFe valorNotaFiscal: {nfe.get('valorNotaFiscal')}")

            return  # primeira janela com sucesso ja basta para confirmar


if __name__ == "__main__":
    main()
