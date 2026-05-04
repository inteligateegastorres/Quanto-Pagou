"""Spider Compras.gov.br — endpoint /modulo-contratos/2_consultarContratosItem.

Ingere itens de contratos federais por janela de datas.
Persiste payload bruto em snapshot imutável (JSONL.gz) + linhas em raw.compras.

Progressive correctness: simples e suficiente. Sofisticar quando houver volume.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
import psycopg
from psycopg.types.json import Jsonb
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ingest.config import settings

logger = logging.getLogger(__name__)

ENDPOINT = "/modulo-contratos/2_consultarContratosItem"
SOURCE = "compras_gov_br/contratos-item"
DEFAULT_PAGE_SIZE = 500
HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


@dataclass(slots=True)
class IngestResult:
    snapshot_id: str
    snapshot_path: Path
    pages_fetched: int
    items_total: int
    items_inserted: int
    hash_sha256: str
    period_start: date
    period_end: date


def _build_snapshot_id(period_start: date, period_end: date) -> str:
    ts = int(time.time())
    return f"compras_gov_br_contratos-item_{period_start.isoformat()}_{period_end.isoformat()}_{ts}"


def _snapshot_path(snapshot_id: str) -> Path:
    base = settings.snapshots_dir / "compras_gov_br"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{snapshot_id}.jsonl.gz"


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, str):
        # API devolve "YYYY-MM-DD" ou ISO completo.
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _coerce_item_row(item: dict[str, Any]) -> dict[str, Any]:
    """Mapeia um VwFtContratoItemDTO para colunas de raw.compras."""
    tipo_item = item.get("tipoItem")  # "M" material | "S" serviço
    codigo_item = item.get("codigoItem")
    catmat_id = str(codigo_item) if tipo_item == "M" and codigo_item is not None else None
    catser_id = str(codigo_item) if tipo_item == "S" and codigo_item is not None else None

    # Compor source_id estável a partir de chave natural do contrato + item.
    parts = [
        str(item.get("numeroControlePncpContrato") or item.get("numeroContrato") or ""),
        str(item.get("numeroItem") or codigo_item or ""),
    ]
    source_id = "|".join(p for p in parts if p) or None

    return {
        "source": SOURCE,
        "source_id": source_id,
        "source_url": None,  # API não devolve URL canônica por item
        "contract_date": _parse_date(item.get("dataVigenciaInicial")),
        "orgao_codigo": item.get("codigoOrgao"),
        "orgao_nome": item.get("nomeOrgao"),
        "fornecedor_cnpj": item.get("niFornecedor"),
        "fornecedor_nome": item.get("nomeRazaoSocialFornecedor"),
        "catmat_id": catmat_id,
        "catser_id": catser_id,
        "descricao": item.get("descricaoIitem") or "",  # typo no schema da API
        "quantidade": item.get("quantidadeItem"),
        "unidade": None,  # endpoint não expõe; resolver via catálogo de material
        "valor_unitario": item.get("valorUnitarioItem"),
        "valor_total": item.get("valorTotalItem"),
        "modalidade": item.get("nomeModalidadeCompra"),
    }


class _RetryableHTTP(Exception):
    """5xx, timeout, connection, ou erros JPA transitórios do backend Compras."""


# Fragmentos de mensagem que indicam falha transitória no backend deles.
_TRANSIENT_BODY_FRAGMENTS = (
    "EntityManager",
    "JDBCConnectionException",
    "Could not open",
    "Communications link failure",
)


@retry(
    retry=retry_if_exception_type(_RetryableHTTP),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _get_page(client: httpx.Client, params: dict[str, Any]) -> dict[str, Any]:
    try:
        resp = client.get(ENDPOINT, params=params)
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
        raise _RetryableHTTP(str(exc)) from exc
    if 500 <= resp.status_code < 600:
        raise _RetryableHTTP(f"{resp.status_code} {resp.reason_phrase}")
    if resp.status_code == 400 and any(f in resp.text for f in _TRANSIENT_BODY_FRAGMENTS):
        # Backend Compras cospe 400 com mensagem JPA quando o pool de conexões cai.
        # Tratamos como transitório e damos retry com backoff.
        raise _RetryableHTTP(f"transient backend: {resp.text[:200]}")
    if resp.status_code >= 400:
        raise httpx.HTTPStatusError(
            f"{resp.status_code} {resp.reason_phrase}: {resp.text[:300]}",
            request=resp.request,
            response=resp,
        )
    return resp.json()


def _iter_pages(
    client: httpx.Client,
    period_start: date,
    period_end: date,
    page_size: int,
    max_pages: int | None,
) -> Iterator[dict[str, Any]]:
    page = 1
    while True:
        params = {
            "dataVigenciaInicialMin": period_start.isoformat(),
            "dataVigenciaInicialMax": period_end.isoformat(),
            "pagina": page,
            "tamanhoPagina": page_size,
        }
        payload = _get_page(client, params)
        yield payload

        total_paginas = int(payload.get("totalPaginas") or 0)
        if total_paginas == 0 or page >= total_paginas:
            return
        if max_pages is not None and page >= max_pages:
            logger.info("Atingido max_pages=%s; parando.", max_pages)
            return
        page += 1


_INSERT_COMPRAS_SQL = """
INSERT INTO raw.compras (
    snapshot_id, source, source_id, source_url, contract_date,
    orgao_codigo, orgao_nome, fornecedor_cnpj, fornecedor_nome,
    catmat_id, catser_id, descricao, quantidade, unidade,
    valor_unitario, valor_total, modalidade, raw_payload
) VALUES (
    %(snapshot_id)s, %(source)s, %(source_id)s, %(source_url)s, %(contract_date)s,
    %(orgao_codigo)s, %(orgao_nome)s, %(fornecedor_cnpj)s, %(fornecedor_nome)s,
    %(catmat_id)s, %(catser_id)s, %(descricao)s, %(quantidade)s, %(unidade)s,
    %(valor_unitario)s, %(valor_total)s, %(modalidade)s, %(raw_payload)s
)
"""


def _insert_items_batch(
    conn: psycopg.Connection,
    snapshot_id: str,
    items: list[dict[str, Any]],
) -> int:
    rows = []
    for item in items:
        row = _coerce_item_row(item)
        row["snapshot_id"] = snapshot_id
        row["raw_payload"] = Jsonb(item)
        rows.append(row)
    with conn.cursor() as cur:
        cur.executemany(_INSERT_COMPRAS_SQL, rows)
    return len(rows)


def _persist_pages(
    pages: Iterator[dict[str, Any]],
    *,
    period_start: date,
    period_end: date,
    snapshot_id_override: str | None = None,
    source: str = SOURCE,
    on_progress: Any = None,
) -> IngestResult:
    """Persiste um stream de paginas (snapshot + raw.compras). Reusavel por fixtures."""
    snapshot_id = snapshot_id_override or _build_snapshot_id(period_start, period_end)
    snap_path = _snapshot_path(snapshot_id)
    hasher = hashlib.sha256()
    pages_fetched = 0
    items_total = 0
    items_inserted = 0
    started = datetime.now()

    with (
        psycopg.connect(settings.database_url) as conn,
        gzip.open(snap_path, "wt", encoding="utf-8", compresslevel=6) as snap_fh,
    ):
        # raw.snapshots primeiro (FK em raw.compras). Atualizamos records_count e hash no fim.
        conn.execute(
            """
            INSERT INTO raw.snapshots
                (id, source, period_start, period_end, records_count, hash_sha256)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (snapshot_id, source, period_start, period_end, 0, ""),
        )
        conn.commit()

        try:
            for payload in pages:
                pages_fetched += 1
                line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                hasher.update(line.encode("utf-8"))
                snap_fh.write(line)
                snap_fh.write("\n")

                items = payload.get("resultado") or []
                items_total += len(items)
                if items:
                    items_inserted += _insert_items_batch(conn, snapshot_id, items)
                    conn.commit()

                if on_progress:
                    on_progress(
                        page=pages_fetched,
                        total_pages=int(payload.get("totalPaginas") or 0),
                        items_so_far=items_total,
                    )
        except Exception:
            conn.rollback()
            raise

        hash_hex = hasher.hexdigest()
        conn.execute(
            "UPDATE raw.snapshots SET records_count = %s, hash_sha256 = %s WHERE id = %s",
            (items_inserted, hash_hex, snapshot_id),
        )
        conn.commit()

    elapsed = (datetime.now() - started).total_seconds()
    logger.info(
        "Persistencia concluida em %.1fs: %d paginas, %d itens, snapshot=%s",
        elapsed,
        pages_fetched,
        items_inserted,
        snap_path,
    )

    return IngestResult(
        snapshot_id=snapshot_id,
        snapshot_path=snap_path,
        pages_fetched=pages_fetched,
        items_total=items_total,
        items_inserted=items_inserted,
        hash_sha256=hash_hex,
        period_start=period_start,
        period_end=period_end,
    )


def ingest(
    period_start: date,
    period_end: date,
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int | None = None,
    on_progress: Any = None,
) -> IngestResult:
    """Executa ingestao de uma janela via API Compras.gov.br."""
    if period_start > period_end:
        raise ValueError("period_start > period_end")

    headers = {"Accept": "application/json", "User-Agent": "quantopagou-ingest/0.0.1"}
    base = settings.compras_api_base.rstrip("/")

    logger.info("Ingest API iniciado: %s -> %s", period_start, period_end)

    with httpx.Client(base_url=base, headers=headers, timeout=HTTP_TIMEOUT) as client:
        pages_iter = _iter_pages(client, period_start, period_end, page_size, max_pages)
        return _persist_pages(
            pages_iter,
            period_start=period_start,
            period_end=period_end,
            on_progress=on_progress,
        )


def ingest_fixture(
    fixture_path: Path,
    *,
    period_start: date,
    period_end: date,
    on_progress: Any = None,
) -> IngestResult:
    """Carrega itens de um arquivo JSONL local (uma resposta-de-pagina por linha).

    Util quando a API Compras.gov.br esta indisponivel (ex: backend JPA caido)
    e queremos exercitar o pipeline downstream com dados sinteticos.
    """
    if not fixture_path.exists():
        raise FileNotFoundError(fixture_path)

    def _iter() -> Iterator[dict[str, Any]]:
        with fixture_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)

    snapshot_id = (
        f"compras_gov_br_fixture_{period_start.isoformat()}_"
        f"{period_end.isoformat()}_{int(time.time())}"
    )
    logger.info("Ingest fixture: %s (snapshot=%s)", fixture_path, snapshot_id)
    return _persist_pages(
        _iter(),
        period_start=period_start,
        period_end=period_end,
        snapshot_id_override=snapshot_id,
        source=f"{SOURCE}/fixture",
        on_progress=on_progress,
    )
