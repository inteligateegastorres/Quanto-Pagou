"""Gera data/fixtures/compras_sample.jsonl — payload sintetico para o pipeline.

Util quando a API Compras.gov.br /modulo-contratos/* esta com falha de backend
(ex: 'Could not open JPA EntityManager for transaction'). Permite exercitar o
pipeline downstream (raw.compras -> marts) sem dependencia externa.

NAO usar em producao — todos os codigoItem e CNPJs sao sinteticos.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

OUT = Path("data/fixtures/compras_sample.jsonl")

# (catmat_id, descricao_canonica, preco_mediano_referencia, faixa_pct)
CATEGORIAS = [
    (280144, "CANETA ESFEROGRAFICA AZUL CORPO TRANSPARENTE", 1.20, 0.40),
    (410, "ARROZ TIPO 1 LONGO FINO PACOTE 5KG", 28.50, 0.55),
    (1825, "CAFE TORRADO MOIDO PACOTE 500G", 22.00, 0.35),
    (39, "PAPEL SULFITE A4 75G RESMA 500 FOLHAS", 32.00, 0.30),
    (8543, "OLEO DIESEL S10 LITRO", 6.30, 0.20),
]

ORGAOS = [
    ("26000", "MINISTERIO DA EDUCACAO", "F", "DF"),
    ("36000", "MINISTERIO DA SAUDE", "F", "DF"),
    ("52000", "MINISTERIO DA DEFESA", "F", "DF"),
    ("44000", "MINISTERIO DA AGRICULTURA", "F", "DF"),
    ("38000", "MINISTERIO DA CIDADANIA", "F", "DF"),
    ("30000", "MINISTERIO DA JUSTICA", "F", "DF"),
    ("25000", "MINISTERIO DA FAZENDA", "F", "DF"),
]

FORNECEDORES = [
    ("12345678000101", "SUPRIMENTOS BRASIL LTDA"),
    ("23456789000102", "DISTRIBUIDORA NACIONAL SA"),
    ("34567890000103", "COMERCIAL ATACADO ME"),
    ("45678901000104", "PAPELARIA CENTRAL LTDA"),
    ("56789012000105", "ALIMENTOS DO SUL LTDA"),
    ("67890123000106", "POSTO DE COMBUSTIVEIS REGIONAL"),
]

MODALIDADES = ["Pregao Eletronico", "Dispensa de Licitacao", "Inexigibilidade", "Concorrencia"]


def gen_items(rng: random.Random, n: int = 30) -> list[dict]:
    items = []
    for i in range(n):
        catmat, descricao, preco_ref, faixa = rng.choice(CATEGORIAS)
        orgao = rng.choice(ORGAOS)
        forn = rng.choice(FORNECEDORES)
        modalidade = rng.choices(MODALIDADES, weights=[0.6, 0.25, 0.05, 0.10])[0]

        # ruido de preco em torno da referencia, para mediana ter dispersao real
        preco_unit = round(preco_ref * (1 + rng.uniform(-faixa, faixa)), 2)
        # alguns outliers (5% acima de 2x)
        if rng.random() < 0.05:
            preco_unit = round(preco_ref * rng.uniform(2.0, 3.5), 2)

        qtd = rng.choice([10, 50, 100, 500, 1000, 5000])
        total = round(preco_unit * qtd, 2)
        contrato = f"{2026000 + i}/2026"

        items.append({
            "codigoOrgao": orgao[0],
            "nomeOrgao": orgao[1],
            "codigoUnidadeGestora": f"{orgao[0][:3]}001",
            "codigoUnidadeGestoraOrigemContrato": f"{orgao[0][:3]}001",
            "codigoUnidadeRealizadoraCompra": f"{orgao[0][:3]}001",
            "codigoModalidadeCompra": "06",
            "numeroContrato": contrato,
            "niFornecedor": forn[0],
            "nomeRazaoSocialFornecedor": forn[1],
            "processo": f"PROC-{i:05d}/2026",
            "dataVigenciaInicial": "2026-04-15",
            "dataVigenciaFinal": "2027-04-15",
            "valorGlobal": total,
            "tipoItem": "M",
            "codigoItem": catmat,
            "descricaoIitem": descricao,
            "quantidadeItem": qtd,
            "valorUnitarioItem": preco_unit,
            "valorTotalItem": total,
            "dataHoraInclusao": "2026-04-15T10:00:00",
            "numeroControlePncpContrato": f"{orgao[0]}{i:05d}-1-2026",
            "idCompra": f"CP-{i:05d}-2026",
            "dataHoraExclusaoContrato": None,
            "contratoExcluido": False,
            "nomeUnidadeGestora": orgao[1] + " - UG",
            "nomeUnidadeGestoraOrigemContrato": orgao[1] + " - UG",
            "nomeUnidadeRealizadoraCompra": orgao[1] + " - UR",
            "nomeModalidadeCompra": modalidade,
            "numeroCompra": f"{i:05d}/2026",
            "dataHoraExclusaoItem": None,
            "contratoItemExcluido": False,
            "numeroItem": str(i + 1),
            "esfera": orgao[2],
            "poder": "E",  # Executivo
            "numeroControlePncpCompra": f"{orgao[0]}{i:05d}-2-2026",
        })
    return items


def main() -> None:
    rng = random.Random(42)  # determinístico
    items = gen_items(rng, n=30)
    page = {
        "resultado": items,
        "totalRegistros": len(items),
        "totalPaginas": 1,
        "paginasRestantes": 0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(page, ensure_ascii=False))
        fh.write("\n")
    print(f"Wrote {OUT} ({len(items)} itens)")


if __name__ == "__main__":
    main()
