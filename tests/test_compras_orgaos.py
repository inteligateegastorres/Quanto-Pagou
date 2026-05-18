"""Unit tests para ingest.compras_orgaos.

Cobre mapeamento DTO -> linha de tabela e parse de timestamp. Não toca DB.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ingest.compras_orgaos import _coerce_orgao_row, _parse_movimento


def test_coerce_orgao_row_full_payload():
    """DTO completo do swagger vira linha com todas as colunas mapeadas."""
    item = {
        "codigoOrgao": 26298,
        "nomeOrgao": "FUNDO NACIONAL DE DESENVOLVIMENTO DA EDUCACAO",
        "nomeMnemonicoOrgao": "FNDE",
        "cnpjCpfOrgao": "00378257000181",
        "codigoOrgaoVinculado": 26000,
        "cnpjCpfOrgaoVinculado": "00394445000114",
        "nomeOrgaoVinculado": "MINISTERIO DA EDUCACAO",
        "codigoOrgaoSuperior": 26000,
        "cnpjCpfOrgaoSuperior": "00394445000114",
        "nomeOrgaoSuperior": "MINISTERIO DA EDUCACAO",
        "codigoTipoAdministracao": 1,
        "nomeTipoAdministracao": "Administracao Direta",
        "poder": "EXECUTIVO",
        "esfera": "FEDERAL",
        "usoSisg": True,
        "statusOrgao": True,
        "dataHoraMovimento": "2024-01-15T10:30:00",
    }
    row = _coerce_orgao_row(item)
    assert row["codigo_orgao"] == 26298
    assert row["nome"] == "FUNDO NACIONAL DE DESENVOLVIMENTO DA EDUCACAO"
    assert row["nome_mnemonico"] == "FNDE"
    assert row["cnpj"] == "00378257000181"
    assert row["codigo_orgao_vinculado"] == 26000
    assert row["nome_orgao_vinculado"] == "MINISTERIO DA EDUCACAO"
    assert row["codigo_orgao_superior"] == 26000
    assert row["nome_orgao_superior"] == "MINISTERIO DA EDUCACAO"
    assert row["codigo_tipo_administracao"] == 1
    assert row["nome_tipo_administracao"] == "Administracao Direta"
    assert row["poder"] == "EXECUTIVO"
    assert row["esfera"] == "FEDERAL"
    assert row["uso_sisg"] is True
    assert row["status_ativo"] is True
    assert row["data_movimento"] == datetime(2024, 1, 15, 10, 30, 0)


def test_coerce_orgao_row_minimal_payload():
    """Payload com apenas o mínimo viável (codigoOrgao + nomeOrgao)."""
    row = _coerce_orgao_row({"codigoOrgao": 1, "nomeOrgao": "X"})
    assert row["codigo_orgao"] == 1
    assert row["nome"] == "X"
    assert row["cnpj"] is None
    assert row["poder"] is None
    assert row["data_movimento"] is None
    # statusOrgao ausente => assume ativo (default True).
    assert row["status_ativo"] is True


def test_coerce_orgao_row_status_inativo():
    row = _coerce_orgao_row({"codigoOrgao": 1, "nomeOrgao": "X", "statusOrgao": False})
    assert row["status_ativo"] is False


def test_coerce_orgao_row_nome_vazio_normaliza_para_string_vazia():
    """nomeOrgao ausente vira "" (coluna NOT NULL)."""
    row = _coerce_orgao_row({"codigoOrgao": 1})
    assert row["nome"] == ""


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2024-01-15T10:30:00", datetime(2024, 1, 15, 10, 30, 0)),
        ("2024-01-15T10:30:00Z", datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)),
        ("2024-01-15T10:30:00+00:00", datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)),
        ("", None),
        (None, None),
        ("not-a-date", None),
        (12345, None),
    ],
)
def test_parse_movimento(raw, expected):
    assert _parse_movimento(raw) == expected
