"""Spider Compras.gov.br — endpoint /modulo-uasg/2_consultarOrgao.

Materializa `analytics.orgao_federal` (~11k linhas em 23 páginas).
Serve como tabela-de-loop para o spider de contratos (L.19.11.b): o
endpoint /modulo-contratos/2_consultarContratosItem passou a exigir
`codigoOrgao` como parâmetro obrigatório (descoberto em 2026-05-18).

Reusa o `httpx.Client` + retry/backoff de `compras.py` (mesmo host,
mesmas características do backend JPA upstream). Persiste payload bruto
em snapshot imutável (JSONL.gz) e faz upsert por `codigo_orgao`.

Progressive correctness: simples e suficiente. Não chama window-split
porque o endpoint não usa janela de data — é um cadastro plano,
paginado por contador.
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

from ingest.compras import HTTP_TIMEOUT, _get_page
from ingest.config import settings

logger = logging.getLogger(__name__)

ENDPOINT = "/modulo-uasg/2_consultarOrgao"
SOURCE = "compras_gov_br/orgaos"
DEFAULT_PAGE_SIZE = 500


@dataclass(slots=True)
class IngestOrgaosResult:
    snapshot_id: str
    snapshot_path: Path
    pages_fetched: int
    orgaos_total: int
    orgaos_upserted: int
    hash_sha256: str
    run_date: date


def _build_snapshot_id(run_date: date) -> str:
    ts = int(time.time())
    return f"compras_gov_br_orgaos_{run_date.isoformat()}_{ts}"


def _snapshot_path(snapshot_id: str) -> Path:
    base = settings.snapshots_dir / "compras_gov_br"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{snapshot_id}.jsonl.gz"


def _parse_movimento(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _coerce_orgao_row(item: dict[str, Any]) -> dict[str, Any]:
    """Mapeia um DmCorpOrgaoDTO para colunas de analytics.orgao_federal."""
    return {
        "codigo_orgao": item.get("codigoOrgao"),
        "nome": item.get("nomeOrgao") or "",
        "nome_mnemonico": item.get("nomeMnemonicoOrgao"),
        "cnpj": item.get("cnpjCpfOrgao"),
        "codigo_orgao_vinculado": item.get("codigoOrgaoVinculado"),
        "nome_orgao_vinculado": item.get("nomeOrgaoVinculado"),
        "codigo_orgao_superior": item.get("codigoOrgaoSuperior"),
        "nome_orgao_superior": item.get("nomeOrgaoSuperior"),
        "codigo_tipo_administracao": item.get("codigoTipoAdministracao"),
        "nome_tipo_administracao": item.get("nomeTipoAdministracao"),
        "poder": item.get("poder"),
        "esfera": item.get("esfera"),
        "uso_sisg": item.get("usoSisg"),
        "status_ativo": bool(item.get("statusOrgao", True)),
        "data_movimento": _parse_movimento(item.get("dataHoraMovimento")),
    }


def _iter_pages(
    client: httpx.Client,
    *,
    status_ativo: bool,
    page_size: int,
    max_pages: int | None,
) -> Iterator[dict[str, Any]]:
    page = 1
    while True:
        params = {
            "statusOrgao": str(status_ativo).lower(),
            "pagina": page,
            "tamanhoPagina": page_size,
        }
        payload = _get_page(client, params, endpoint=ENDPOINT)
        yield payload

        total_paginas = int(payload.get("totalPaginas") or 0)
        if total_paginas == 0 or page >= total_paginas:
            return
        if max_pages is not None and page >= max_pages:
            logger.info("Atingido max_pages=%s; parando.", max_pages)
            return
        page += 1


_UPSERT_ORGAO_SQL = """
INSERT INTO analytics.orgao_federal (
    codigo_orgao, nome, nome_mnemonico, cnpj,
    codigo_orgao_vinculado, nome_orgao_vinculado,
    codigo_orgao_superior, nome_orgao_superior,
    codigo_tipo_administracao, nome_tipo_administracao,
    poder, esfera, uso_sisg, status_ativo, data_movimento,
    raw_payload, snapshot_id
) VALUES (
    %(codigo_orgao)s, %(nome)s, %(nome_mnemonico)s, %(cnpj)s,
    %(codigo_orgao_vinculado)s, %(nome_orgao_vinculado)s,
    %(codigo_orgao_superior)s, %(nome_orgao_superior)s,
    %(codigo_tipo_administracao)s, %(nome_tipo_administracao)s,
    %(poder)s, %(esfera)s, %(uso_sisg)s, %(status_ativo)s, %(data_movimento)s,
    %(raw_payload)s, %(snapshot_id)s
)
ON CONFLICT (codigo_orgao) DO UPDATE SET
    nome                       = EXCLUDED.nome,
    nome_mnemonico             = EXCLUDED.nome_mnemonico,
    cnpj                       = EXCLUDED.cnpj,
    codigo_orgao_vinculado     = EXCLUDED.codigo_orgao_vinculado,
    nome_orgao_vinculado       = EXCLUDED.nome_orgao_vinculado,
    codigo_orgao_superior      = EXCLUDED.codigo_orgao_superior,
    nome_orgao_superior        = EXCLUDED.nome_orgao_superior,
    codigo_tipo_administracao  = EXCLUDED.codigo_tipo_administracao,
    nome_tipo_administracao    = EXCLUDED.nome_tipo_administracao,
    poder                      = EXCLUDED.poder,
    esfera                     = EXCLUDED.esfera,
    uso_sisg                   = EXCLUDED.uso_sisg,
    status_ativo               = EXCLUDED.status_ativo,
    data_movimento             = EXCLUDED.data_movimento,
    raw_payload                = EXCLUDED.raw_payload,
    snapshot_id                = EXCLUDED.snapshot_id,
    ultima_sync                = NOW()
"""


def _upsert_orgaos_batch(
    conn: psycopg.Connection,
    snapshot_id: str,
    items: list[dict[str, Any]],
) -> int:
    """Upsert por codigo_orgao. Itens sem codigo_orgao são descartados (log)."""
    rows = []
    for item in items:
        row = _coerce_orgao_row(item)
        if row["codigo_orgao"] is None:
            logger.warning("Órgão sem codigoOrgao descartado: %r", item)
            continue
        row["snapshot_id"] = snapshot_id
        row["raw_payload"] = Jsonb(item)
        rows.append(row)
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(_UPSERT_ORGAO_SQL, rows)
    return len(rows)


def _register_snapshot_in_progress(
    snapshot_id: str,
    *,
    source: str,
    run_date: date,
) -> None:
    """Insere snapshot 'in_progress' em conn separada (autocommit)."""
    with psycopg.connect(settings.database_url, autocommit=True) as bootstrap:
        bootstrap.execute(
            """
            INSERT INTO raw.snapshots
                (id, source, period_start, period_end, records_count, hash_sha256, status)
            VALUES (%s, %s, %s, %s, 0, '', 'in_progress')
            """,
            (snapshot_id, source, run_date, run_date),
        )


def _mark_snapshot_failed(snapshot_id: str, error: str) -> None:
    """Marca snapshot 'failed' em conn nova. Best-effort."""
    try:
        with psycopg.connect(settings.database_url, autocommit=True) as fail_conn:
            fail_conn.execute(
                "UPDATE raw.snapshots SET status='failed', error_message=%s WHERE id=%s",
                (error[:500], snapshot_id),
            )
    except Exception:
        logger.exception("Não consegui marcar snapshot %s como failed", snapshot_id)


def _persist_pages(
    pages: Iterator[dict[str, Any]],
    *,
    run_date: date,
    snapshot_id_override: str | None = None,
    source: str = SOURCE,
    on_progress: Any = None,
) -> IngestOrgaosResult:
    """Persiste stream de páginas: snapshot JSONL.gz + upsert em analytics.orgao_federal."""
    snapshot_id = snapshot_id_override or _build_snapshot_id(run_date)
    snap_path = _snapshot_path(snapshot_id)
    hasher = hashlib.sha256()
    pages_fetched = 0
    orgaos_total = 0
    orgaos_upserted = 0
    started = datetime.now()

    _register_snapshot_in_progress(snapshot_id, source=source, run_date=run_date)

    try:
        with (
            psycopg.connect(settings.database_url) as conn,
            gzip.open(snap_path, "wt", encoding="utf-8", compresslevel=6) as snap_fh,
        ):
            try:
                for payload in pages:
                    pages_fetched += 1
                    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                    hasher.update(line.encode("utf-8"))
                    snap_fh.write(line)
                    snap_fh.write("\n")

                    items = payload.get("resultado") or []
                    orgaos_total += len(items)
                    if items:
                        orgaos_upserted += _upsert_orgaos_batch(conn, snapshot_id, items)
                        conn.commit()

                    if on_progress:
                        on_progress(
                            page=pages_fetched,
                            total_pages=int(payload.get("totalPaginas") or 0),
                            orgaos_so_far=orgaos_total,
                        )
            except Exception:
                conn.rollback()
                raise

            hash_hex = hasher.hexdigest()
            conn.execute(
                """
                UPDATE raw.snapshots
                   SET records_count=%s, hash_sha256=%s, status='completed'
                 WHERE id=%s
                """,
                (orgaos_upserted, hash_hex, snapshot_id),
            )
            conn.commit()
    except Exception as exc:
        _mark_snapshot_failed(snapshot_id, f"{type(exc).__name__}: {exc}")
        raise

    elapsed = (datetime.now() - started).total_seconds()
    logger.info(
        "Persistência concluída em %.1fs: %d páginas, %d órgãos, snapshot=%s",
        elapsed,
        pages_fetched,
        orgaos_upserted,
        snap_path,
    )

    return IngestOrgaosResult(
        snapshot_id=snapshot_id,
        snapshot_path=snap_path,
        pages_fetched=pages_fetched,
        orgaos_total=orgaos_total,
        orgaos_upserted=orgaos_upserted,
        hash_sha256=hash_hex,
        run_date=run_date,
    )


def ingest_orgaos(
    *,
    status_ativo: bool = True,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int | None = None,
    run_date: date | None = None,
    on_progress: Any = None,
) -> IngestOrgaosResult:
    """Ingere cadastro de órgãos federais via API Compras.gov.br.

    Sem janela de data — o endpoint é um cadastro plano paginado.
    Por default coleta só órgãos ativos (statusOrgao=true).
    """
    run_date = run_date or date.today()
    headers = {"Accept": "application/json", "User-Agent": "quantopagou-ingest/0.0.1"}
    base = settings.compras_api_base.rstrip("/")

    logger.info(
        "Ingest órgãos federais iniciado (status_ativo=%s, page_size=%s)",
        status_ativo,
        page_size,
    )

    with httpx.Client(base_url=base, headers=headers, timeout=HTTP_TIMEOUT) as client:
        pages_iter = _iter_pages(
            client,
            status_ativo=status_ativo,
            page_size=page_size,
            max_pages=max_pages,
        )
        return _persist_pages(
            pages_iter,
            run_date=run_date,
            on_progress=on_progress,
        )


def ingest_orgaos_fixture(
    fixture_path: Path,
    *,
    run_date: date | None = None,
    on_progress: Any = None,
) -> IngestOrgaosResult:
    """Carrega cadastro de órgãos de um arquivo JSONL local (uma página por linha).

    Útil para tests e para exercitar o pipeline downstream quando a API
    está indisponível.
    """
    if not fixture_path.exists():
        raise FileNotFoundError(fixture_path)
    run_date = run_date or date.today()

    def _iter() -> Iterator[dict[str, Any]]:
        with fixture_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue
                yield json.loads(stripped)

    snapshot_id = f"compras_gov_br_orgaos_fixture_{run_date.isoformat()}_{int(time.time())}"
    logger.info("Ingest fixture órgãos: %s (snapshot=%s)", fixture_path, snapshot_id)
    return _persist_pages(
        _iter(),
        run_date=run_date,
        snapshot_id_override=snapshot_id,
        source=f"{SOURCE}/fixture",
        on_progress=on_progress,
    )
