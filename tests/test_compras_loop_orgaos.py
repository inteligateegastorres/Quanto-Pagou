"""Tests unitários para o loop por órgão (PLANO §19.11.b).

Cobre:
- _build_snapshot_id com codigo_orgao (sufixo) e sem (compatível com fixture).
- _iter_pages: shape dos params inclui codigoOrgao.
- _resolve_orgaos (CLI): 'all' delega ao loader, lista CSV parseia int, edge cases.

Não toca DB para os testes do parser CLI — o loader é mockado.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from ingest.compras import _build_snapshot_id, _iter_pages


def test_build_snapshot_id_sem_orgao_compatibilidade_fixture():
    """Sem codigo_orgao, o id mantém o formato legado (modo fixture)."""
    sid = _build_snapshot_id(date(2026, 1, 1), date(2026, 1, 7))
    assert sid.startswith("compras_gov_br_contratos-item_2026-01-01_2026-01-07_")
    assert "_orgao" not in sid


def test_build_snapshot_id_com_orgao_inclui_sufixo():
    """codigo_orgao vira sufixo _orgao{N} para evitar colisão entre órgãos."""
    sid = _build_snapshot_id(date(2026, 1, 1), date(2026, 1, 7), codigo_orgao=26298)
    assert sid.startswith("compras_gov_br_contratos-item_orgao26298_2026-01-01_2026-01-07_")


def test_iter_pages_inclui_codigo_orgao_nos_params():
    """_iter_pages passa codigoOrgao em cada chamada (breaking change upstream)."""
    captured_params: list[dict] = []

    def fake_get(endpoint, params=None):
        captured_params.append(dict(params))
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"resultado": [], "totalPaginas": 1}
        return resp

    client = MagicMock()
    client.get.side_effect = fake_get

    pages = list(
        _iter_pages(
            client,
            date(2026, 1, 1),
            date(2026, 1, 7),
            codigo_orgao=26298,
            page_size=500,
            max_pages=None,
        )
    )

    assert len(pages) == 1
    assert len(captured_params) == 1
    p = captured_params[0]
    assert p["codigoOrgao"] == 26298
    assert p["dataVigenciaInicialMin"] == "2026-01-01"
    assert p["dataVigenciaInicialMax"] == "2026-01-07"
    assert p["pagina"] == 1
    assert p["tamanhoPagina"] == 500


def test_iter_pages_para_no_total_paginas():
    """Loop para quando page >= totalPaginas."""
    payloads = [
        {"resultado": [{"x": 1}], "totalPaginas": 2},
        {"resultado": [{"x": 2}], "totalPaginas": 2},
        # nunca deve ser pedido — testamos isso pela contagem de chamadas
    ]
    call_count = {"n": 0}

    def fake_get(endpoint, params=None):
        idx = call_count["n"]
        call_count["n"] += 1
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = payloads[idx]
        return resp

    client = MagicMock()
    client.get.side_effect = fake_get

    pages = list(
        _iter_pages(
            client,
            date(2026, 1, 1),
            date(2026, 1, 7),
            codigo_orgao=1,
            page_size=500,
            max_pages=None,
        )
    )
    assert len(pages) == 2
    assert call_count["n"] == 2


# ---------- _resolve_orgaos (CLI helper) ----------


@pytest.fixture
def patch_loader():
    with patch("ingest.__main__.load_orgaos_ativos_federais") as m:
        yield m


def test_resolve_orgaos_all_delega_loader(patch_loader):
    from ingest.__main__ import _resolve_orgaos

    patch_loader.return_value = [10, 20, 30]
    result = _resolve_orgaos("all", limit=None)
    assert result == [10, 20, 30]
    patch_loader.assert_called_once_with(limit=None)


def test_resolve_orgaos_all_com_limit(patch_loader):
    from ingest.__main__ import _resolve_orgaos

    patch_loader.return_value = [10, 20]
    result = _resolve_orgaos("all", limit=2)
    assert result == [10, 20]
    patch_loader.assert_called_once_with(limit=2)


def test_resolve_orgaos_all_loader_vazio_levanta(patch_loader):
    from ingest.__main__ import _resolve_orgaos

    patch_loader.return_value = []
    with pytest.raises(RuntimeError, match="Nenhum orgao federal"):
        _resolve_orgaos("all", limit=None)


def test_resolve_orgaos_lista_csv():
    from ingest.__main__ import _resolve_orgaos

    assert _resolve_orgaos("26298,20000,1234", limit=None) == [26298, 20000, 1234]


def test_resolve_orgaos_csv_ignora_espacos_e_vazios():
    from ingest.__main__ import _resolve_orgaos

    assert _resolve_orgaos("  26298 , 20000 ,, ", limit=None) == [26298, 20000]


def test_resolve_orgaos_csv_invalido():
    from ingest.__main__ import _resolve_orgaos

    with pytest.raises(ValueError, match="--orgaos invalido"):
        _resolve_orgaos("26298,abc", limit=None)


def test_resolve_orgaos_csv_vazio():
    from ingest.__main__ import _resolve_orgaos

    with pytest.raises(ValueError, match="não pode ser vazio"):
        _resolve_orgaos(",,, ", limit=None)


def test_resolve_orgaos_limit_so_com_all():
    """--orgaos-limit não faz sentido com lista explícita; rejeitamos."""
    from ingest.__main__ import _resolve_orgaos

    with pytest.raises(ValueError, match="só é válido com --orgaos all"):
        _resolve_orgaos("26298", limit=3)
