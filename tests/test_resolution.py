"""Regression tests para resolution.py.

Cobre os bugs ja encontrados manualmente:
- S10 LITRO nao deve capturar "10 LITRO".
- 75G/M2 (gramatura de papel) nao deve virar 0.075 kg.
- Patterns de papel/resma devem casar antes dos de massa.
"""

from __future__ import annotations

import pytest

from analytics.resolution import (
    canonicalize,
    load_golden_set,
    load_unit_conversion,
    parse_unit,
    resolve_cluster,
)


@pytest.fixture(scope="module")
def conv() -> dict:
    return load_unit_conversion()


@pytest.fixture(scope="module")
def golden():
    by_catmat, _ = load_golden_set()
    return by_catmat


# ---------- parse_unit: edge cases que motivaram este arquivo ----------


@pytest.mark.parametrize(
    "descricao,categoria,unidade_base,qtd_em_base",
    [
        # Diesel: "S10" nao deve ser capturado como "10 L".
        ("OLEO DIESEL S10 LITRO", "combustivel", "litro", 1.0),
        ("OLEO DIESEL S-10", "combustivel", "litro", 1.0),
        ("DIESEL S10 LT", "combustivel", "litro", 1.0),
        ("OLEO DIESEL S10 RODOVIARIO L", "combustivel", "litro", 1.0),
        # Papel: "75G/M2" nao deve virar 0.075 kg; resma deve casar.
        ("PAPEL SULFITE A4 75G RESMA 500 FOLHAS", "escritorio", "resma_500", 1.0),
        ("PAPEL A4 75G/M2 RESMA C/ 500 FLS", "escritorio", "resma_500", 1.0),
        ("PAPEL SULFITE BRANCO A4 75G CAIXA C 10 RESMAS", "escritorio", "resma_500", 10.0),
        ("PAPEL A4 SULFITE 75G/M2 EMBALAGEM 500 FOLHAS", "escritorio", "resma_500", 1.0),
        ("PAPEL SULFITE BRANCO 75G FORMATO A4 RESMA", "escritorio", "resma_500", 1.0),
        # Massa: KG/G isolados e com embalagem.
        ("ARROZ TIPO 1 LONGO FINO PACOTE 5KG", "alimento_seco", "kg", 5.0),
        ("ARROZ BRANCO TIPO 1 LONGO FINO 1KG", "alimento_seco", "kg", 1.0),
        ("ARROZ TIPO 1 PACOTE COM 5 QUILOS", "alimento_seco", "kg", 5.0),
        ("ARROZ TIPO 1 BRANCO POLIDO FARDO 30KG", "alimento_seco", "kg", 30.0),
        ("CAFE TORRADO MOIDO PACOTE 500G", "alimento_seco", "kg", 0.5),
        ("CAFE TORRADO MOIDO 250G", "alimento_seco", "kg", 0.25),
        # Caneta: caixa com N + unidade solo.
        ("CANETA ESFEROGRAFICA AZUL CX C/ 50 UNIDADES", "escritorio", "unidade", 50.0),
        ("CANETA ESFEROGRAFICA AZUL CAIXA COM 50", "escritorio", "unidade", 50.0),
        ("CANETA ESFEROGRAFICA AZUL UNIDADE", "escritorio", "unidade", 1.0),
        # Default por categoria quando descricao nao tem unidade.
        ("CANETA ESFEROGRAFICA AZUL CORPO TRANSPARENTE", "escritorio", "unidade", 1.0),
    ],
)
def test_parse_unit_golden(descricao, categoria, unidade_base, qtd_em_base, conv):
    m = parse_unit(descricao, categoria, conv)
    assert m is not None, f"sem match para {descricao!r}"
    assert m.unidade_base == unidade_base, (
        f"{descricao!r}: esperado base {unidade_base}, veio {m.unidade_base}"
    )
    assert m.qtd_em_unidade_base == pytest.approx(qtd_em_base), (
        f"{descricao!r}: esperado qtd {qtd_em_base}, veio {m.qtd_em_unidade_base}"
    )


def test_parse_unit_sem_default_quando_nada_bate(conv):
    """Categoria 'desconhecida' + descricao sem unidade -> None (vai para quarentena)."""
    m = parse_unit("XYZ ABC PRODUTO TESTE", "desconhecida", conv)
    assert m is None


def test_parse_unit_marca_inferido_em_default(conv):
    """Default deve marcar fator_inferido=True para penalizar confianca."""
    m = parse_unit("CANETA ESFEROGRAFICA AZUL CORPO TRANSPARENTE", "escritorio", conv)
    assert m is not None
    assert m.fator_inferido is True


# ---------- resolve_cluster ----------


def test_resolve_cluster_golden(golden):
    """CATMAT no golden -> cluster do golden, confianca 1.00."""
    res = resolve_cluster("410", golden)
    assert res.cluster_id == "arroz_tipo_1"
    assert res.cluster_version == "v1"
    assert res.metodo_resolucao == "tier1_catmat_golden"
    assert res.confianca_resolucao == 1.00


def test_resolve_cluster_sintetico(golden):
    """CATMAT fora do golden -> cluster sintetico, confianca 0.85."""
    res = resolve_cluster("99999999", golden)
    assert res.cluster_id == "catmat_99999999"
    assert res.cluster_version == "v1"
    assert res.metodo_resolucao == "tier1_catmat_sintetico"
    assert res.confianca_resolucao == 0.85
    assert res.categoria == "desconhecida"


def test_resolve_cluster_sem_catmat(golden):
    """Sem CATMAT -> sem_cluster, confianca 0."""
    res = resolve_cluster(None, golden)
    assert res.cluster_id is None
    assert res.metodo_resolucao == "sem_cluster"
    assert res.confianca_resolucao == 0.0


# ---------- canonicalize: smoke ----------


def test_canonicalize_arroz_federal(golden, conv):
    """Linha tipica da fixture: arroz 5kg, esfera federal -> tudo preenchido, sem quarentena."""
    raw = {
        "id": 123,
        "catmat_id": "410",
        "descricao": "ARROZ TIPO 1 LONGO FINO PACOTE 5KG",
        "valor_unitario": 28.50,
        "raw_payload": {"esfera": "F"},
    }
    cr = canonicalize(raw, golden, conv)
    assert cr.cluster_id == "arroz_tipo_1"
    assert cr.unidade_base == "kg"
    assert cr.fator_conversao == 5.0
    assert cr.valor_unitario_normalizado == pytest.approx(5.70)
    assert cr.ente_nivel == "federal"
    assert cr.uf == "DF"
    assert cr.porte == "federal_central"
    assert cr.em_quarentena is False
    assert cr.confianca_resolucao == 1.00


def test_canonicalize_diesel_nao_corrompe_S10(golden, conv):
    """Regression: 'S10 LITRO' deve cair em default 1L, nao em '10 L'."""
    raw = {
        "id": 124,
        "catmat_id": "8543",
        "descricao": "OLEO DIESEL S10 LITRO",
        "valor_unitario": 6.30,
        "raw_payload": {"esfera": "F"},
    }
    cr = canonicalize(raw, golden, conv)
    assert cr.unidade_base == "litro"
    assert cr.fator_conversao == 1.0
    assert cr.valor_unitario_normalizado == pytest.approx(6.30)


def test_canonicalize_papel_nao_corrompe_gramatura(golden, conv):
    """Regression: '75G/M2' nao deve ser interpretado como 0.075 kg."""
    raw = {
        "id": 125,
        "catmat_id": "39",
        "descricao": "PAPEL A4 SULFITE 75G/M2 EMBALAGEM 500 FOLHAS",
        "valor_unitario": 32.00,
        "raw_payload": {"esfera": "F"},
    }
    cr = canonicalize(raw, golden, conv)
    assert cr.unidade_base == "resma_500"
    assert cr.fator_conversao == 1.0
    assert cr.valor_unitario_normalizado == pytest.approx(32.00)


def test_canonicalize_sem_catmat_vai_para_quarentena(golden, conv):
    raw = {
        "id": 126,
        "catmat_id": None,
        "descricao": "ITEM QUALQUER",
        "valor_unitario": 10.00,
        "raw_payload": {"esfera": "F"},
    }
    cr = canonicalize(raw, golden, conv)
    assert cr.em_quarentena is True
    assert "sem_catmat" in (cr.motivo_quarentena or "")
