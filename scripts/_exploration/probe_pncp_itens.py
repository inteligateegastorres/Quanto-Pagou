"""Probe PNCP - granularidade item-a-item.

Baseado no probe anterior, /v1/contratos e /v1/contratacoes/publicacao
funcionam. Agora a pergunta: PNCP expoe ITENS dessas contratacoes?
Sem isso, perdemos a comparacao item-a-item que e o nucleo do projeto.
"""

from __future__ import annotations

import json
import time

import httpx

BASE = "https://pncp.gov.br/api/consulta"

# numeroControlePncpCompra do sample anterior: "95595120000195-1-000009/2026"
# Decompomos: cnpj-1-sequencial/ano. Endpoints PNCP geralmente usam
# /orgaos/{cnpj}/compras/{ano}/{seq}/itens (padrao REST documentado).
CNPJ = "95595120000195"
ANO = "2026"
SEQ = "9"  # sequencialCompra=9

# Tambem vamos pegar 1 contrato real para ter um numeroControlePncpContrato.
def fetch_contract_id() -> tuple[str, dict] | None:
    """Pega 1 contrato real para extrair seus identificadores."""
    try:
        with httpx.Client(timeout=httpx.Timeout(60.0, connect=15.0)) as c:
            r = c.get(
                f"{BASE}/v1/contratos",
                params={
                    "dataInicial": "20260401",
                    "dataFinal": "20260430",
                    "pagina": 1,
                    "tamanhoPagina": 1,
                },
            )
        r.raise_for_status()
        data = r.json()
        if data.get("data"):
            sample = data["data"][0]
            print(f"[{sample.get('numeroControlePncpCompra')}]")
            print(f"  contrato: {sample.get('numeroContratoEmpenho')}")
            print(f"  cnpj orgao: {sample.get('orgaoEntidade',{}).get('cnpj')}")
            print(f"  ano: {sample.get('anoContrato')}")
            print(f"  seq: {sample.get('sequencialContrato')}")
            print(f"  esfera: {sample.get('orgaoEntidade',{}).get('esferaId')}")
            print(f"  todos os campos: {sorted(sample.keys())}")
            return sample.get("numeroControlePncpCompra"), sample
    except Exception as e:
        print(f"FAIL fetching contract: {e}")
    return None


def probe(label: str, path: str) -> bool:
    print(f"\n{label}: GET {path}")
    t0 = time.monotonic()
    try:
        with httpx.Client(timeout=httpx.Timeout(60.0, connect=15.0)) as c:
            r = c.get(BASE + path, headers={"Accept": "application/json"})
    except Exception as e:
        print(f"  FAIL ({time.monotonic()-t0:.1f}s) {type(e).__name__}: {e}")
        return False
    elapsed = time.monotonic() - t0
    print(f"  HTTP {r.status_code} ({elapsed:.1f}s) bytes={len(r.content)}")
    if r.status_code != 200:
        print(f"    body: {r.text[:300]!r}")
        return False
    try:
        data = r.json()
    except Exception:
        print(f"    nao-json: {r.text[:200]!r}")
        return False
    if isinstance(data, list):
        print(f"  LIST len={len(data)}")
        if data:
            print(f"    sample keys: {sorted(data[0].keys())[:20]}")
            print(f"    sample: {json.dumps(data[0], ensure_ascii=False)[:400]}")
    elif isinstance(data, dict):
        print(f"  DICT keys: {sorted(data.keys())[:15]}")
        for k in ("data", "content", "items", "resultado"):
            if k in data and isinstance(data[k], list):
                print(f"    {k}: len={len(data[k])}")
                if data[k]:
                    print(f"    sample: {json.dumps(data[k][0], ensure_ascii=False)[:400]}")
                break
    return True


def main() -> None:
    # Valores hardcoded do probe anterior (que respondeu em 0.8s).
    # numeroControlePncpCompra observado: "95595120000195-1-000009/2026"
    # MUNICIPIO DE DIAMANTE DO SUL/PR · sequencialCompra=9 · ano=2026
    cnpj_orgao = "95595120000195"
    ano_contrato = 2026
    seq_contrato = 9  # placeholder; pode nao haver contrato com seq=9, mas item endpoint testa estrutura

    print("\n" + "=" * 70)
    print("Probing endpoints de ITENS (varias convencoes)")
    print(f"Usando cnpj={cnpj_orgao} ano={ano_contrato} seq={seq_contrato}")
    print("=" * 70)

    # Convencoes documentadas comuns no PNCP:
    candidates = [
        # 1. Itens de contratacao via cnpj/ano/seq da COMPRA original
        ("itens da compra (v1)", f"/v1/orgaos/{CNPJ}/compras/{ANO}/{SEQ}/itens"),
        # 2. Itens do contrato via cnpj/ano/seq do contrato
        (
            "itens do contrato",
            f"/v1/orgaos/{cnpj_orgao}/contratos/{ano_contrato}/{seq_contrato}/itens",
        ),
        # 3. Variantes plurais
        ("itens v2", f"/v2/orgaos/{cnpj_orgao}/contratos/{ano_contrato}/{seq_contrato}/itens"),
        # 4. Endpoint global de itens
        ("itens globais (data range)", "/v1/itens-contratacao?dataInicial=20260401&dataFinal=20260430&pagina=1&tamanhoPagina=10"),
        # 5. Ata de registro de preco com itens
        ("atas com itens", "/v1/atas?dataInicial=20260401&dataFinal=20260430&pagina=1&tamanhoPagina=10"),
        # 6. Compra individual
        ("compra individual", f"/v1/orgaos/{CNPJ}/compras/{ANO}/{SEQ}"),
        # 7. Contrato individual
        (
            "contrato individual",
            f"/v1/orgaos/{cnpj_orgao}/contratos/{ano_contrato}/{seq_contrato}",
        ),
    ]
    for label, path in candidates:
        probe(label, path)


if __name__ == "__main__":
    main()
