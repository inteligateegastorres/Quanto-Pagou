"""Spider TCE-PR — ZIP anual com Contratos de 399 municipios do Parana.

Fonte: pit.tce.pr.gov.br/Arquivos/{ano}_PIT_TodosArquivos.zip (publico, sem auth).
Estrutura: ZIP outer contem 1 sub-zip por (municipio, tema). Cada sub-zip
descompacta em XMLs ASP.NET-style (atributos no elemento, sem aninhamento).

Granularidade do TCE-PR e por CONTRATO, nao por item — vlContrato e o valor
total agregado, dsObjeto e descricao livre. Pipeline de cluster usa keyword
em dsObjeto (config/cluster_keywords.yaml), nao CATMAT.

Persistencia em raw.compras com source='tce_pr/contrato'. Coexiste com
o pipeline federal (source='compras_gov_br/contratos-item') sem conflito.
"""

from __future__ import annotations

import hashlib
import io
import logging
import time
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

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

SOURCE = "tce_pr/contrato"
PIT_BASE = "https://pit.tce.pr.gov.br/Arquivos"
HTTP_TIMEOUT = httpx.Timeout(120.0, connect=15.0)


@dataclass(slots=True)
class TcePrIngestResult:
    snapshot_id: str
    snapshot_path: Path
    ano: int
    municipios_processados: int
    contratos_inseridos: int
    hash_sha256: str


@dataclass(slots=True)
class _MunicipioStats:
    cd_tce: str
    n_contratos: int = 0
    error: str | None = None


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


class _RetryableHTTP(Exception):
    pass


@retry(
    retry=retry_if_exception_type(_RetryableHTTP),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)
def download_year_zip(ano: int, dest: Path) -> Path:
    """Baixa o ZIP anual do TCE-PR. Idempotente: se ja existe e tem tamanho > 0,
    nao redownload (mas tambem nao valida hash — isso fica para o snapshot).
    """
    if dest.exists() and dest.stat().st_size > 0:
        logger.info(
            "ZIP %s ja existe (%s bytes); reusando.", dest.name, dest.stat().st_size
        )
        return dest
    url = f"{PIT_BASE}/{ano}_PIT_TodosArquivos.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Baixando %s -> %s", url, dest)
    started = time.monotonic()
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as c:
            with c.stream("GET", url, headers={"User-Agent": "Mozilla/5.0"}) as r:
                if r.status_code in (502, 503, 504, 429):
                    raise _RetryableHTTP(f"HTTP {r.status_code}")
                r.raise_for_status()
                with dest.open("wb") as f:
                    bytes_total = 0
                    for chunk in r.iter_bytes(chunk_size=1 << 16):
                        f.write(chunk)
                        bytes_total += len(chunk)
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        raise _RetryableHTTP(str(e)) from e
    elapsed = time.monotonic() - started
    logger.info("Baixou %s bytes em %.1fs", bytes_total, elapsed)
    return dest


# ---------------------------------------------------------------------------
# Extracao + parse
# ---------------------------------------------------------------------------


def _list_municipios(year_zip: Path) -> list[str]:
    """Devolve a lista de codigos TCE de municipios presentes no ZIP anual.
    Inferida a partir dos nomes dos sub-zips: {ano}_{cd_tce}_Contrato.zip.
    """
    cods: set[str] = set()
    with zipfile.ZipFile(year_zip) as outer:
        for info in outer.infolist():
            if info.filename.endswith("_Contrato.zip"):
                # padrao: 2026_410690_Contrato.zip
                parts = info.filename.split("_")
                if len(parts) >= 3:
                    cods.add(parts[1])
    return sorted(cods)


def _extract_contrato_xml(
    year_zip: Path, ano: int, cd_tce: str
) -> ET.Element | None:
    """Extrai e parseia o XML de Contratos de um municipio. Retorna None
    se municipio nao tem Contrato.xml ou esta vazio (65 bytes = XML vazio).
    """
    sub_name = f"{ano}_{cd_tce}_Contrato.zip"
    inner_xml = f"{ano}_{cd_tce}_Contrato.xml"
    try:
        with zipfile.ZipFile(year_zip) as outer:
            with outer.open(sub_name) as sub_fh:
                sub_bytes = sub_fh.read()
        with zipfile.ZipFile(io.BytesIO(sub_bytes)) as inner:
            with inner.open(inner_xml) as xml_fh:
                xml_bytes = xml_fh.read()
    except KeyError:
        # municipio nao tem o arquivo
        return None
    if len(xml_bytes) < 100:
        # XML vazio (so o root) — pula
        return None
    # XML do TCE vem com BOM utf-8 inicial
    if xml_bytes.startswith(b"\xef\xbb\xbf"):
        xml_bytes = xml_bytes[3:]
    try:
        return ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        logger.warning("Parse XML falhou para %s: %s", sub_name, e)
        return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _parse_decimal(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_contrato_row(elem: ET.Element) -> dict[str, Any] | None:
    """Mapeia um <Contrato/> para colunas de raw.compras.
    Retorna None se faltar campo essencial (idContrato, dsObjeto, vlContrato).
    """
    a = elem.attrib
    id_contrato = a.get("idContrato")
    ds_objeto = a.get("dsObjeto") or ""
    vl_contrato = _parse_decimal(a.get("vlContrato"))
    if not id_contrato or not ds_objeto.strip() or vl_contrato is None:
        return None

    fornecedor_nome = (a.get("nmContratado") or "").strip() or None
    fornecedor_cnpj = (a.get("nrDocContratado") or "").strip() or None

    # raw_payload preserva atributos originais para reprocessamento.
    # Atencao: o atributo XML chama-se cdIBGE mas e na verdade o codigo
    # TCE-PR (6 digitos), nao o codigo IBGE real (7 digitos). Para obter
    # cd_ibge real, faz-se JOIN com analytics.municipio_pr no SQL.
    raw_payload: dict[str, Any] = {
        "cd_tce": a.get("cdIBGE"),
        "municipio": a.get("nmMunicipio"),
        "id_pessoa": a.get("idPessoa"),
        "nm_entidade": a.get("nmEntidade"),
        "id_contrato": id_contrato,
        "nr_contrato": a.get("nrContrato"),
        "nr_ano_contrato": a.get("nrAnoContrato"),
        "ds_tipo_regime_execucao": a.get("dsTipoRegimeExecucaoContrato"),
        "ds_tipo_garantia": a.get("dsTipoGarantiaContrato"),
        "ds_tipo_origem": a.get("dsTipoOrigemContrato"),
        "ds_tipo_ato": a.get("dsTipoAtoContrato"),
        "ds_tipo_forma_pagamento": a.get("dsTipoFormaPagamentoContrato"),
        "fl_subcontratacao": a.get("flSubContratacao"),
        "dt_inicio": a.get("dtInicio"),
        "dt_fim": a.get("dtFim"),
        "dt_envio": a.get("dtEnvio"),
        "data_referencia": a.get("DataReferencia"),
    }

    return {
        "source": SOURCE,
        "source_id": id_contrato,
        "source_url": None,  # TCE-PR exige login para URL canonica
        "contract_date": _parse_date(a.get("dtAssinatura")),
        "orgao_codigo": a.get("idPessoa"),
        "orgao_nome": (a.get("nmEntidade") or "").strip() or None,
        "fornecedor_cnpj": fornecedor_cnpj,
        "fornecedor_nome": fornecedor_nome,
        "catmat_id": None,
        "catser_id": None,
        "descricao": ds_objeto.strip(),
        "quantidade": 1.0,
        "unidade": "contrato",
        "valor_unitario": vl_contrato,
        "valor_total": vl_contrato,
        "modalidade": None,  # vem de Licitacao.xml + LicitacaoXContrato.xml; TODO fase 2
        "raw_payload": raw_payload,
    }


def iter_contratos(
    year_zip: Path, ano: int, *, municipios: list[str] | None = None
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Itera (cd_tce, contrato_row) ao longo dos municipios. Pula vazios.

    `municipios=None` significa todos. Lista pequena facilita teste/sample.
    """
    if municipios is None:
        municipios = _list_municipios(year_zip)
    for cd_tce in municipios:
        root = _extract_contrato_xml(year_zip, ano, cd_tce)
        if root is None:
            continue
        for elem in root.findall(".//Contrato"):
            row = _coerce_contrato_row(elem)
            if row is None:
                continue
            yield cd_tce, row


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------

_INSERT_SQL = """
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


def _build_snapshot_id(ano: int) -> str:
    ts = int(time.time())
    return f"tce_pr_contratos_{ano}_{ts}"


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 16):
            h.update(chunk)
    return h.hexdigest()


def ingest_year(
    ano: int,
    *,
    year_zip_path: Path | None = None,
    municipios: list[str] | None = None,
    on_municipio: Any = None,
) -> TcePrIngestResult:
    """Ingere todos os contratos de um ano do TCE-PR.

    `year_zip_path`: se None, baixa de pit.tce.pr.gov.br.
    `municipios`: filtra para uma lista de cd_tce (None = todos).
    `on_municipio(stats)`: callback opcional por municipio processado.
    """
    if year_zip_path is None:
        year_zip_path = settings.snapshots_dir / "tce_pr" / f"{ano}_PIT_TodosArquivos.zip"
        download_year_zip(ano, year_zip_path)
    elif not year_zip_path.exists():
        raise FileNotFoundError(year_zip_path)

    snapshot_id = _build_snapshot_id(ano)
    file_hash = _hash_file(year_zip_path)
    period_start = date(ano, 1, 1)
    period_end = date(ano, 12, 31)
    started = datetime.now()

    # Registra snapshot in_progress
    with psycopg.connect(settings.database_url, autocommit=True) as boot:
        boot.execute(
            """
            INSERT INTO raw.snapshots
                (id, source, period_start, period_end, records_count, hash_sha256, status)
            VALUES (%s, %s, %s, %s, 0, %s, 'in_progress')
            ON CONFLICT (id) DO NOTHING
            """,
            (snapshot_id, SOURCE, period_start, period_end, file_hash),
        )

    if municipios is None:
        municipios = _list_municipios(year_zip_path)
    logger.info("ano=%s, %d municipios a processar", ano, len(municipios))

    contratos_total = 0
    municipios_proc = 0
    try:
        with psycopg.connect(settings.database_url) as conn:
            for cd_tce in municipios:
                stats = _MunicipioStats(cd_tce=cd_tce)
                root = _extract_contrato_xml(year_zip_path, ano, cd_tce)
                if root is None:
                    if on_municipio:
                        on_municipio(stats)
                    continue
                rows: list[dict[str, Any]] = []
                for elem in root.findall(".//Contrato"):
                    row = _coerce_contrato_row(elem)
                    if row is None:
                        continue
                    row["snapshot_id"] = snapshot_id
                    row["raw_payload"] = Jsonb({"cd_tce": cd_tce, **row["raw_payload"]})
                    rows.append(row)
                if rows:
                    with conn.cursor() as cur:
                        cur.executemany(_INSERT_SQL, rows)
                    conn.commit()
                stats.n_contratos = len(rows)
                contratos_total += stats.n_contratos
                municipios_proc += 1
                if on_municipio:
                    on_municipio(stats)
    except Exception as e:
        with psycopg.connect(settings.database_url, autocommit=True) as fail_conn:
            fail_conn.execute(
                "UPDATE raw.snapshots SET status='failed', error_message=%s WHERE id=%s",
                (f"{type(e).__name__}: {e}"[:500], snapshot_id),
            )
        raise

    # Marca snapshot como completed
    with psycopg.connect(settings.database_url, autocommit=True) as done:
        done.execute(
            """
            UPDATE raw.snapshots
               SET records_count=%s, hash_sha256=%s, status='completed'
             WHERE id=%s
            """,
            (contratos_total, file_hash, snapshot_id),
        )

    elapsed = (datetime.now() - started).total_seconds()
    logger.info(
        "ano=%s OK: %d municipios, %d contratos em %.1fs",
        ano, municipios_proc, contratos_total, elapsed,
    )

    return TcePrIngestResult(
        snapshot_id=snapshot_id,
        snapshot_path=year_zip_path,
        ano=ano,
        municipios_processados=municipios_proc,
        contratos_inseridos=contratos_total,
        hash_sha256=file_hash,
    )
