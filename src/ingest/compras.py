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
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
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


@dataclass(slots=True)
class FailedWindow:
    period_start: date
    period_end: date
    error: str
    snapshot_id: str | None  # snapshot 'failed' registrado em raw.snapshots, se houver


@dataclass(slots=True)
class IngestRunSummary:
    """Sumario de uma execucao com window-splitting: 1 ou mais sub-janelas."""

    successes: list[IngestResult] = field(default_factory=list)
    failures: list[FailedWindow] = field(default_factory=list)

    @property
    def items_total(self) -> int:
        return sum(r.items_inserted for r in self.successes)

    @property
    def pages_total(self) -> int:
        return sum(r.pages_fetched for r in self.successes)

    @property
    def has_any_success(self) -> bool:
        return len(self.successes) > 0

    @property
    def has_any_failure(self) -> bool:
        return len(self.failures) > 0


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


# Backend Compras.gov.br entra em modo "EntityManager caido" por minutos
# de cada vez (pool JPA do lado deles). 8 tentativas com backoff ate 60s
# da uma janela de ~4min antes de desistir e deixar o split assumir.
@retry(
    retry=retry_if_exception_type(_RetryableHTTP),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(8),
    reraise=True,
)
def _get_page(
    client: httpx.Client,
    params: dict[str, Any],
    endpoint: str = ENDPOINT,
) -> dict[str, Any]:
    try:
        resp = client.get(endpoint, params=params)
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


def _register_snapshot_in_progress(
    snapshot_id: str,
    *,
    source: str,
    period_start: date,
    period_end: date,
) -> None:
    """Insere snapshot com status='in_progress' em transacao isolada (autocommit).

    Conn separada da que fara o ingest: se a ingest_conn morrer com rollback,
    a row de snapshot ja esta commitada, e podemos marca-la 'failed' depois.
    """
    with psycopg.connect(settings.database_url, autocommit=True) as bootstrap:
        bootstrap.execute(
            """
            INSERT INTO raw.snapshots
                (id, source, period_start, period_end, records_count, hash_sha256, status)
            VALUES (%s, %s, %s, %s, 0, '', 'in_progress')
            """,
            (snapshot_id, source, period_start, period_end),
        )


def _mark_snapshot_failed(snapshot_id: str, error: str) -> None:
    """Marca snapshot como 'failed' em conn nova. Best-effort: nunca propaga."""
    try:
        with psycopg.connect(settings.database_url, autocommit=True) as fail_conn:
            fail_conn.execute(
                "UPDATE raw.snapshots SET status='failed', error_message=%s WHERE id=%s",
                (error[:500], snapshot_id),
            )
    except Exception:
        logger.exception("Nao consegui marcar snapshot %s como failed", snapshot_id)


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

    _register_snapshot_in_progress(
        snapshot_id, source=source, period_start=period_start, period_end=period_end
    )

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
                """
                UPDATE raw.snapshots
                   SET records_count=%s, hash_sha256=%s, status='completed'
                 WHERE id=%s
                """,
                (items_inserted, hash_hex, snapshot_id),
            )
            conn.commit()
    except Exception as exc:
        _mark_snapshot_failed(snapshot_id, f"{type(exc).__name__}: {exc}")
        raise

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


# ---------------------------------------------------------------------------
# Window splitting: divide a janela ao meio quando o backend deles esta
# instavel demais para responder a janela inteira (sintoma classico:
# 400 + "Could not open JPA EntityManager"). Recursao ate min_window_days.
# Janelas terminais que falham viram snapshot 'failed' em raw.snapshots —
# pipeline downstream (build_marts) ignora essas linhas porque nao ha raw.compras.
# ---------------------------------------------------------------------------


def _is_split_recoverable(exc: BaseException) -> bool:
    """A excecao indica problema possivelmente especifico desta janela?"""
    if isinstance(exc, _RetryableHTTP):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        # 5xx ja sao retriable no _get_page; aqui pegamos 4xx persistentes
        # com mensagem de backend (pode ser data range que machucou o JPA deles).
        return 400 <= exc.response.status_code < 500
    if isinstance(exc, httpx.HTTPError):
        return True
    return False


def _split_window(
    period_start: date, period_end: date
) -> tuple[tuple[date, date], tuple[date, date]] | None:
    """Divide [start, end] inclusivo em duas metades. Retorna None se start==end."""
    length_days = (period_end - period_start).days + 1
    if length_days < 2:
        return None
    half = length_days // 2
    first_end = period_start + timedelta(days=half - 1)
    second_start = first_end + timedelta(days=1)
    return (period_start, first_end), (second_start, period_end)


def _ingest_window_recursive(
    period_start: date,
    period_end: date,
    *,
    page_size: int,
    max_pages: int | None,
    min_window_days: int,
    on_progress: Any,
    on_window_event: Any,
    summary: IngestRunSummary,
) -> None:
    length_days = (period_end - period_start).days + 1

    if on_window_event:
        on_window_event("start", period_start, period_end, length_days=length_days)

    try:
        result = ingest(
            period_start,
            period_end,
            page_size=page_size,
            max_pages=max_pages,
            on_progress=on_progress,
        )
    except Exception as exc:
        if not _is_split_recoverable(exc):
            # Erro nao-relacionado a backend instavel (ex: erro de DB local).
            # Nao adianta dividir; propaga para o caller.
            if on_window_event:
                on_window_event(
                    "fatal", period_start, period_end, error=str(exc)[:300]
                )
            raise

        if length_days <= min_window_days:
            err = f"{type(exc).__name__}: {exc}"[:500]
            # snapshot ja foi marcado 'failed' por _persist_pages se chegou a entrar la;
            # caso contrario nao ha snapshot_id para listar.
            summary.failures.append(
                FailedWindow(period_start, period_end, err, snapshot_id=None)
            )
            if on_window_event:
                on_window_event("fail", period_start, period_end, error=err)
            return

        # Divide e recurse.
        if on_window_event:
            on_window_event(
                "split", period_start, period_end, error=str(exc)[:300]
            )
        halves = _split_window(period_start, period_end)
        if halves is None:
            # Defensivo: nao deveria chegar aqui (length_days > min_window_days >= 1).
            err = f"{type(exc).__name__}: {exc}"[:500]
            summary.failures.append(
                FailedWindow(period_start, period_end, err, snapshot_id=None)
            )
            return
        first, second = halves
        _ingest_window_recursive(
            first[0], first[1],
            page_size=page_size, max_pages=max_pages,
            min_window_days=min_window_days,
            on_progress=on_progress, on_window_event=on_window_event,
            summary=summary,
        )
        _ingest_window_recursive(
            second[0], second[1],
            page_size=page_size, max_pages=max_pages,
            min_window_days=min_window_days,
            on_progress=on_progress, on_window_event=on_window_event,
            summary=summary,
        )
        return

    summary.successes.append(result)
    if on_window_event:
        on_window_event("ok", period_start, period_end, result=result)


def ingest_with_split(
    period_start: date,
    period_end: date,
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int | None = None,
    min_window_days: int = 1,
    on_progress: Any = None,
    on_window_event: Any = None,
) -> IngestRunSummary:
    """Ingere uma janela; em caso de falha transitoria, divide ao meio recursivamente.

    `min_window_days` = 1 significa "para de dividir quando a janela tem 1 dia
    (start == end)". Janelas terminais que falham viram FailedWindow no sumario
    e marcam snapshot 'failed' em raw.snapshots se o erro veio de dentro do
    _persist_pages (caso contrario snapshot_id e None).

    O caller pode passar `on_window_event(event, start, end, **kw)` para receber
    notificacoes ('start', 'ok', 'split', 'fail', 'fatal').
    """
    if period_start > period_end:
        raise ValueError("period_start > period_end")
    if min_window_days < 1:
        raise ValueError("min_window_days must be >= 1")

    summary = IngestRunSummary()
    _ingest_window_recursive(
        period_start, period_end,
        page_size=page_size, max_pages=max_pages,
        min_window_days=min_window_days,
        on_progress=on_progress, on_window_event=on_window_event,
        summary=summary,
    )
    return summary


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
