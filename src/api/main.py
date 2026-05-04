"""API publica do Quanto Pagou (FastAPI).

Endpoints minimos para Fase 0.5:
  GET  /health             - sanity + contagens
  GET  /clusters           - lista clusters disponiveis
  GET  /pares              - mart_pares filtrada por cluster
  GET  /ranking/orgaos     - mart_orgao_cluster ordenada (gancho viral)
  GET  /item/{raw_id}      - item canonicalizado + comparacao com pares
  GET  /quarentena/resumo  - saude publica do pipeline (% itens nao comparaveis)

Decisoes:
  - Pool psycopg simples (SimpleConnectionPool); sofisticar quando houver
    trafego real. Progressive correctness.
  - Modelos pydantic explicitos para abrir OpenAPI/Swagger limpo - uteis
    para jornalistas/pesquisadores que vao consumir direto a API.
  - Sem auth nesta fase (dados publicos por definicao). Rate limit fica para
    Fase 1+ via reverse proxy (Cloudflare / Caddy).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Annotated, Any

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field

from ingest.config import settings


# ----------------------------- pool -----------------------------------


_pool: ConnectionPool | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _pool
    _pool = ConnectionPool(
        conninfo=settings.database_url,
        min_size=1,
        max_size=10,
        kwargs={"row_factory": dict_row},
        open=True,
    )
    yield
    _pool.close()


def get_conn():
    assert _pool is not None, "pool not initialized"
    with _pool.connection() as conn:
        yield conn


# ----------------------------- modelos --------------------------------


class HealthOut(BaseModel):
    status: str
    snapshots: int
    raw_compras: int
    item_canonical: int
    em_quarentena: int
    mart_pares_rows: int
    mart_orgao_rows: int


class ClusterOut(BaseModel):
    cluster_id: str
    cluster_version: str
    descricao_canonica: str
    categoria: str
    n_itens: int = Field(description="Numero de itens canonicalizados nesse cluster")


class ParesOut(BaseModel):
    cluster_id: str
    cluster_version: str
    ente_nivel: str
    uf: str
    porte: str
    n: int
    minimo: Decimal
    p25: Decimal
    mediana: Decimal
    p75: Decimal
    maximo: Decimal
    iqr: Decimal


class RankingOrgaoOut(BaseModel):
    cluster_id: str
    cluster_version: str
    orgao_codigo: str
    orgao_nome: str
    n_compras: int
    mediana_orgao: Decimal
    valor_total_periodo: Decimal


class QuarentenaResumoOut(BaseModel):
    categoria: str | None
    motivo_quarentena: str | None
    n: int


class ItemOut(BaseModel):
    raw_id: int
    cluster_id: str | None
    cluster_version: str | None
    metodo_resolucao: str
    confianca_resolucao: float
    descricao_original: str
    catmat_id: str | None
    orgao_codigo: str | None
    orgao_nome: str | None
    fornecedor_cnpj: str | None
    fornecedor_nome: str | None
    contract_date: str | None
    valor_unitario: Decimal | None
    valor_unitario_normalizado: Decimal | None
    unidade_base: str | None
    fator_conversao: Decimal | None
    em_quarentena: bool
    motivo_quarentena: str | None
    pares: ParesOut | None = Field(
        default=None,
        description="Pares de comparacao (mesma uf+porte+ente). Ausente se em_quarentena.",
    )


# ----------------------------- app ------------------------------------


app = FastAPI(
    title="Quanto Pagou API",
    description=(
        "API publica de dados de gastos publicos brasileiros. "
        "Comparacoes apenas com confianca >= 0.75; itens em quarentena sao "
        "expostos com flag mas nunca somem do dataset."
    ),
    version="0.0.1",
    lifespan=lifespan,
)


ConnDep = Annotated[psycopg.Connection, Depends(get_conn)]


# ----------------------------- handlers -------------------------------


@app.get("/health", response_model=HealthOut, tags=["meta"])
def health(conn: ConnDep) -> HealthOut:
    counts: dict[str, int] = {}
    for label, sql in [
        ("snapshots", "SELECT COUNT(*) AS n FROM raw.snapshots"),
        ("raw_compras", "SELECT COUNT(*) AS n FROM raw.compras"),
        ("item_canonical", "SELECT COUNT(*) AS n FROM analytics.item_canonical"),
        (
            "em_quarentena",
            "SELECT COUNT(*) AS n FROM analytics.item_canonical WHERE em_quarentena",
        ),
        ("mart_pares_rows", "SELECT COUNT(*) AS n FROM analytics.mart_pares"),
        ("mart_orgao_rows", "SELECT COUNT(*) AS n FROM analytics.mart_orgao_cluster"),
    ]:
        with conn.cursor() as cur:
            cur.execute(sql)
            counts[label] = cur.fetchone()["n"]
    return HealthOut(status="ok", **counts)


@app.get("/clusters", response_model=list[ClusterOut], tags=["catalogo"])
def list_clusters(
    conn: ConnDep,
    categoria: str | None = Query(default=None, description="Filtra por categoria."),
) -> list[ClusterOut]:
    sql = """
        SELECT
            cr.cluster_id,
            cr.cluster_version,
            cr.descricao_canonica,
            cr.categoria,
            COUNT(ic.raw_id) AS n_itens
        FROM analytics.cluster_registry cr
        LEFT JOIN analytics.item_canonical ic
            ON ic.cluster_id = cr.cluster_id
           AND ic.cluster_version = cr.cluster_version
           AND ic.em_quarentena = FALSE
        WHERE cr.ativo = TRUE
          AND (%s::text IS NULL OR cr.categoria = %s)
        GROUP BY cr.cluster_id, cr.cluster_version, cr.descricao_canonica, cr.categoria
        ORDER BY n_itens DESC, cr.cluster_id
    """
    with conn.cursor() as cur:
        cur.execute(sql, (categoria, categoria))
        return [ClusterOut(**row) for row in cur.fetchall()]


@app.get("/pares", response_model=list[ParesOut], tags=["dados"])
def get_pares(
    conn: ConnDep,
    cluster_id: str,
    cluster_version: str = "v1",
) -> list[ParesOut]:
    sql = """
        SELECT cluster_id, cluster_version, ente_nivel, uf, porte,
               n, minimo, p25, mediana, p75, maximo, iqr
        FROM analytics.mart_pares
        WHERE cluster_id = %s AND cluster_version = %s
        ORDER BY ente_nivel, uf, porte
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cluster_id, cluster_version))
        rows = cur.fetchall()
    if not rows:
        raise HTTPException(404, f"sem mart_pares para {cluster_id} {cluster_version}")
    return [ParesOut(**r) for r in rows]


@app.get("/ranking/orgaos", response_model=list[RankingOrgaoOut], tags=["dados"])
def ranking_orgaos(
    conn: ConnDep,
    cluster_id: str,
    cluster_version: str = "v1",
    order: str = Query(default="mediana_desc", description="mediana_desc | mediana_asc | n_desc"),
    limit: int = Query(default=10, ge=1, le=100),
) -> list[RankingOrgaoOut]:
    order_sql = {
        "mediana_desc": "mediana_orgao DESC",
        "mediana_asc": "mediana_orgao ASC",
        "n_desc": "n_compras DESC",
    }.get(order)
    if order_sql is None:
        raise HTTPException(400, f"order invalido: {order}")
    sql = f"""
        SELECT cluster_id, cluster_version, orgao_codigo, orgao_nome,
               n_compras, mediana_orgao, valor_total_periodo
        FROM analytics.mart_orgao_cluster
        WHERE cluster_id = %s AND cluster_version = %s
        ORDER BY {order_sql}
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cluster_id, cluster_version, limit))
        return [RankingOrgaoOut(**r) for r in cur.fetchall()]


@app.get("/quarentena/resumo", response_model=list[QuarentenaResumoOut], tags=["meta"])
def quarentena_resumo(conn: ConnDep) -> list[QuarentenaResumoOut]:
    with conn.cursor() as cur:
        cur.execute("SELECT categoria, motivo_quarentena, n FROM analytics.v_quarentena_resumo")
        return [QuarentenaResumoOut(**r) for r in cur.fetchall()]


@app.get("/item/{raw_id}", response_model=ItemOut, tags=["dados"])
def get_item(conn: ConnDep, raw_id: int) -> ItemOut:
    sql = """
        SELECT
            ic.raw_id,
            ic.cluster_id, ic.cluster_version,
            ic.metodo_resolucao, ic.confianca_resolucao,
            ic.unidade_base, ic.fator_conversao,
            ic.valor_unitario_normalizado,
            ic.em_quarentena, ic.motivo_quarentena,
            ic.ente_nivel, ic.uf, ic.porte,
            rc.descricao AS descricao_original,
            rc.catmat_id, rc.orgao_codigo, rc.orgao_nome,
            rc.fornecedor_cnpj, rc.fornecedor_nome,
            rc.contract_date::text AS contract_date,
            rc.valor_unitario
        FROM analytics.item_canonical ic
        JOIN raw.compras rc ON rc.id = ic.raw_id
        WHERE ic.raw_id = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (raw_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(404, f"item {raw_id} nao encontrado")

    pares: ParesOut | None = None
    if not row["em_quarentena"] and row["cluster_id"]:
        sql_pares = """
            SELECT cluster_id, cluster_version, ente_nivel, uf, porte,
                   n, minimo, p25, mediana, p75, maximo, iqr
            FROM analytics.mart_pares
            WHERE cluster_id = %s AND cluster_version = %s
              AND ente_nivel = %s AND uf = %s AND porte = %s
        """
        with conn.cursor() as cur:
            cur.execute(
                sql_pares,
                (
                    row["cluster_id"],
                    row["cluster_version"],
                    row["ente_nivel"] or "desconhecido",
                    row["uf"] or "desconhecido",
                    row["porte"] or "desconhecido",
                ),
            )
            p = cur.fetchone()
        if p is not None:
            pares = ParesOut(**p)

    return ItemOut(
        raw_id=row["raw_id"],
        cluster_id=row["cluster_id"],
        cluster_version=row["cluster_version"],
        metodo_resolucao=row["metodo_resolucao"],
        confianca_resolucao=float(row["confianca_resolucao"] or 0),
        descricao_original=row["descricao_original"],
        catmat_id=row["catmat_id"],
        orgao_codigo=row["orgao_codigo"],
        orgao_nome=row["orgao_nome"],
        fornecedor_cnpj=row["fornecedor_cnpj"],
        fornecedor_nome=row["fornecedor_nome"],
        contract_date=row["contract_date"],
        valor_unitario=row["valor_unitario"],
        valor_unitario_normalizado=row["valor_unitario_normalizado"],
        unidade_base=row["unidade_base"],
        fator_conversao=row["fator_conversao"],
        em_quarentena=row["em_quarentena"],
        motivo_quarentena=row["motivo_quarentena"],
        pares=pares,
    )
