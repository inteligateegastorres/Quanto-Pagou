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


class ContratoMunicipioOut(BaseModel):
    cluster_id: str
    cluster_version: str
    cd_ibge: str | None
    municipio: str | None
    porte: str
    orgao_codigo: str
    orgao_nome: str
    n_contratos: int
    valor_total_periodo: Decimal
    mediana_valor_contrato: Decimal
    p25_valor: Decimal
    p75_valor: Decimal


class FornecedorMunicipioOut(BaseModel):
    cd_ibge: str | None
    municipio: str | None
    fornecedor_cnpj: str
    fornecedor_nome: str | None
    n_contratos: int
    valor_total_periodo: Decimal
    n_orgaos_distintos: int


class TcePrSummaryOut(BaseModel):
    cd_ibge: str
    municipio: str
    n_contratos_total: int
    valor_total: Decimal
    n_em_cluster: int
    n_em_quarentena: int
    cobertura_pct: float = Field(
        description="Pct de contratos que casaram com algum cluster keyword"
    )


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


# ----------------------------- TCE-PR ---------------------------------

# Os endpoints abaixo usam mart_contratos_municipio e
# mart_fornecedores_municipio, que sao especificos da fonte tce_pr/contrato.
# Granularidade e por contrato (nao por item) — comparacao por valor de
# contrato com objeto similar (cluster por keyword em dsObjeto).


@app.get(
    "/tce-pr/municipio/{cd_ibge}/resumo",
    response_model=TcePrSummaryOut,
    tags=["tce-pr"],
)
def tce_pr_municipio_resumo(conn: ConnDep, cd_ibge: str) -> TcePrSummaryOut:
    """Resumo de contratos do TCE-PR para um municipio."""
    sql = """
        SELECT
            mp.cd_ibge AS cd_ibge,
            COALESCE(mp.nome, rc.raw_payload->>'municipio') AS municipio,
            COUNT(*) AS n_total,
            SUM(rc.valor_total) AS valor_total,
            COUNT(*) FILTER (WHERE ic.em_quarentena = FALSE) AS n_cluster,
            COUNT(*) FILTER (WHERE ic.em_quarentena = TRUE)  AS n_quarentena
        FROM raw.compras rc
        JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
        LEFT JOIN analytics.municipio_pr mp ON mp.cd_tce = rc.raw_payload->>'cd_tce'
        WHERE rc.source = 'tce_pr/contrato'
          AND mp.cd_ibge = %s
        GROUP BY 1, 2
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cd_ibge,))
        row = cur.fetchone()
    if row is None or row["n_total"] == 0:
        raise HTTPException(404, f"sem dados TCE-PR para cd_ibge={cd_ibge}")
    n_total = row["n_total"]
    n_cluster = row["n_cluster"]
    cobertura = (n_cluster / n_total) if n_total > 0 else 0.0
    return TcePrSummaryOut(
        cd_ibge=row["cd_ibge"],
        municipio=row["municipio"] or "",
        n_contratos_total=n_total,
        valor_total=row["valor_total"] or Decimal(0),
        n_em_cluster=n_cluster,
        n_em_quarentena=row["n_quarentena"],
        cobertura_pct=round(cobertura, 4),
    )


@app.get(
    "/tce-pr/municipio/{cd_ibge}/contratos-por-cluster",
    response_model=list[ContratoMunicipioOut],
    tags=["tce-pr"],
)
def tce_pr_contratos_por_cluster(
    conn: ConnDep,
    cd_ibge: str,
    cluster_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=200),
) -> list[ContratoMunicipioOut]:
    """Para um municipio, mostra agregados por cluster x orgao (gancho viral).

    Sem cluster_id: lista todos os clusters com algum contrato.
    Com cluster_id: filtra para um cluster especifico (top orgaos do municipio).
    """
    sql = """
        SELECT cluster_id, cluster_version, cd_ibge, municipio, porte,
               orgao_codigo, orgao_nome, n_contratos, valor_total_periodo,
               mediana_valor_contrato, p25_valor, p75_valor
        FROM analytics.mart_contratos_municipio
        WHERE cd_ibge = %s
          AND (%s::text IS NULL OR cluster_id = %s)
        ORDER BY valor_total_periodo DESC
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cd_ibge, cluster_id, cluster_id, limit))
        return [ContratoMunicipioOut(**r) for r in cur.fetchall()]


@app.get(
    "/tce-pr/municipio/{cd_ibge}/fornecedores",
    response_model=list[FornecedorMunicipioOut],
    tags=["tce-pr"],
)
def tce_pr_fornecedores(
    conn: ConnDep,
    cd_ibge: str,
    limit: int = Query(default=20, ge=1, le=200),
) -> list[FornecedorMunicipioOut]:
    """Top fornecedores de um municipio do PR (por valor acumulado)."""
    sql = """
        SELECT cd_ibge, municipio, fornecedor_cnpj, fornecedor_nome,
               n_contratos, valor_total_periodo, n_orgaos_distintos
        FROM analytics.mart_fornecedores_municipio
        WHERE cd_ibge = %s
        ORDER BY valor_total_periodo DESC
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cd_ibge, limit))
        return [FornecedorMunicipioOut(**r) for r in cur.fetchall()]


@app.get(
    "/tce-pr/cluster/{cluster_id}/comparacao-municipios",
    response_model=list[ContratoMunicipioOut],
    tags=["tce-pr"],
)
def tce_pr_comparacao_municipios(
    conn: ConnDep,
    cluster_id: str,
    cluster_version: str = "v1",
    porte: str | None = None,
    order: str = Query(default="mediana_desc"),
    limit: int = Query(default=30, ge=1, le=200),
) -> list[ContratoMunicipioOut]:
    """Compara municipios PR para um cluster especifico (ex: merenda escolar).

    Permite filtrar por porte (municipio_pr_grande/medio/pequeno) para garantir
    que so aparece comparacao entre pares de mesmo tamanho — guardrail do plano.
    """
    order_sql = {
        "mediana_desc": "mediana_valor_contrato DESC",
        "mediana_asc": "mediana_valor_contrato ASC",
        "total_desc": "valor_total_periodo DESC",
        "n_desc": "n_contratos DESC",
    }.get(order)
    if order_sql is None:
        raise HTTPException(400, f"order invalido: {order}")
    sql = f"""
        SELECT cluster_id, cluster_version, cd_ibge, municipio, porte,
               orgao_codigo, orgao_nome, n_contratos, valor_total_periodo,
               mediana_valor_contrato, p25_valor, p75_valor
        FROM analytics.mart_contratos_municipio
        WHERE cluster_id = %s AND cluster_version = %s
          AND (%s::text IS NULL OR porte = %s)
        ORDER BY {order_sql}
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cluster_id, cluster_version, porte, porte, limit))
        return [ContratoMunicipioOut(**r) for r in cur.fetchall()]
