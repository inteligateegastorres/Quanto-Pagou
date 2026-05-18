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

import csv
import io
import os
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Literal

import psycopg
from psycopg import sql as psycopg_sql
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

# Pool/lifespan/ConnDep extraidos pra deps.py (PLANO §17.B.1 fase 1).
# Endpoints e modelos serao movidos pra routers/schemas em fase 2.
from api.deps import FORNECEDOR_THRESHOLD as _FORNECEDOR_THRESHOLD
from api.deps import ConnDep, lifespan


# Sentry — observabilidade opcional. Inicializa SO se SENTRY_DSN_API
# estiver setado e o pacote estiver instalado. Sem DSN = no-op.
# (DEPLOY.md / .env.production.example documentam a chave.)
_sentry_dsn = os.environ.get("SENTRY_DSN_API")
if _sentry_dsn:
    try:
        import sentry_sdk  # type: ignore[import-untyped]

        sentry_sdk.init(
            dsn=_sentry_dsn,
            traces_sample_rate=float(
                os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.05")
            ),
            send_default_pii=False,
        )
    except ImportError:
        # sentry-sdk nao instalado — silencioso, ambiente dev tipico.
        pass

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


class RankingMunicipioOut(BaseModel):
    cluster_id: str
    cd_tce: str
    cd_ibge: str
    municipio: str
    porte: str
    populacao: int | None  # IBGE Censo 2022 (PLANO §19.7)
    n_contratos: int
    valor_total_periodo: Decimal
    mediana_valor_contrato: Decimal


class PerCapitaOut(BaseModel):
    """PLANO §19.7 — gasto_per_capita = SUM(valor_total)/populacao IBGE 2022."""

    cluster_id: str
    cluster_version: str
    cd_tce: str
    cd_ibge: str
    municipio: str
    porte: str
    populacao: int
    n_contratos: int
    gasto_total: Decimal
    gasto_per_capita: Decimal
    mediana_valor_contrato: Decimal


class FornecedorMunicipioOut(BaseModel):
    cd_ibge: str | None
    municipio: str | None
    fornecedor_cnpj: str
    fornecedor_nome: str | None
    n_contratos: int
    valor_total_periodo: Decimal
    n_orgaos_distintos: int


class StatsPrModalidadeOut(BaseModel):
    modalidade: str
    n_contratos: int


class StatsPrTopClusterOut(BaseModel):
    cluster_id: str
    descricao_canonica: str | None
    n_contratos: int


class StatsPrOut(BaseModel):
    total_contratos: int
    total_municipios: int
    total_fornecedores: int
    n_em_cluster: int
    n_em_quarentena: int
    cobertura_cluster_pct: float = Field(
        description="Pct de contratos categorizados por keyword (vs quarentena)"
    )
    valor_total_pr: Decimal | None
    modalidades: list[StatsPrModalidadeOut]
    top_clusters: list[StatsPrTopClusterOut]
    last_snapshot_at: str | None
    n_escolas_catalogadas: int


class MunicipioListItemOut(BaseModel):
    cd_tce: str
    cd_ibge: str | None
    nome: str
    porte: str
    catalogado: bool
    n_contratos: int
    valor_total: Decimal


class FornecedorListItemOut(BaseModel):
    fornecedor_cnpj: str
    fornecedor_nome: str | None
    n_contratos: int
    valor_total: Decimal
    n_municipios_distintos: int


class InstituicaoFornecedorOut(BaseModel):
    fornecedor_cnpj: str
    fornecedor_nome: str | None
    n_contratos: int
    valor_total: Decimal
    n_municipios: int


class InstituicaoOrgaoOut(BaseModel):
    orgao_codigo: str
    orgao_nome: str
    cd_tce: str | None
    cd_ibge: str | None
    municipio: str | None
    n_contratos: int
    valor_total: Decimal


class InstituicaoObjetoOut(BaseModel):
    """Contratos cujo objeto menciona o termo, agrupados por (municipio, orgao)."""
    cd_tce: str | None
    cd_ibge: str | None
    municipio: str | None
    orgao_codigo: str
    orgao_nome: str
    n_contratos: int
    valor_total: Decimal


class InstituicaoFornecedorObjetoOut(BaseModel):
    """Top fornecedores PAGOS em contratos cujo objeto menciona o termo.
    Ex: "quem mais recebeu por contratos que mencionam UPA Centro?"."""
    fornecedor_cnpj: str
    fornecedor_nome: str | None
    n_contratos: int
    valor_total: Decimal
    n_municipios: int


class InstituicoesSearchOut(BaseModel):
    q: str
    fornecedores: list[InstituicaoFornecedorOut]
    orgaos: list[InstituicaoOrgaoOut]
    objetos: list[InstituicaoObjetoOut]
    fornecedores_no_objeto: list[InstituicaoFornecedorObjetoOut]
    total_fornecedores: int
    total_orgaos: int
    total_objeto_contratos: int
    total_fornecedores_no_objeto: int
    valor_total_objeto: Decimal


class ContratoSearchItemOut(BaseModel):
    raw_id: int
    source_id: str | None
    municipio: str | None
    cd_tce: str | None
    orgao_nome: str | None
    fornecedor_cnpj: str | None
    fornecedor_nome: str | None
    descricao: str
    valor_total: Decimal | None
    contract_date: str | None
    cluster_id: str | None
    cluster_descricao: str | None
    modalidade: str | None
    em_quarentena: bool


class ContratoSearchPageOut(BaseModel):
    page: int
    limit: int
    total: int
    valor_total_filtrado: Decimal
    contratos: list[ContratoSearchItemOut]


class DispensaTopFornecedorOut(BaseModel):
    fornecedor_cnpj: str
    fornecedor_nome: str | None
    n_dispensas: int
    valor_total_dispensas: Decimal
    n_municipios: int
    n_orgaos: int
    cnpj_mascarado: bool


class MunicipioInfoOut(BaseModel):
    cd_tce: str
    cd_ibge: str | None
    nome: str
    porte: str
    catalogado: bool = Field(
        description="True se o municipio esta na tabela municipio_pr"
    )


class EscolaListItemOut(BaseModel):
    escola_slug: str
    escola_nome: str  # primeiro nome observado (variantes podem existir)
    n_mencoes: int
    n_municipios: int
    valor_total: Decimal


class EscolaContratoOut(BaseModel):
    raw_id: int
    contrato_id: str | None
    municipio: str | None
    cd_tce: str | None
    orgao_nome: str | None
    descricao: str
    valor_total: Decimal | None
    contract_date: str | None
    cluster_id: str | None
    padrao: str  # qual regex casou (auditoria)
    escola_nome: str  # nome exato extraido (varia entre contratos)


class ContratoDetalheOut(BaseModel):
    raw_id: int
    source: str
    source_id: str | None
    source_url: str | None
    contract_date: str | None
    orgao_codigo: str | None
    orgao_nome: str | None
    fornecedor_cnpj: str | None
    fornecedor_nome: str | None
    descricao: str
    valor_total: Decimal | None
    valor_unitario: Decimal | None
    quantidade: Decimal | None
    unidade: str | None
    modalidade: str | None
    catmat_id: str | None
    catser_id: str | None
    raw_payload: dict[str, Any]
    # canonicalizacao
    cluster_id: str | None
    cluster_version: str | None
    cluster_descricao: str | None
    metodo_resolucao: str | None
    confianca_resolucao: float | None
    em_quarentena: bool
    motivo_quarentena: str | None
    # snapshot (camada de durabilidade)
    snapshot_id: str
    snapshot_period_start: str | None
    snapshot_period_end: str | None
    snapshot_hash_sha256: str | None
    snapshot_ingested_at: str
    # municipio (so para TCE-PR)
    cd_ibge: str | None
    municipio_nome: str | None


class FornecedorPerfilOut(BaseModel):
    fornecedor_cnpj: str
    fornecedor_nome: str | None
    n_contratos_total: int
    valor_total: Decimal
    n_orgaos_distintos: int
    n_municipios_distintos: int
    primeiro_contrato: str | None
    ultimo_contrato: str | None
    cnpj_mascarado: bool = Field(
        description="True se CNPJ vem mascarado (TCE-PR mascara CPFs de PFs)"
    )


class AlertaProgressivoOut(BaseModel):
    """Alerta de aumento progressivo trimestre-a-trimestre (PLANO §19.4)."""
    fornecedor_cnpj: str
    fornecedor_nome: str | None
    cd_tce: str
    cluster_id: str
    trimestre_1: str
    trimestre_2: str
    trimestre_3: str
    mediana_1: Decimal
    mediana_2: Decimal
    mediana_3: Decimal
    growth_ratio: Decimal = Field(
        description="mediana_3 / mediana_1. >= 1.44 (1.2² mínimo do filtro) por construção."
    )
    n_1: int
    n_2: int
    n_3: int
    total_1: Decimal
    total_2: Decimal
    total_3: Decimal


class FornecedorContratoOut(BaseModel):
    raw_id: int
    contrato_id: str
    municipio: str | None
    orgao_nome: str
    descricao: str
    valor_total: Decimal
    contract_date: str | None
    cluster_id: str | None
    em_quarentena: bool


class FornecedorAgregadoOut(BaseModel):
    chave: str
    nome: str | None
    n_contratos: int
    valor_total: Decimal


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


# Correcoes (LGPD L.12)


class CorrecaoTicketIn(BaseModel):
    tipo: Literal[
        "factual",
        "lgpd_acesso",
        "lgpd_correcao",
        "lgpd_eliminacao",
        "classificacao_pj",
        "revisao_ranking",
        "outro",
    ] = Field(description="Natureza do pedido. Define SLA (factual=48h, lgpd_*=15d, revisao_ranking=15d art. 20).")
    descricao: str = Field(min_length=20, max_length=4000)
    url_afetada: str | None = Field(default=None, max_length=500)
    raw_id_afetado: int | None = None
    fornecedor_cnpj: str | None = Field(default=None, max_length=20)
    fonte_correta: str | None = Field(default=None, max_length=1000)
    publicar_descricao: bool = Field(
        default=False,
        description="Se TRUE, a descricao pode aparecer na vitrine publica /correcoes ao ser resolvido. Default FALSE (privacidade).",
    )
    contato_email: str | None = Field(default=None, max_length=255)


class CorrecaoTicketOut(BaseModel):
    ticket_id: str
    criado_em: str
    tipo: str
    sla_classe: str
    status: str
    descricao_publica: str | None = Field(
        description="Descricao do problema, apenas se publicar_descricao=TRUE OU se status nao for terminal. Caso contrario None.",
    )
    url_afetada: str | None
    raw_id_afetado: int | None
    fornecedor_cnpj: str | None
    resolvido_em: str | None
    resolucao_publica: str | None
    prazo_iso: str | None = Field(
        description="Prazo nominal de resposta (criado_em + SLA). Pode ser passado sem resposta — auditoria publica.",
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


# ConnDep importado de api.deps (PLANO §17.B.1 fase 1).


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
        # Distingue tres casos:
        #   1. cluster nao existe                 -> 404 simples
        #   2. cluster existe mas e contract-level (TCE-PR sem unit price)
        #                                         -> 404 sugerindo o endpoint correto
        #   3. cluster existe item-a-item mas sem dados que passem o threshold
        #                                         -> 404 explicando o filtro
        with conn.cursor() as cur:
            cur.execute(
                "SELECT cluster_id FROM analytics.cluster_registry "
                "WHERE cluster_id = %s AND cluster_version = %s LIMIT 1",
                (cluster_id, cluster_version),
            )
            existe = cur.fetchone() is not None
            if not existe:
                raise HTTPException(
                    404, f"cluster '{cluster_id}' (v={cluster_version}) nao existe"
                )
            cur.execute(
                "SELECT COUNT(*) AS n FROM analytics.item_canonical "
                "WHERE cluster_id = %s AND cluster_version = %s "
                "  AND valor_unitario_normalizado IS NOT NULL",
                (cluster_id, cluster_version),
            )
            n_com_unit_price = cur.fetchone()["n"]
        if n_com_unit_price == 0:
            raise HTTPException(
                404,
                f"cluster '{cluster_id}' e contract-level (sem preco unitario "
                f"normalizado) — use /tce-pr/cluster/{cluster_id}/comparacao-municipios "
                f"para comparacao por contrato entre municipios PR.",
            )
        raise HTTPException(
            404,
            f"cluster '{cluster_id}' nao tem itens com confianca >= 0.75 "
            f"(threshold de mart_pares) — verifique /quarentena/resumo.",
        )
    return [ParesOut(**r) for r in rows]


@app.get("/ranking/orgaos", response_model=list[RankingOrgaoOut], tags=["dados"])
def ranking_orgaos(
    conn: ConnDep,
    cluster_id: str,
    cluster_version: str = "v1",
    order: Literal["mediana_desc", "mediana_asc", "n_desc"] = Query(
        default="mediana_desc",
        description="mediana_desc | mediana_asc | n_desc",
    ),
    limit: int = Query(default=10, ge=1, le=100),
) -> list[RankingOrgaoOut]:
    order_sql = {
        "mediana_desc": "mediana_orgao DESC",
        "mediana_asc": "mediana_orgao ASC",
        "n_desc": "n_compras DESC",
    }[order]
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


# ----------------------------- Eliminacoes (LGPD art. 18 IV) ----------------


class EliminacaoPublicaOut(BaseModel):
    """Lista publica de eliminacoes (transparencia LGPD).

    Mostra raw_id + motivo + fundamento + data, SEM reproduzir o conteudo
    eliminado. Cidadao confere que pedidos sao atendidos; conteudo
    permanece eliminado.
    """

    raw_id: int
    eliminada_em: str
    motivo: str
    fundamento_legal: str
    ticket_ref: str | None


@app.get(
    "/eliminacoes/publicas",
    response_model=list[EliminacaoPublicaOut],
    tags=["meta"],
)
def eliminacoes_publicas(
    conn: ConnDep,
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[EliminacaoPublicaOut]:
    """Lista publica de eliminacoes atendidas (LGPD art. 18 IV).

    Transparencia radical: todo cidadao pode auditar quais raw_ids foram
    removidos e com qual fundamento legal. Conteudo nunca e reproduzido
    aqui — so o registro do ato.

    Refletir como vitrine de cumprimento (similar a `/correcoes`) — vide
    PLANO §18 L.1.
    """
    sql = """
        SELECT raw_id, eliminada_em::text AS eliminada_em,
               motivo, fundamento_legal, ticket_ref
        FROM analytics.eliminacao
        ORDER BY eliminada_em DESC LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (limit,))
        return [EliminacaoPublicaOut(**r) for r in cur.fetchall()]


# ----------------------------- Manchetes ------------------------------------


class ManchteOut(BaseModel):
    """Uma manchete algoritmica selecionada pelo YAML versionado."""

    rank_no_dia: int
    cluster_id: str
    cluster_version: str
    cd_tce: str
    cd_ibge: str | None
    municipio_nome: str | None
    porte: str | None
    populacao: int | None
    n_sujeito: int
    valor_total_sujeito: Decimal
    med_sujeito: Decimal
    med_cluster: Decimal
    spread: Decimal
    iqr_sujeito: Decimal
    iqr_cluster: Decimal
    comparab_proxy: Decimal
    # Estabilidade temporal: spreads em 3 janelas (NULL se janela vazia)
    # + count de quantas passaram o spread_min do YAML.
    spread_90d: Decimal | None
    spread_180d: Decimal | None
    spread_365d: Decimal | None
    janelas_passadas: int
    rank_score: Decimal
    parametros_hash: str
    refresh_em: str


class ManchteSaidaOut(BaseModel):
    """Manchete que saiu — payload anterior + motivo diagnostico."""

    saiu_em: str
    manchete_id: str
    motivo: str
    cluster_id: str | None
    municipio_nome: str | None
    spread_anterior: Decimal | None
    parametros_hash: str


_SITE_URL = os.environ.get(
    "NEXT_PUBLIC_SITE_URL", "https://quantopagou.org"
).rstrip("/")


def _rows_to_csv_response(
    rows: list[dict[str, Any]],
    fieldnames: list[str],
    filename: str,
) -> Response:
    """Helper L.19.3: serializa lista de dicts em CSV pra download.
    Aceita Decimal, date, None — converte pra str apropriada."""
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=fieldnames, extrasaction="ignore", quoting=csv.QUOTE_MINIMAL
    )
    writer.writeheader()
    for r in rows:
        out: dict[str, Any] = {}
        for k in fieldnames:
            v = r.get(k)
            if v is None:
                out[k] = ""
            elif isinstance(v, Decimal):
                out[k] = format(v, "f")
            elif isinstance(v, (date,)):
                out[k] = v.isoformat()
            else:
                out[k] = v
        writer.writerow(out)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "public, max-age=300",
        },
    )


def _xml_escape(s: str | None) -> str:
    if s is None:
        return ""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


@app.get(
    "/manchetes/feed.xml",
    response_class=Response,
    tags=["meta"],
    summary="Atom feed das manchetes ativas (PLANO §19.2)",
)
def manchetes_feed(conn: ConnDep) -> Response:
    """Atom 1.0 das manchetes ativas — engajamento sem login.
    Cada entry tem id estavel (cluster_id + cd_tce + parametros_hash)
    pra leitores RSS deduplicarem corretamente. Substitui parcialmente
    necessidade de alerta por e-mail (PLANO §19)."""
    sql = """
        SELECT cluster_id, cluster_version, cd_tce, municipio_nome,
               spread, med_sujeito, med_cluster, n_sujeito,
               valor_total_sujeito, parametros_hash,
               refresh_em
        FROM analytics.manchete
        ORDER BY rank_no_dia
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    last_updated = (
        max((r["refresh_em"] for r in rows), default=None)
        if rows
        else None
    )
    feed_updated = (
        last_updated.isoformat() if last_updated else "2026-01-01T00:00:00+00:00"
    )

    entries = []
    for r in rows:
        cluster_id = r["cluster_id"]
        cd_tce = r["cd_tce"]
        municipio = r["municipio_nome"] or cd_tce
        spread = float(r["spread"] or 0)
        med_s = float(r["med_sujeito"] or 0)
        med_c = float(r["med_cluster"] or 0)
        n_sujeito = int(r["n_sujeito"] or 0)
        params_hash = r["parametros_hash"] or "v0"
        # id estavel — muda se cluster, municipio ou config mudar
        entry_id = (
            f"tag:quantopagou.org,2026:manchete:"
            f"{cluster_id}:{cd_tce}:{params_hash[:8]}"
        )
        link = f"{_SITE_URL}/manchetes#{cluster_id}-{cd_tce}"
        title = (
            f"{municipio}: mediana de {cluster_id.replace('_', ' ')} "
            f"{spread:.1f}× a do estado"
        )
        summary = (
            f"Mediana do município: R$ {med_s:,.2f} · "
            f"Mediana do cluster PR: R$ {med_c:,.2f} · "
            f"{n_sujeito} contratos no período."
        ).replace(",", ".")
        updated = (
            r["refresh_em"].isoformat()
            if r["refresh_em"]
            else feed_updated
        )
        entries.append(
            f"""  <entry>
    <id>{_xml_escape(entry_id)}</id>
    <title>{_xml_escape(title)}</title>
    <link href="{_xml_escape(link)}" rel="alternate"/>
    <updated>{_xml_escape(updated)}</updated>
    <summary type="text">{_xml_escape(summary)}</summary>
    <category term="{_xml_escape(cluster_id)}"/>
  </entry>"""
        )

    feed_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        f"  <title>Manchetes — Quanto Pagou</title>\n"
        f"  <subtitle>Discrepâncias algoritmicas em gastos públicos "
        f"municipais do Paraná. Sem curadoria humana.</subtitle>\n"
        f"  <link href=\"{_xml_escape(_SITE_URL + '/manchetes')}\" "
        f'rel="alternate"/>\n'
        f"  <link href=\"{_xml_escape(_SITE_URL + '/manchetes/feed.xml')}\" "
        f'rel="self"/>\n'
        f"  <id>tag:quantopagou.org,2026:manchetes</id>\n"
        f"  <updated>{_xml_escape(feed_updated)}</updated>\n"
        f"  <generator uri=\"{_xml_escape(_SITE_URL)}\" version=\"1\">"
        "Quanto Pagou</generator>\n"
        f"  <rights>CC-BY 4.0 — Quanto Pagou. Dados primários: TCE-PR (público).</rights>\n"
        + "\n".join(entries)
        + "\n</feed>\n"
    )
    return Response(
        content=feed_xml,
        media_type="application/atom+xml; charset=utf-8",
        headers={"Cache-Control": "public, max-age=1800"},
    )


@app.get(
    "/manchetes.csv",
    response_class=Response,
    tags=["meta"],
    summary="Manchetes ativas em CSV (PLANO §19.3)",
)
def get_manchetes_csv(conn: ConnDep) -> Response:
    sql = """
        SELECT rank_no_dia, cluster_id, cluster_version, cd_tce, cd_ibge,
               municipio_nome, porte, populacao, n_sujeito, valor_total_sujeito,
               med_sujeito, med_cluster, spread, iqr_sujeito, iqr_cluster,
               comparab_proxy, spread_90d, spread_180d, spread_365d,
               janelas_passadas, rank_score, parametros_hash
        FROM analytics.manchete
        ORDER BY rank_no_dia
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return _rows_to_csv_response(
        rows,
        fieldnames=[
            "rank_no_dia", "cluster_id", "cluster_version", "cd_tce", "cd_ibge",
            "municipio_nome", "porte", "populacao", "n_sujeito",
            "valor_total_sujeito", "med_sujeito", "med_cluster", "spread",
            "iqr_sujeito", "iqr_cluster", "comparab_proxy",
            "spread_90d", "spread_180d", "spread_365d",
            "janelas_passadas", "rank_score", "parametros_hash",
        ],
        filename="manchetes_quantopagou.csv",
    )


@app.get(
    "/alertas/progressivos",
    response_model=list[AlertaProgressivoOut],
    tags=["meta"],
    summary="Alertas de aumento progressivo trimestre-a-trimestre (PLANO §19.4)",
)
def get_alertas_progressivos(
    conn: ConnDep, limit: int = Query(default=50, ge=1, le=500)
) -> list[AlertaProgressivoOut]:
    """Combinações (fornecedor PJ + município + cluster) onde a mediana
    do valor de contrato cresceu >1.2× em cada trimestre nos últimos 3
    trimestres consecutivos com dados. Complementa /manchetes —
    manchete capta nível, alerta progressivo capta tendência."""
    sql = """
        SELECT fornecedor_cnpj, fornecedor_nome, cd_tce, cluster_id,
               trimestre_1::text, trimestre_2::text, trimestre_3::text,
               mediana_1, mediana_2, mediana_3, growth_ratio,
               n_1, n_2, n_3, total_1, total_2, total_3
        FROM analytics.alerta_progressivo
        ORDER BY growth_ratio DESC
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (limit,))
        return [AlertaProgressivoOut(**r) for r in cur.fetchall()]


@app.get(
    "/alertas/progressivos.csv",
    response_class=Response,
    tags=["meta"],
    summary="Alertas progressivos em CSV (PLANO §19.3 + §19.4)",
)
def get_alertas_progressivos_csv(
    conn: ConnDep, limit: int = Query(default=500, ge=1, le=5000)
) -> Response:
    sql = """
        SELECT fornecedor_cnpj, fornecedor_nome, cd_tce, cluster_id,
               trimestre_1::text, trimestre_2::text, trimestre_3::text,
               mediana_1, mediana_2, mediana_3, growth_ratio,
               n_1, n_2, n_3, total_1, total_2, total_3
        FROM analytics.alerta_progressivo
        ORDER BY growth_ratio DESC
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (limit,))
        rows = cur.fetchall()
    return _rows_to_csv_response(
        rows,
        fieldnames=[
            "fornecedor_cnpj", "fornecedor_nome", "cd_tce", "cluster_id",
            "trimestre_1", "trimestre_2", "trimestre_3",
            "mediana_1", "mediana_2", "mediana_3", "growth_ratio",
            "n_1", "n_2", "n_3", "total_1", "total_2", "total_3",
        ],
        filename="alertas_progressivos_quantopagou.csv",
    )


@app.get("/manchetes", response_model=list[ManchteOut], tags=["meta"])
def get_manchetes(conn: ConnDep) -> list[ManchteOut]:
    """Top N manchetes ativas (algoritmo, nao curadoria). Ordenadas por rank.

    Selecao definida em config/manchete_v*.yaml. Cada linha carrega
    parametros_hash pra auditoria — permite reconstruir contra qual config
    a manchete foi gerada.

    Para tunar: editar YAML e rodar
      python -m uv run python -m analytics.manchetes refresh
    """
    sql = """
        SELECT
            rank_no_dia, cluster_id, cluster_version, cd_tce, cd_ibge,
            municipio_nome, porte, populacao, n_sujeito, valor_total_sujeito,
            med_sujeito, med_cluster, spread, iqr_sujeito, iqr_cluster,
            comparab_proxy, spread_90d, spread_180d, spread_365d,
            janelas_passadas, rank_score, parametros_hash,
            refresh_em::text AS refresh_em
        FROM analytics.manchete
        ORDER BY rank_no_dia
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return [ManchteOut(**r) for r in cur.fetchall()]


class ManchteCandidatoDiagOut(BaseModel):
    cluster_id: str
    n_sujeito: int
    spread: Decimal | None
    iqr_sujeito: Decimal | None
    comparab_proxy: Decimal | None
    motivo_falha: str | None  # None se passou todos os thresholds


class ManchteDiagnosticoOut(BaseModel):
    cd_tce: str
    municipio_nome: str | None
    populacao: int | None
    parametros_hash: str | None
    ativas: list[ManchteOut]                # manchetes onde o municipio aparece
    candidatos: list[ManchteCandidatoDiagOut]  # outros clusters com discrepancias avaliadas


def _diag_motivo_falha(row: dict[str, Any], cfg: dict[str, Any]) -> str | None:
    """Replica a logica de _diagnosticar_motivo do refresh, sobre uma linha
    crua de cluster_discrepancias. Devolve None se passou tudo.
    Converte tudo pra float pra evitar Decimal vs float em operacoes."""
    def f(v: Any) -> float | None:
        return None if v is None else float(v)

    n_cluster = row["n_cluster"]
    n_sujeito = row["n_sujeito"]
    vt = f(row["valor_total_sujeito"])
    spread = f(row["spread"])
    iqr_s = f(row["iqr_sujeito"])
    iqr_c = f(row["iqr_cluster"])
    comparab = f(row["comparab_proxy"])
    spread_min = float(cfg.get("spread_min", 0))

    if n_cluster < cfg.get("cluster_n_min", 0):
        return f"cluster pequeno (n={n_cluster} < {cfg.get('cluster_n_min')})"
    if n_sujeito < cfg.get("sujeito_n_min", 0):
        return f"poucos contratos no municipio (n={n_sujeito} < {cfg.get('sujeito_n_min')})"
    if vt is not None and vt < float(cfg.get("sujeito_valor_total_min", 0)):
        return f"volume baixo (R$ {vt:,.0f} < limiar)".replace(",", ".")
    if spread is not None and spread < spread_min:
        return f"spread {spread:.1f}x abaixo do limiar {spread_min}x"
    if iqr_s is not None and iqr_s < float(cfg.get("iqr_sujeito_min", 0)):
        return f"IQR sujeito muito baixo ({iqr_s:.1f}) — distribuicao homogenea, sem dispersao real"
    if iqr_s is not None and iqr_c is not None and iqr_s > float(cfg.get("iqr_relativo_max_k", 99)) * iqr_c:
        return f"IQR sujeito ({iqr_s:.1f}) muito acima do IQR cluster ({iqr_c:.1f}) — sujeito desproporcionalmente heterogeneo"
    if comparab is not None and comparab < float(cfg.get("comparab_min", 0)):
        return f"comparabilidade {comparab:.2f} abaixo do limiar {cfg.get('comparab_min')}"
    janelas_passadas = sum(
        1 for n_field, sp_field in [
            ("n_sujeito_90d", "spread_90d"),
            ("n_sujeito_180d", "spread_180d"),
            ("n_sujeito_365d", "spread_365d"),
        ]
        if (row.get(n_field) or 0) >= cfg.get("estabilidade_min_n_janela", 0)
        and row.get(sp_field) is not None
        and float(row[sp_field]) >= spread_min
    )
    if janelas_passadas < cfg.get("estabilidade_min_janelas", 0):
        return f"estabilidade {janelas_passadas}/3 janelas (limiar {cfg.get('estabilidade_min_janelas')})"
    return None


@app.get(
    "/manchetes/diagnostico",
    response_model=ManchteDiagnosticoOut,
    tags=["meta"],
)
def get_manchete_diagnostico(conn: ConnDep, cd_tce: str) -> ManchteDiagnosticoOut:
    """Busca reversa: para um municipio, mostra manchetes ativas E
    diagnostico de por que outras (cluster, municipio) nao viraram manchete.

    Fecha a cara do sistema: ninguem escapa do escrutinio por aleatoriedade.
    Toda combinacao avaliada e visivel — passou ou explica o motivo.
    """
    with conn.cursor() as cur:
        # Info do municipio
        cur.execute(
            "SELECT cd_tce, nome, populacao FROM analytics.municipio_pr WHERE cd_tce = %s",
            (cd_tce,),
        )
        mun = cur.fetchone()
        municipio_nome = mun["nome"] if mun else None
        populacao = mun["populacao"] if mun else None

        # Config ativa (ultima aplicada)
        cur.execute(
            """
            SELECT parametros_hash, config_json
            FROM analytics.manchete_config_aplicada
            ORDER BY ultima_aplicacao DESC LIMIT 1
            """
        )
        cfg_row = cur.fetchone()
        if not cfg_row:
            return ManchteDiagnosticoOut(
                cd_tce=cd_tce, municipio_nome=municipio_nome, populacao=populacao,
                parametros_hash=None, ativas=[], candidatos=[],
            )
        config = cfg_row["config_json"]
        parametros_hash = cfg_row["parametros_hash"]

        # Manchetes ativas onde aparece
        cur.execute(
            """
            SELECT
                rank_no_dia, cluster_id, cluster_version, cd_tce, cd_ibge,
                municipio_nome, porte, populacao, n_sujeito, valor_total_sujeito,
                med_sujeito, med_cluster, spread, iqr_sujeito, iqr_cluster,
                comparab_proxy, spread_90d, spread_180d, spread_365d,
                janelas_passadas, rank_score, parametros_hash,
                refresh_em::text AS refresh_em
            FROM analytics.manchete WHERE cd_tce = %s ORDER BY rank_no_dia
            """,
            (cd_tce,),
        )
        ativas = [ManchteOut(**r) for r in cur.fetchall()]
        ativas_ids = {(a.cluster_id, a.cd_tce) for a in ativas}

        # Todas as discrepancias (cluster, mun) avaliadas — diagnostica falha
        cur.execute(
            """
            SELECT cluster_id, n_cluster, n_sujeito, valor_total_sujeito,
                   spread, iqr_sujeito, iqr_cluster, comparab_proxy,
                   spread_90d, spread_180d, spread_365d,
                   n_sujeito_90d, n_sujeito_180d, n_sujeito_365d
            FROM analytics.cluster_discrepancias WHERE cd_tce = %s
            ORDER BY spread DESC NULLS LAST
            """,
            (cd_tce,),
        )
        candidatos: list[ManchteCandidatoDiagOut] = []
        for row in cur.fetchall():
            if (row["cluster_id"], cd_tce) in ativas_ids:
                continue  # ja na lista de ativas
            motivo = _diag_motivo_falha(row, config)
            candidatos.append(ManchteCandidatoDiagOut(
                cluster_id=row["cluster_id"],
                n_sujeito=row["n_sujeito"],
                spread=row["spread"],
                iqr_sujeito=row["iqr_sujeito"],
                comparab_proxy=row["comparab_proxy"],
                motivo_falha=motivo,
            ))

    return ManchteDiagnosticoOut(
        cd_tce=cd_tce, municipio_nome=municipio_nome, populacao=populacao,
        parametros_hash=parametros_hash, ativas=ativas, candidatos=candidatos,
    )


@app.get("/manchetes/saidas", response_model=list[ManchteSaidaOut], tags=["meta"])
def get_manchetes_saidas(
    conn: ConnDep,
    dias: int = Query(default=90, ge=1, le=365),
) -> list[ManchteSaidaOut]:
    """Manchetes que sairam nos ultimos N dias com motivo diagnostico.

    Cumpre o principio "vela apagada e tambem informacao" — credibilidade
    publica. Conhecer o que SAIU revela que o sistema e vivo e auto-corrige.
    """
    sql = """
        SELECT
            saiu_em::text AS saiu_em,
            manchete_id,
            motivo,
            payload_anterior->>'cluster_id'    AS cluster_id,
            payload_anterior->>'municipio_nome' AS municipio_nome,
            (payload_anterior->>'spread')::numeric AS spread_anterior,
            parametros_hash
        FROM analytics.manchete_saida
        WHERE saiu_em >= NOW() - (%s || ' days')::interval
        ORDER BY saiu_em DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql, (dias,))
        return [ManchteSaidaOut(**r) for r in cur.fetchall()]


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


# ----------------------------- Contrato (detalhe) ---------------------


@app.get(
    "/contrato/{raw_id}",
    response_model=ContratoDetalheOut,
    tags=["contrato"],
)
def contrato_detalhe(conn: ConnDep, raw_id: int) -> ContratoDetalheOut:
    """Detalhe de um contrato pela chave interna `raw_id` (raw.compras.id).

    Agrega: raw.compras + item_canonical + cluster_registry + snapshot +
    municipio_pr (so se source = tce_pr/contrato). raw_payload exposto
    completo para auditoria.

    LGPD art. 18 IV: se houver registro em analytics.eliminacao, retorna
    410 Gone com motivo publico (sem reproduzir o conteudo eliminado).
    """
    # Checa eliminacao primeiro — antes de gastar query no detalhe
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT eliminada_em::text AS eliminada_em, motivo, fundamento_legal
            FROM analytics.eliminacao WHERE raw_id = %s
            """,
            (raw_id,),
        )
        elim = cur.fetchone()
    if elim is not None:
        # 410 Gone e o codigo HTTP correto para "recurso existiu mas
        # foi removido permanentemente"
        raise HTTPException(
            status_code=410,
            detail={
                "raw_id": raw_id,
                "eliminada_em": elim["eliminada_em"],
                "motivo": elim["motivo"],
                "fundamento_legal": elim["fundamento_legal"],
                "info": (
                    "Conteudo removido a pedido do titular ou por base legal. "
                    "raw.snapshots preservados (auditoria); vitrine publica filtra. "
                    "Ver /eliminacoes/publicas pra lista agregada."
                ),
            },
        )
    sql = """
        SELECT
            rc.id AS raw_id,
            rc.source,
            rc.source_id,
            rc.source_url,
            rc.contract_date::text AS contract_date,
            rc.orgao_codigo,
            rc.orgao_nome,
            rc.fornecedor_cnpj,
            rc.fornecedor_nome,
            rc.descricao,
            rc.valor_total,
            rc.valor_unitario,
            rc.quantidade,
            rc.unidade,
            rc.modalidade,
            rc.catmat_id,
            rc.catser_id,
            rc.raw_payload,
            ic.cluster_id,
            ic.cluster_version,
            ic.metodo_resolucao,
            ic.confianca_resolucao,
            ic.em_quarentena,
            ic.motivo_quarentena,
            cr.descricao_canonica AS cluster_descricao,
            s.id AS snapshot_id,
            s.period_start::text AS snapshot_period_start,
            s.period_end::text AS snapshot_period_end,
            s.hash_sha256 AS snapshot_hash_sha256,
            s.ingested_at::text AS snapshot_ingested_at,
            mp.cd_ibge,
            COALESCE(mp.nome, rc.raw_payload->>'municipio') AS municipio_nome
        FROM raw.compras rc
        LEFT JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
        LEFT JOIN analytics.cluster_registry cr
            ON cr.cluster_id = ic.cluster_id AND cr.cluster_version = ic.cluster_version
        JOIN raw.snapshots s ON s.id = rc.snapshot_id
        LEFT JOIN analytics.municipio_pr mp
            ON mp.cd_tce = rc.raw_payload->>'cd_tce'
        WHERE rc.id = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (raw_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(404, f"contrato raw_id={raw_id} nao encontrado")
    # raw_payload pode vir como dict (psycopg) — garante
    payload = row["raw_payload"]
    if isinstance(payload, str):
        import json as _json
        payload = _json.loads(payload)
    return ContratoDetalheOut(
        raw_id=row["raw_id"],
        source=row["source"],
        source_id=row["source_id"],
        source_url=row["source_url"],
        contract_date=row["contract_date"],
        orgao_codigo=row["orgao_codigo"],
        orgao_nome=row["orgao_nome"],
        fornecedor_cnpj=row["fornecedor_cnpj"],
        fornecedor_nome=row["fornecedor_nome"],
        descricao=row["descricao"],
        valor_total=row["valor_total"],
        valor_unitario=row["valor_unitario"],
        quantidade=row["quantidade"],
        unidade=row["unidade"],
        modalidade=row["modalidade"],
        catmat_id=row["catmat_id"],
        catser_id=row["catser_id"],
        raw_payload=payload or {},
        cluster_id=row["cluster_id"],
        cluster_version=row["cluster_version"],
        cluster_descricao=row["cluster_descricao"],
        metodo_resolucao=row["metodo_resolucao"],
        confianca_resolucao=(
            float(row["confianca_resolucao"]) if row["confianca_resolucao"] is not None else None
        ),
        em_quarentena=row["em_quarentena"] or False,
        motivo_quarentena=row["motivo_quarentena"],
        snapshot_id=row["snapshot_id"],
        snapshot_period_start=row["snapshot_period_start"],
        snapshot_period_end=row["snapshot_period_end"],
        snapshot_hash_sha256=row["snapshot_hash_sha256"],
        snapshot_ingested_at=row["snapshot_ingested_at"],
        cd_ibge=row["cd_ibge"],
        municipio_nome=row["municipio_nome"],
    )


# ----------------------------- Instituicoes (busca unica) -------------


@app.get(
    "/instituicoes/search",
    response_model=InstituicoesSearchOut,
    tags=["meta"],
)
def instituicoes_search(
    conn: ConnDep,
    q: str = Query(..., min_length=2, description="Termo de busca (>= 2 chars)"),
    limit: int = Query(default=20, ge=1, le=50, description="Por seção"),
) -> InstituicoesSearchOut:
    """Busca instituicoes em 3 contextos simultaneos:
      1. Fornecedores (quem recebeu) — agrupa por (cnpj, nome)
      2. Orgaos contratantes (quem comprou) — agrupa por orgao + municipio
      3. Termos no objeto (ex: UPA, escola, hospital) — agrupa por
         (municipio, orgao) os contratos cujo dsObjeto menciona o termo.

    Retorna top N de cada um + contagens totais. Cada item linka pra
    pagina canonica (/fornecedor, /municipio, /contratos).
    """
    like = f"%{q}%"

    # 1. FORNECEDORES — busca em fornecedor_nome
    sql_forn = """
        SELECT
            rc.fornecedor_cnpj,
            MAX(rc.fornecedor_nome) AS fornecedor_nome,
            COUNT(*) AS n_contratos,
            ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total,
            COUNT(DISTINCT rc.raw_payload->>'cd_tce') AS n_municipios
        FROM raw.compras rc
        WHERE rc.fornecedor_cnpj IS NOT NULL
          AND rc.fornecedor_nome ILIKE %s
        GROUP BY rc.fornecedor_cnpj
        ORDER BY valor_total DESC NULLS LAST
        LIMIT %s
    """
    sql_forn_count = """
        SELECT COUNT(DISTINCT rc.fornecedor_cnpj) AS n
        FROM raw.compras rc
        WHERE rc.fornecedor_cnpj IS NOT NULL AND rc.fornecedor_nome ILIKE %s
    """

    # 2. ORGAOS — busca em orgao_nome
    sql_orgao = """
        SELECT
            rc.orgao_codigo,
            MAX(rc.orgao_nome) AS orgao_nome,
            rc.raw_payload->>'cd_tce' AS cd_tce,
            mp.cd_ibge,
            COALESCE(mp.nome, rc.raw_payload->>'municipio') AS municipio,
            COUNT(*) AS n_contratos,
            ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total
        FROM raw.compras rc
        LEFT JOIN analytics.municipio_pr mp ON mp.cd_tce = rc.raw_payload->>'cd_tce'
        WHERE rc.orgao_nome ILIKE %s
        GROUP BY rc.orgao_codigo, rc.raw_payload->>'cd_tce', mp.cd_ibge, mp.nome,
                 rc.raw_payload->>'municipio'
        ORDER BY valor_total DESC NULLS LAST
        LIMIT %s
    """
    sql_orgao_count = """
        SELECT COUNT(DISTINCT rc.orgao_codigo) AS n
        FROM raw.compras rc WHERE rc.orgao_nome ILIKE %s
    """

    # 3. OBJETO — agrupa por (municipio, orgao)
    sql_obj = """
        SELECT
            rc.raw_payload->>'cd_tce' AS cd_tce,
            mp.cd_ibge,
            COALESCE(mp.nome, rc.raw_payload->>'municipio') AS municipio,
            rc.orgao_codigo,
            MAX(rc.orgao_nome) AS orgao_nome,
            COUNT(*) AS n_contratos,
            ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total
        FROM raw.compras rc
        LEFT JOIN analytics.municipio_pr mp ON mp.cd_tce = rc.raw_payload->>'cd_tce'
        WHERE rc.descricao ILIKE %s
        GROUP BY rc.raw_payload->>'cd_tce', mp.cd_ibge, mp.nome,
                 rc.raw_payload->>'municipio', rc.orgao_codigo
        ORDER BY valor_total DESC NULLS LAST
        LIMIT %s
    """
    sql_obj_count = """
        SELECT COUNT(*) AS n_contratos,
               COALESCE(SUM(valor_total), 0) AS valor
        FROM raw.compras WHERE descricao ILIKE %s
    """

    # 4. FORNECEDORES NO OBJETO — agrega por (fornecedor) os contratos
    # cujo objeto menciona o termo. Resposta a "quem foi pago por
    # entregar à UPA Centro?".
    sql_forn_obj = """
        SELECT
            rc.fornecedor_cnpj,
            MAX(rc.fornecedor_nome) AS fornecedor_nome,
            COUNT(*) AS n_contratos,
            ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total,
            COUNT(DISTINCT rc.raw_payload->>'cd_tce') AS n_municipios
        FROM raw.compras rc
        WHERE rc.descricao ILIKE %s
          AND rc.fornecedor_cnpj IS NOT NULL
        GROUP BY rc.fornecedor_cnpj
        ORDER BY valor_total DESC NULLS LAST
        LIMIT %s
    """
    sql_forn_obj_count = """
        SELECT COUNT(DISTINCT rc.fornecedor_cnpj) AS n
        FROM raw.compras rc
        WHERE rc.descricao ILIKE %s AND rc.fornecedor_cnpj IS NOT NULL
    """

    with conn.cursor() as cur:
        cur.execute(sql_forn, (like, limit))
        fornecedores = [InstituicaoFornecedorOut(**r) for r in cur.fetchall()]
        cur.execute(sql_forn_count, (like,))
        n_forn = cur.fetchone()["n"]

        cur.execute(sql_orgao, (like, limit))
        orgaos = [InstituicaoOrgaoOut(**r) for r in cur.fetchall()]
        cur.execute(sql_orgao_count, (like,))
        n_orgao = cur.fetchone()["n"]

        cur.execute(sql_obj, (like, limit))
        objetos = [InstituicaoObjetoOut(**r) for r in cur.fetchall()]
        cur.execute(sql_obj_count, (like,))
        obj_count = cur.fetchone()

        cur.execute(sql_forn_obj, (like, limit))
        forn_obj = [InstituicaoFornecedorObjetoOut(**r) for r in cur.fetchall()]
        cur.execute(sql_forn_obj_count, (like,))
        n_forn_obj = cur.fetchone()["n"]

    return InstituicoesSearchOut(
        q=q,
        fornecedores=fornecedores,
        orgaos=orgaos,
        objetos=objetos,
        fornecedores_no_objeto=forn_obj,
        total_fornecedores=n_forn or 0,
        total_orgaos=n_orgao or 0,
        total_objeto_contratos=obj_count["n_contratos"] or 0,
        total_fornecedores_no_objeto=n_forn_obj or 0,
        valor_total_objeto=obj_count["valor"] or Decimal(0),
    )


# ----------------------------- Contratos search (drill-down) ----------


@app.get(
    "/contratos/search",
    response_model=ContratoSearchPageOut,
    tags=["contrato"],
)
def contratos_search(
    conn: ConnDep,
    cluster_id: str | None = Query(default=None),
    cd_tce: str | None = Query(default=None, description="Codigo TCE-PR (6 dig.)"),
    cd_ibge: str | None = Query(default=None, description="Codigo IBGE (7 dig.)"),
    modalidade: str | None = Query(default=None, description="'sem_modalidade' = nao resolvida"),
    fornecedor_cnpj: str | None = Query(default=None),
    orgao_codigo: str | None = Query(default=None),
    escola_slug: str | None = Query(default=None),
    source: str | None = Query(default=None, description="ex: tce_pr/contrato"),
    em_quarentena: bool | None = Query(
        default=None, description="None=ambos; True/False filtra"
    ),
    q: str | None = Query(
        default=None,
        description="Busca textual livre em descricao OU fornecedor_nome OU orgao_nome (ILIKE %q% case-insensitive). Cobre 'UPA Centro' (objeto), 'Atlantica Construcoes' (fornecedor), 'Funcao Estatal de Atencao' (orgao).",
    ),
    since: date | None = Query(default=None, description="contract_date >= YYYY-MM-DD"),
    until: date | None = Query(default=None, description="contract_date <= YYYY-MM-DD"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    order: Literal["valor_desc", "valor_asc", "data_desc", "data_asc"] = Query(
        default="valor_desc",
        description="valor_desc | valor_asc | data_desc | data_asc",
    ),
) -> ContratoSearchPageOut:
    """Busca paginada e filtrada de contratos. Drill-down universal —
    cada filtro corresponde a um agregado em outras paginas.

    Implementacao: monta WHERE dinamicamente com AND. Conta total e
    soma valor_total na mesma query (CTE).
    """
    # Resolve cd_ibge para cd_tce se necessario
    if cd_ibge and not cd_tce:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT cd_tce FROM analytics.municipio_pr WHERE cd_ibge = %s",
                (cd_ibge,),
            )
            row = cur.fetchone()
            if row:
                cd_tce = row["cd_tce"]

    where = ["1 = 1"]
    args: list[Any] = []
    if source:
        where.append("rc.source = %s")
        args.append(source)
    if cluster_id:
        where.append("ic.cluster_id = %s")
        args.append(cluster_id)
    if cd_tce:
        where.append("rc.raw_payload->>'cd_tce' = %s")
        args.append(cd_tce)
    if modalidade:
        if modalidade == "sem_modalidade":
            where.append("rc.modalidade IS NULL")
        else:
            where.append("rc.modalidade = %s")
            args.append(modalidade)
    if fornecedor_cnpj:
        where.append("rc.fornecedor_cnpj = %s")
        args.append(fornecedor_cnpj)
    if orgao_codigo:
        where.append("rc.orgao_codigo = %s")
        args.append(orgao_codigo)
    if escola_slug:
        where.append(
            "rc.id IN (SELECT raw_id FROM analytics.escola_mencao WHERE escola_slug = %s)"
        )
        args.append(escola_slug)
    if em_quarentena is not None:
        where.append("ic.em_quarentena = %s")
        args.append(em_quarentena)
    if since:
        where.append("rc.contract_date >= %s::date")
        args.append(since)
    if until:
        where.append("rc.contract_date <= %s::date")
        args.append(until)
    if q:
        # ILIKE em 3 campos: objeto + fornecedor + orgao. ORs no mesmo
        # AND-block do WHERE; substring em ambos os lados, case-insensitive.
        where.append(
            "(rc.descricao ILIKE %s "
            "OR rc.fornecedor_nome ILIKE %s "
            "OR rc.orgao_nome ILIKE %s)"
        )
        like = f"%{q}%"
        args.extend([like, like, like])

    where_sql = " AND ".join(where)

    order_sql = {
        "valor_desc": "rc.valor_total DESC NULLS LAST",
        "valor_asc": "rc.valor_total ASC NULLS LAST",
        "data_desc": "rc.contract_date DESC NULLS LAST",
        "data_asc": "rc.contract_date ASC NULLS LAST",
    }[order]

    # Conta total + soma — uma query so
    sql_total = f"""
        SELECT COUNT(*) AS total,
               COALESCE(SUM(rc.valor_total), 0) AS valor_total
        FROM raw.compras rc
        LEFT JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
        WHERE {where_sql}
    """
    with conn.cursor() as cur:
        cur.execute(sql_total, args)
        agg = cur.fetchone()

    offset = (page - 1) * limit
    sql_items = f"""
        SELECT
            rc.id AS raw_id,
            rc.source_id,
            COALESCE(mp.nome, rc.raw_payload->>'municipio') AS municipio,
            rc.raw_payload->>'cd_tce' AS cd_tce,
            rc.orgao_nome,
            rc.fornecedor_cnpj,
            rc.fornecedor_nome,
            rc.descricao,
            rc.valor_total,
            rc.contract_date::text AS contract_date,
            ic.cluster_id,
            cr.descricao_canonica AS cluster_descricao,
            rc.modalidade,
            COALESCE(ic.em_quarentena, FALSE) AS em_quarentena
        FROM raw.compras rc
        LEFT JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
        LEFT JOIN analytics.cluster_registry cr
            ON cr.cluster_id = ic.cluster_id AND cr.cluster_version = ic.cluster_version
        LEFT JOIN analytics.municipio_pr mp ON mp.cd_tce = rc.raw_payload->>'cd_tce'
        WHERE {where_sql}
        ORDER BY {order_sql}
        LIMIT %s OFFSET %s
    """
    with conn.cursor() as cur:
        cur.execute(sql_items, [*args, limit, offset])
        rows = cur.fetchall()

    return ContratoSearchPageOut(
        page=page,
        limit=limit,
        total=agg["total"] or 0,
        valor_total_filtrado=agg["valor_total"] or Decimal(0),
        contratos=[ContratoSearchItemOut(**r) for r in rows],
    )


# ----------------------------- Dispensas (gancho viral) ---------------


@app.get(
    "/tce-pr/dispensas/top-fornecedores",
    response_model=list[DispensaTopFornecedorOut],
    tags=["tce-pr"],
)
def dispensas_top_fornecedores(
    conn: ConnDep,
    incluir_cpf_mascarado: bool = Query(
        default=False,
        description="Inclui pessoas fisicas (CPFs mascarados pelo TCE-PR; multiplas pessoas colidem no mesmo CNPJ-***).",
    ),
    min_contratos: int = Query(default=2, ge=1, description="Threshold minimo"),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[DispensaTopFornecedorOut]:
    """Top fornecedores em contratos de modalidade dispensa no PR.

    Linguagem factual estrita: dispensa NAO implica irregularidade —
    Lei 14.133/2021 prevê dispensa para emergencia, valor baixo,
    fornecedor exclusivo, etc. Presenca alta aqui e ponto de partida
    para investigacao, nao prova de nada.

    Threshold default = 2 (vs 5 da pagina /fornecedor) — listagem,
    nao perfil; aceita visibilidade maior porque a UI ja traz disclaimer
    forte e nao linka pra perfil quando < 5.
    """
    sql = """
        SELECT
            rc.fornecedor_cnpj,
            MAX(rc.fornecedor_nome) AS fornecedor_nome,
            COUNT(*) AS n_dispensas,
            ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total_dispensas,
            COUNT(DISTINCT rc.raw_payload->>'cd_tce') AS n_municipios,
            COUNT(DISTINCT rc.orgao_codigo) AS n_orgaos
        FROM raw.compras rc
        WHERE rc.source = 'tce_pr/contrato'
          AND rc.modalidade = 'dispensa'
          AND rc.fornecedor_cnpj IS NOT NULL
          AND (%s::boolean OR rc.fornecedor_cnpj NOT LIKE '%%*%%')
        GROUP BY rc.fornecedor_cnpj
        HAVING COUNT(*) >= %s
        ORDER BY valor_total_dispensas DESC NULLS LAST
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (incluir_cpf_mascarado, min_contratos, limit))
        rows = cur.fetchall()
    return [
        DispensaTopFornecedorOut(
            fornecedor_cnpj=r["fornecedor_cnpj"],
            fornecedor_nome=r["fornecedor_nome"],
            n_dispensas=r["n_dispensas"],
            valor_total_dispensas=r["valor_total_dispensas"],
            n_municipios=r["n_municipios"],
            n_orgaos=r["n_orgaos"],
            cnpj_mascarado="*" in r["fornecedor_cnpj"],
        )
        for r in rows
    ]


# ----------------------------- Stats PR (home) ------------------------


@app.get("/stats/pr", response_model=StatsPrOut, tags=["meta"])
def stats_pr(conn: ConnDep) -> StatsPrOut:
    """Agregados em vivo do pipeline TCE-PR — alimenta a home sem
    hardcode. Usa um único conn pra evitar N round-trips.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) AS total_contratos,
                COUNT(DISTINCT raw_payload->>'cd_tce') AS total_municipios,
                ROUND(SUM(valor_total)::numeric, 2) AS valor_total
            FROM raw.compras
            WHERE source = 'tce_pr/contrato'
            """
        )
        agg = cur.fetchone()
        # Fornecedores: contagem (cnpj, nome) distinta — alinha com a mart
        # mart_fornecedores_municipio (CPFs mascarados pelo TCE-PR colidem
        # no mesmo cnpj entre pessoas fisicas distintas; nome desambigua).
        cur.execute(
            """
            SELECT COUNT(*) AS n
            FROM (
                SELECT DISTINCT fornecedor_cnpj, fornecedor_nome
                FROM raw.compras
                WHERE source = 'tce_pr/contrato' AND fornecedor_cnpj IS NOT NULL
            ) sub
            """
        )
        n_fornecedores = cur.fetchone()["n"]

        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE em_quarentena = FALSE) AS n_cluster,
                COUNT(*) FILTER (WHERE em_quarentena = TRUE)  AS n_quarentena
            FROM analytics.item_canonical ic
            JOIN raw.compras rc ON rc.id = ic.raw_id
            WHERE rc.source = 'tce_pr/contrato'
            """
        )
        cobertura = cur.fetchone()

        cur.execute(
            """
            SELECT COALESCE(modalidade, 'sem_modalidade') AS modalidade,
                   COUNT(*) AS n
            FROM raw.compras
            WHERE source = 'tce_pr/contrato'
            GROUP BY 1
            ORDER BY n DESC
            """
        )
        modalidades = [
            StatsPrModalidadeOut(modalidade=r["modalidade"], n_contratos=r["n"])
            for r in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT ic.cluster_id,
                   cr.descricao_canonica,
                   COUNT(*) AS n
            FROM analytics.item_canonical ic
            JOIN raw.compras rc ON rc.id = ic.raw_id
            LEFT JOIN analytics.cluster_registry cr
                ON cr.cluster_id = ic.cluster_id
               AND cr.cluster_version = ic.cluster_version
            WHERE rc.source = 'tce_pr/contrato'
              AND ic.em_quarentena = FALSE
            GROUP BY 1, 2
            ORDER BY n DESC
            LIMIT 5
            """
        )
        top_clusters = [
            StatsPrTopClusterOut(
                cluster_id=r["cluster_id"],
                descricao_canonica=r["descricao_canonica"],
                n_contratos=r["n"],
            )
            for r in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT MAX(ingested_at)::text AS last
            FROM raw.snapshots
            WHERE source = 'tce_pr/contrato' AND status = 'completed'
            """
        )
        last = cur.fetchone()["last"]

        cur.execute(
            "SELECT COUNT(DISTINCT escola_slug) AS n FROM analytics.escola_mencao"
        )
        n_escolas = cur.fetchone()["n"]

    n_cluster = cobertura["n_cluster"] or 0
    n_quarentena = cobertura["n_quarentena"] or 0
    total_canon = n_cluster + n_quarentena
    cobertura_pct = round(n_cluster / total_canon, 4) if total_canon else 0.0

    return StatsPrOut(
        total_contratos=agg["total_contratos"] or 0,
        total_municipios=agg["total_municipios"] or 0,
        total_fornecedores=n_fornecedores or 0,
        n_em_cluster=n_cluster,
        n_em_quarentena=n_quarentena,
        cobertura_cluster_pct=cobertura_pct,
        valor_total_pr=agg["valor_total"],
        modalidades=modalidades,
        top_clusters=top_clusters,
        last_snapshot_at=last,
        n_escolas_catalogadas=n_escolas or 0,
    )


# ----------------------------- Escolas (catalogo) ---------------------

# Catalogo de obras escolares: ~270-1000 mencoes de escola individual
# extraidas via regex em src/analytics/escolas.py. Cobertura geral ~0.17%
# do raw.compras — feature de catalogo de transparencia, NAO ranking
# (volume baixo demais para comparacao estatistica). Concentrado em
# obras_edificacao (29% do cluster).


@app.get(
    "/escolas",
    response_model=list[EscolaListItemOut],
    tags=["escolas"],
)
def list_escolas(
    conn: ConnDep,
    search: str | None = Query(default=None, description="Filtra por nome (case-insensitive)"),
    cd_tce: str | None = Query(default=None, description="Filtra por municipio (cd_tce)"),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[EscolaListItemOut]:
    """Lista escolas detectadas, ordenadas por numero de mencoes."""
    sql = """
        SELECT
            em.escola_slug,
            (
                SELECT em2.escola_nome FROM analytics.escola_mencao em2
                WHERE em2.escola_slug = em.escola_slug
                ORDER BY length(em2.escola_nome) ASC LIMIT 1
            ) AS escola_nome,
            COUNT(*) AS n_mencoes,
            COUNT(DISTINCT em.cd_tce) AS n_municipios,
            ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total
        FROM analytics.escola_mencao em
        JOIN raw.compras rc ON rc.id = em.raw_id
        WHERE (%s::text IS NULL OR lower(em.escola_nome) LIKE '%%' || lower(%s) || '%%')
          AND (%s::text IS NULL OR em.cd_tce = %s)
        GROUP BY em.escola_slug
        ORDER BY n_mencoes DESC, valor_total DESC NULLS LAST
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (search, search, cd_tce, cd_tce, limit))
        return [EscolaListItemOut(**r) for r in cur.fetchall()]


@app.get(
    "/escolas/{slug}/contratos",
    response_model=list[EscolaContratoOut],
    tags=["escolas"],
)
def escola_contratos(
    conn: ConnDep, slug: str, limit: int = Query(default=50, ge=1, le=200)
) -> list[EscolaContratoOut]:
    """Contratos vinculados a uma escola pelo slug. Ordem: maior valor primeiro."""
    sql = """
        SELECT
            rc.id AS raw_id,
            rc.source_id AS contrato_id,
            COALESCE(mp.nome, rc.raw_payload->>'municipio') AS municipio,
            em.cd_tce,
            rc.orgao_nome,
            rc.descricao,
            rc.valor_total,
            rc.contract_date::text AS contract_date,
            ic.cluster_id,
            em.padrao,
            em.escola_nome
        FROM analytics.escola_mencao em
        JOIN raw.compras rc ON rc.id = em.raw_id
        LEFT JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
        LEFT JOIN analytics.municipio_pr mp ON mp.cd_tce = em.cd_tce
        WHERE em.escola_slug = %s
        ORDER BY rc.valor_total DESC NULLS LAST, rc.contract_date DESC NULLS LAST
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (slug, limit))
        rows = cur.fetchall()
    if not rows:
        raise HTTPException(404, f"escola '{slug}' nao encontrada")
    return [EscolaContratoOut(**r) for r in rows]


# ----------------------------- Listings ------------------------------


@app.get(
    "/municipios",
    response_model=list[MunicipioListItemOut],
    tags=["municipio"],
)
def list_municipios(
    conn: ConnDep,
    search: str | None = Query(default=None, description="Filtra por nome (case-insensitive, sem acento)"),
    limit: int = Query(default=50, ge=1, le=399),
) -> list[MunicipioListItemOut]:
    """Lista municipios PR com contratos no banco (TCE-PR). Sem search,
    devolve top N por numero de contratos. Com search, filtra por nome."""
    sql = """
        SELECT
            COALESCE(mp.cd_tce, rc.raw_payload->>'cd_tce') AS cd_tce,
            mp.cd_ibge AS cd_ibge,
            COALESCE(mp.nome, rc.raw_payload->>'municipio') AS nome,
            COALESCE(mp.porte, 'municipio_pr_pequeno') AS porte,
            (mp.cd_tce IS NOT NULL) AS catalogado,
            COUNT(*) AS n_contratos,
            ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total
        FROM raw.compras rc
        LEFT JOIN analytics.municipio_pr mp ON mp.cd_tce = rc.raw_payload->>'cd_tce'
        WHERE rc.source = 'tce_pr/contrato'
          AND (
              %s::text IS NULL
              OR unaccent(lower(COALESCE(mp.nome, rc.raw_payload->>'municipio')))
                  LIKE '%%' || unaccent(lower(%s)) || '%%'
          )
        GROUP BY 1, 2, 3, 4, 5
        ORDER BY n_contratos DESC
        LIMIT %s
    """
    # unaccent extension may not be installed; fallback graceful
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (search, search, limit))
            return [MunicipioListItemOut(**r) for r in cur.fetchall()]
    except psycopg.errors.UndefinedFunction:
        conn.rollback()
        # fallback sem unaccent: case-insensitive simples
        sql_fb = sql.replace("unaccent(lower(", "lower(").replace(")) LIKE", ") LIKE").replace(") || '%%'", ") || '%%'")
        # mais simples: refazer
        sql_fb = """
            SELECT
                COALESCE(mp.cd_tce, rc.raw_payload->>'cd_tce') AS cd_tce,
                mp.cd_ibge AS cd_ibge,
                COALESCE(mp.nome, rc.raw_payload->>'municipio') AS nome,
                COALESCE(mp.porte, 'municipio_pr_pequeno') AS porte,
                (mp.cd_tce IS NOT NULL) AS catalogado,
                COUNT(*) AS n_contratos,
                ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total
            FROM raw.compras rc
            LEFT JOIN analytics.municipio_pr mp ON mp.cd_tce = rc.raw_payload->>'cd_tce'
            WHERE rc.source = 'tce_pr/contrato'
              AND (
                  %s::text IS NULL
                  OR lower(COALESCE(mp.nome, rc.raw_payload->>'municipio'))
                      LIKE '%%' || lower(%s) || '%%'
              )
            GROUP BY 1, 2, 3, 4, 5
            ORDER BY n_contratos DESC
            LIMIT %s
        """
        with conn.cursor() as cur:
            cur.execute(sql_fb, (search, search, limit))
            return [MunicipioListItemOut(**r) for r in cur.fetchall()]


@app.get(
    "/fornecedores",
    response_model=list[FornecedorListItemOut],
    tags=["fornecedor"],
)
def list_fornecedores(
    conn: ConnDep,
    search: str | None = Query(default=None, description="Filtra por nome ou CNPJ (case-insensitive)"),
    min_contratos: int = Query(
        default=_FORNECEDOR_THRESHOLD,
        ge=1,
        description="Filtra fornecedores com pelo menos N contratos (default = threshold da pagina de perfil)",
    ),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[FornecedorListItemOut]:
    """Lista fornecedores com contratos no banco. Default = top por volume,
    threshold de 5 contratos (alinhado com a pagina /fornecedor/[cnpj])."""
    # LGPD L.2.b: listagem so devolve PJ confirmado. JOIN com
    # analytics.fornecedor filtra MEI/EI/PF e nao-classificados.
    sql = """
        SELECT
            rc.fornecedor_cnpj,
            MAX(rc.fornecedor_nome) AS fornecedor_nome,
            COUNT(*) AS n_contratos,
            ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total,
            COUNT(DISTINCT rc.raw_payload->>'cd_tce') AS n_municipios_distintos
        FROM raw.compras rc
        JOIN analytics.fornecedor f ON f.cnpj = rc.fornecedor_cnpj
        WHERE rc.fornecedor_cnpj IS NOT NULL
          AND f.tipo_juridico = 'PJ'
          AND (
              %s::text IS NULL
              OR lower(rc.fornecedor_nome) LIKE '%%' || lower(%s) || '%%'
              OR rc.fornecedor_cnpj LIKE '%%' || %s || '%%'
          )
        GROUP BY rc.fornecedor_cnpj
        HAVING COUNT(*) >= %s
        ORDER BY valor_total DESC NULLS LAST
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (search, search, search, min_contratos, limit))
        return [FornecedorListItemOut(**r) for r in cur.fetchall()]


@app.get(
    "/fornecedores.csv",
    response_class=Response,
    tags=["fornecedor"],
    summary="Listagem de fornecedores PJ em CSV (PLANO §19.3)",
)
def list_fornecedores_csv(
    conn: ConnDep,
    search: str | None = Query(default=None),
    min_contratos: int = Query(default=_FORNECEDOR_THRESHOLD, ge=1),
    limit: int = Query(default=500, ge=1, le=5000),
) -> Response:
    """Mesma query de /fornecedores em CSV pra uso jornalistico (CC-BY 4.0).
    Limit default mais alto (500) ja que e download."""
    sql = """
        SELECT
            rc.fornecedor_cnpj,
            MAX(rc.fornecedor_nome) AS fornecedor_nome,
            COUNT(*) AS n_contratos,
            ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total,
            COUNT(DISTINCT rc.raw_payload->>'cd_tce') AS n_municipios_distintos
        FROM raw.compras rc
        JOIN analytics.fornecedor f ON f.cnpj = rc.fornecedor_cnpj
        WHERE rc.fornecedor_cnpj IS NOT NULL
          AND f.tipo_juridico = 'PJ'
          AND (
              %s::text IS NULL
              OR lower(rc.fornecedor_nome) LIKE '%%' || lower(%s) || '%%'
              OR rc.fornecedor_cnpj LIKE '%%' || %s || '%%'
          )
        GROUP BY rc.fornecedor_cnpj
        HAVING COUNT(*) >= %s
        ORDER BY valor_total DESC NULLS LAST
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (search, search, search, min_contratos, limit))
        rows = cur.fetchall()
    return _rows_to_csv_response(
        rows,
        fieldnames=[
            "fornecedor_cnpj", "fornecedor_nome", "n_contratos",
            "valor_total", "n_municipios_distintos",
        ],
        filename="fornecedores_quantopagou.csv",
    )


# ----------------------------- Municipio (resolver) -------------------


@app.get("/municipio/{key}/info", response_model=MunicipioInfoOut, tags=["municipio"])
def municipio_info(conn: ConnDep, key: str) -> MunicipioInfoOut:
    """Resolve cd_tce ou cd_ibge para info canonica do municipio.

    Aceita 6 digitos (cd_tce) ou 7 digitos (cd_ibge). Para municipios fora
    da tabela analytics.municipio_pr, busca no raw.compras (TCE-PR) e
    devolve nome inferido + porte=municipio_pr_pequeno (default).
    """
    if not key.isdigit() or len(key) not in (6, 7):
        raise HTTPException(400, "key deve ter 6 (cd_tce) ou 7 (cd_ibge) digitos")
    is_tce = len(key) == 6
    sql_cat = """
        SELECT cd_tce, cd_ibge, nome, porte
        FROM analytics.municipio_pr
        WHERE (%s::boolean AND cd_tce = %s) OR (NOT %s::boolean AND cd_ibge = %s)
    """
    with conn.cursor() as cur:
        cur.execute(sql_cat, (is_tce, key, is_tce, key))
        row = cur.fetchone()
    if row:
        return MunicipioInfoOut(
            cd_tce=row["cd_tce"],
            cd_ibge=row["cd_ibge"],
            nome=row["nome"],
            porte=row["porte"],
            catalogado=True,
        )
    # Nao catalogado — busca em raw.compras pelo cd_tce (so funciona se for cd_tce)
    if not is_tce:
        raise HTTPException(404, f"municipio cd_ibge={key} nao catalogado e nao posso inferir cd_tce")
    sql_raw = """
        SELECT raw_payload->>'cd_tce' AS cd_tce,
               MAX(raw_payload->>'municipio') AS nome
        FROM raw.compras
        WHERE source = 'tce_pr/contrato'
          AND raw_payload->>'cd_tce' = %s
        GROUP BY 1
        LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(sql_raw, (key,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(404, f"municipio cd_tce={key} nao encontrado")
    return MunicipioInfoOut(
        cd_tce=row["cd_tce"],
        cd_ibge=None,
        nome=row["nome"] or "—",
        porte="municipio_pr_pequeno",
        catalogado=False,
    )


# ----------------------------- Fornecedor -----------------------------

# Guardrails do plano §6.5: threshold mínimo de 5 contratos, sem ranking
# implícito ("pior"), linguagem factual estrita. noindex/nofollow é
# imposto no frontend (meta tag). _FORNECEDOR_THRESHOLD definido no topo
# do modulo para reuso na listagem.
#
# LGPD L.2 (default deny): _require_pj_or_404 garante que todos os
# endpoints derivados (/por-orgao, /por-municipio, /por-categoria,
# /por-modalidade, /contratos) so respondem para PJ confirmado. Sem
# isso, quem souber o CNPJ raw poderia pular o gate do perfil principal.


def _require_pj_or_404(conn, cnpj: str) -> None:
    """Verifica em analytics.fornecedor que o CNPJ esta classificado
    como pessoa juridica (LGPD L.2). MEI/EI/PF e nao-classificados (NULL)
    sao bloqueados com 404. Use antes da query principal em qualquer
    endpoint que aceite cnpj como path/query."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT tipo_juridico FROM analytics.fornecedor WHERE cnpj = %s",
            (cnpj,),
        )
        row = cur.fetchone()
    if row is None or row.get("tipo_juridico") != "PJ":
        raise HTTPException(
            404,
            "perfil público indisponível: tipo jurídico não confirmado como pessoa jurídica "
            "(defesa LGPD para MEI/EI/PF). Solicite verificação em /correcoes.",
        )


@app.get("/fornecedor/{cnpj}", response_model=FornecedorPerfilOut, tags=["fornecedor"])
def fornecedor_perfil(conn: ConnDep, cnpj: str) -> FornecedorPerfilOut:
    """Resumo do fornecedor. Threshold >= 5 contratos para gerar página
    (filtra fornecedores eventuais, reduz risco de exposição injusta)."""
    cnpj_normalizado = "".join(ch for ch in cnpj if ch.isdigit() or ch == "*")
    if not cnpj_normalizado:
        raise HTTPException(400, "cnpj inválido")
    sql = """
        SELECT
            rc.fornecedor_cnpj,
            MAX(rc.fornecedor_nome) AS fornecedor_nome,
            COUNT(*) AS n_contratos_total,
            SUM(rc.valor_total) AS valor_total,
            COUNT(DISTINCT rc.orgao_codigo) AS n_orgaos_distintos,
            COUNT(DISTINCT rc.raw_payload->>'cd_tce') AS n_municipios_distintos,
            MIN(rc.contract_date)::text AS primeiro_contrato,
            MAX(rc.contract_date)::text AS ultimo_contrato,
            MAX(f.tipo_juridico) AS tipo_juridico,
            MAX(f.fonte) AS classificacao_fonte
        FROM raw.compras rc
        LEFT JOIN analytics.fornecedor f ON f.cnpj = rc.fornecedor_cnpj
        WHERE rc.fornecedor_cnpj = %s
        GROUP BY rc.fornecedor_cnpj
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cnpj_normalizado,))
        row = cur.fetchone()
    if row is None or row["n_contratos_total"] < _FORNECEDOR_THRESHOLD:
        raise HTTPException(
            404,
            f"fornecedor {cnpj_normalizado} sem perfil público (mínimo {_FORNECEDOR_THRESHOLD} contratos)",
        )
    # LGPD L.2 — default deny: so PJ confirmado tem perfil publico.
    # tipo_juridico NULL ou != 'PJ' = potencial MEI/EI/PF, dado pessoal.
    if row.get("tipo_juridico") != "PJ":
        raise HTTPException(
            404,
            "perfil público indisponível: tipo jurídico não confirmado como pessoa jurídica "
            "(defesa LGPD para MEI/EI/PF). Solicite verificação em /correcoes.",
        )
    return FornecedorPerfilOut(
        fornecedor_cnpj=row["fornecedor_cnpj"],
        fornecedor_nome=row["fornecedor_nome"],
        n_contratos_total=row["n_contratos_total"],
        valor_total=row["valor_total"] or Decimal(0),
        n_orgaos_distintos=row["n_orgaos_distintos"],
        n_municipios_distintos=row["n_municipios_distintos"],
        primeiro_contrato=row["primeiro_contrato"],
        ultimo_contrato=row["ultimo_contrato"],
        cnpj_mascarado="*" in row["fornecedor_cnpj"],
    )


@app.get(
    "/fornecedor/{cnpj}/por-orgao",
    response_model=list[FornecedorAgregadoOut],
    tags=["fornecedor"],
)
def fornecedor_por_orgao(
    conn: ConnDep, cnpj: str, limit: int = Query(default=15, ge=1, le=100)
) -> list[FornecedorAgregadoOut]:
    _require_pj_or_404(conn, cnpj)
    sql = """
        SELECT
            rc.orgao_codigo AS chave,
            MAX(rc.orgao_nome) AS nome,
            COUNT(*) AS n_contratos,
            ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total
        FROM raw.compras rc
        WHERE rc.fornecedor_cnpj = %s
        GROUP BY 1
        ORDER BY valor_total DESC NULLS LAST
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cnpj, limit))
        return [FornecedorAgregadoOut(**r) for r in cur.fetchall()]


@app.get(
    "/fornecedor/{cnpj}/por-municipio",
    response_model=list[FornecedorAgregadoOut],
    tags=["fornecedor"],
)
def fornecedor_por_municipio(
    conn: ConnDep, cnpj: str, limit: int = Query(default=15, ge=1, le=100)
) -> list[FornecedorAgregadoOut]:
    _require_pj_or_404(conn, cnpj)
    sql = """
        SELECT
            COALESCE(mp.cd_ibge, rc.raw_payload->>'cd_tce') AS chave,
            COALESCE(mp.nome, rc.raw_payload->>'municipio') AS nome,
            COUNT(*) AS n_contratos,
            ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total
        FROM raw.compras rc
        LEFT JOIN analytics.municipio_pr mp ON mp.cd_tce = rc.raw_payload->>'cd_tce'
        WHERE rc.fornecedor_cnpj = %s
        GROUP BY 1, 2
        ORDER BY valor_total DESC NULLS LAST
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cnpj, limit))
        return [FornecedorAgregadoOut(**r) for r in cur.fetchall()]


@app.get(
    "/fornecedor/{cnpj}/por-categoria",
    response_model=list[FornecedorAgregadoOut],
    tags=["fornecedor"],
)
def fornecedor_por_categoria(
    conn: ConnDep, cnpj: str
) -> list[FornecedorAgregadoOut]:
    _require_pj_or_404(conn, cnpj)
    sql = """
        SELECT
            COALESCE(ic.cluster_id, '_quarentena') AS chave,
            COALESCE(cr.descricao_canonica, 'Sem categoria mapeada') AS nome,
            COUNT(*) AS n_contratos,
            ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total
        FROM raw.compras rc
        JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
        LEFT JOIN analytics.cluster_registry cr
            ON cr.cluster_id = ic.cluster_id AND cr.cluster_version = ic.cluster_version
        WHERE rc.fornecedor_cnpj = %s
        GROUP BY 1, 2
        ORDER BY valor_total DESC NULLS LAST
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cnpj,))
        return [FornecedorAgregadoOut(**r) for r in cur.fetchall()]


@app.get(
    "/fornecedor/{cnpj}/por-modalidade",
    response_model=list[FornecedorAgregadoOut],
    tags=["fornecedor"],
)
def fornecedor_por_modalidade(
    conn: ConnDep, cnpj: str
) -> list[FornecedorAgregadoOut]:
    """Distribuicao de contratos do fornecedor por modalidade de licitacao.
    'sem_modalidade' = contratos onde nao foi possivel resolver via
    Licitacao + LicitacaoXContrato (fragmentado, ano cruzado, ou modalidade
    fora do mapa normalizado). Mostrado para nao esconder volume."""
    _require_pj_or_404(conn, cnpj)
    sql = """
        SELECT
            COALESCE(rc.modalidade, 'sem_modalidade') AS chave,
            COALESCE(rc.modalidade, 'Sem modalidade resolvida') AS nome,
            COUNT(*) AS n_contratos,
            ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total
        FROM raw.compras rc
        WHERE rc.fornecedor_cnpj = %s
        GROUP BY 1, 2
        ORDER BY valor_total DESC NULLS LAST
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cnpj,))
        return [FornecedorAgregadoOut(**r) for r in cur.fetchall()]


@app.get(
    "/fornecedor/{cnpj}/contratos",
    response_model=list[FornecedorContratoOut],
    tags=["fornecedor"],
)
def fornecedor_contratos(
    conn: ConnDep, cnpj: str, limit: int = Query(default=20, ge=1, le=100)
) -> list[FornecedorContratoOut]:
    """Top contratos do fornecedor por valor (mais recentes desempatam)."""
    _require_pj_or_404(conn, cnpj)
    sql = """
        SELECT
            rc.id AS raw_id,
            rc.source_id AS contrato_id,
            COALESCE(mp.nome, rc.raw_payload->>'municipio') AS municipio,
            rc.orgao_nome,
            rc.descricao,
            rc.valor_total,
            rc.contract_date::text AS contract_date,
            ic.cluster_id,
            ic.em_quarentena
        FROM raw.compras rc
        JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
        LEFT JOIN analytics.municipio_pr mp ON mp.cd_tce = rc.raw_payload->>'cd_tce'
        WHERE rc.fornecedor_cnpj = %s
        ORDER BY rc.valor_total DESC NULLS LAST, rc.contract_date DESC NULLS LAST
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cnpj, limit))
        return [FornecedorContratoOut(**r) for r in cur.fetchall()]


@app.get(
    "/fornecedor/{cnpj}/contratos.csv",
    response_class=Response,
    tags=["fornecedor"],
    summary="Contratos do fornecedor em CSV (PLANO §19.3)",
)
def fornecedor_contratos_csv(
    conn: ConnDep, cnpj: str, limit: int = Query(default=500, ge=1, le=5000)
) -> Response:
    """Mesma query de /fornecedor/{cnpj}/contratos em CSV. Default limit 500.
    Aplica L.2 default deny (helper _require_pj_or_404)."""
    _require_pj_or_404(conn, cnpj)
    sql = """
        SELECT
            rc.id AS raw_id,
            rc.source_id AS contrato_id,
            COALESCE(mp.nome, rc.raw_payload->>'municipio') AS municipio,
            rc.orgao_nome,
            rc.descricao,
            rc.valor_total,
            rc.contract_date::text AS contract_date,
            ic.cluster_id,
            ic.em_quarentena
        FROM raw.compras rc
        JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
        LEFT JOIN analytics.municipio_pr mp ON mp.cd_tce = rc.raw_payload->>'cd_tce'
        WHERE rc.fornecedor_cnpj = %s
        ORDER BY rc.valor_total DESC NULLS LAST, rc.contract_date DESC NULLS LAST
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cnpj, limit))
        rows = cur.fetchall()
    safe_cnpj = "".join(ch for ch in cnpj if ch.isdigit())
    return _rows_to_csv_response(
        rows,
        fieldnames=[
            "raw_id", "contrato_id", "municipio", "orgao_nome",
            "descricao", "valor_total", "contract_date",
            "cluster_id", "em_quarentena",
        ],
        filename=f"contratos_{safe_cnpj}_quantopagou.csv",
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
    "/tce-pr/municipio/{cd_ibge}/fornecedores.csv",
    response_class=Response,
    tags=["tce-pr"],
    summary="Fornecedores PJ do municipio em CSV (PLANO §19.3)",
)
def tce_pr_fornecedores_csv(
    conn: ConnDep,
    cd_ibge: str,
    limit: int = Query(default=500, ge=1, le=5000),
) -> Response:
    """Top fornecedores PJ do municipio em CSV. A MV ja filtra PJ
    (L.2.b), entao MEI/EI nao aparecem."""
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
        rows = cur.fetchall()
    return _rows_to_csv_response(
        rows,
        fieldnames=[
            "cd_ibge", "municipio", "fornecedor_cnpj", "fornecedor_nome",
            "n_contratos", "valor_total_periodo", "n_orgaos_distintos",
        ],
        filename=f"fornecedores_municipio_{cd_ibge}_quantopagou.csv",
    )


@app.get(
    "/tce-pr/cluster/{cluster_id}/ranking-municipios",
    response_model=list[RankingMunicipioOut],
    tags=["tce-pr"],
)
def tce_pr_ranking_municipios(
    conn: ConnDep,
    cluster_id: str,
    porte: str | None = None,
    modalidade: str | None = Query(
        default=None,
        description="Filtra por modalidade (pregao, dispensa, concorrencia, etc). 'sem_modalidade' = nao resolvida.",
    ),
    since: date | None = Query(
        default=None,
        description="Data assinatura mínima (YYYY-MM-DD). Filtra rc.contract_date.",
    ),
    until: date | None = Query(
        default=None,
        description="Data assinatura máxima (YYYY-MM-DD inclusive).",
    ),
    order: Literal["mediana_desc", "mediana_asc", "total_desc", "n_desc"] = Query(
        default="mediana_desc"
    ),
    limit: int = Query(default=20, ge=1, le=200),
) -> list[RankingMunicipioOut]:
    """Ranking de municipios PR para um cluster (soma todos os orgaos do
    municipio). Permite filtro por porte para garantir comparacao entre pares
    de mesmo tamanho, e filtro por modalidade para isolar (ex.) so dispensas.
    Vai direto na raw.compras + item_canonical (nao depende do mart).
    """
    order_sql = {
        "mediana_desc": "mediana_valor_contrato DESC",
        "mediana_asc": "mediana_valor_contrato ASC",
        "total_desc": "valor_total_periodo DESC",
        "n_desc": "n_contratos DESC",
    }[order]
    sql = f"""
        SELECT
            ic.cluster_id,
            mp.cd_tce AS cd_tce,
            mp.cd_ibge AS cd_ibge,
            COALESCE(mp.nome, rc.raw_payload->>'municipio') AS municipio,
            COALESCE(mp.porte, 'municipio_pr_pequeno') AS porte,
            mp.populacao AS populacao,
            COUNT(*) AS n_contratos,
            ROUND(SUM(rc.valor_total)::numeric, 2) AS valor_total_periodo,
            ROUND(percentile_cont(0.5) WITHIN GROUP (
                ORDER BY rc.valor_total)::numeric, 2) AS mediana_valor_contrato
        FROM raw.compras rc
        JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
        LEFT JOIN analytics.municipio_pr mp ON mp.cd_tce = rc.raw_payload->>'cd_tce'
        WHERE rc.source = 'tce_pr/contrato'
          AND ic.em_quarentena = FALSE
          AND ic.cluster_id = %s
          AND (%s::text IS NULL OR COALESCE(mp.porte, 'municipio_pr_pequeno') = %s)
          AND (
              %s::text IS NULL
              OR (%s = 'sem_modalidade' AND rc.modalidade IS NULL)
              OR rc.modalidade = %s
          )
          AND (%s::date IS NULL OR rc.contract_date >= %s::date)
          AND (%s::date IS NULL OR rc.contract_date <= %s::date)
          AND mp.cd_ibge IS NOT NULL
        GROUP BY 1, 2, 3, 4, 5, 6
        ORDER BY {order_sql}
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                cluster_id,
                porte, porte,
                modalidade, modalidade, modalidade,
                since, since,
                until, until,
                limit,
            ),
        )
        return [RankingMunicipioOut(**r) for r in cur.fetchall()]


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
    order: Literal["mediana_desc", "mediana_asc", "total_desc", "n_desc"] = Query(
        default="mediana_desc"
    ),
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
    }[order]
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


# ----------------------------- Per capita (PLANO §19.7) ---------------

_PER_CAPITA_ORDER_SQL = {
    "per_capita_desc": "gasto_per_capita DESC",
    "per_capita_asc": "gasto_per_capita ASC",
    "total_desc": "gasto_total DESC",
    "n_desc": "n_contratos DESC",
}

_PER_CAPITA_BASE_SELECT = """
    SELECT cluster_id, cluster_version, cd_tce, cd_ibge, municipio, porte,
           populacao, n_contratos, gasto_total, gasto_per_capita,
           mediana_valor_contrato
    FROM analytics.mart_gasto_per_capita
"""


@app.get(
    "/tce-pr/per-capita",
    response_model=list[PerCapitaOut],
    tags=["tce-pr"],
    summary="Ranking de gasto per capita (PLANO §19.7)",
)
def tce_pr_per_capita(
    conn: ConnDep,
    cluster: str | None = Query(
        default=None,
        description="Filtra por cluster_id (ex: merenda_escolar, medicamentos)",
    ),
    porte: str | None = Query(
        default=None,
        description=(
            "Filtra por porte (municipio_pr_grande/medio/pequeno) — guardrail "
            "de comparacao entre pares."
        ),
    ),
    order: Literal[
        "per_capita_desc", "per_capita_asc", "total_desc", "n_desc"
    ] = Query(default="per_capita_desc"),
    limit: int = Query(default=20, ge=1, le=200),
) -> list[PerCapitaOut]:
    """Ranking de municipios PR por gasto_per_capita (R$/habitante).

    populacao = IBGE Censo 2022; data fixa. Ver `/metodologia` para limites.
    Sem filtro de cluster, o ranking acumula todos os clusters do municipio
    — util pra comparar gasto total per capita entre cidades de mesmo porte.
    """
    sql = f"""
        {_PER_CAPITA_BASE_SELECT}
        WHERE (%s::text IS NULL OR cluster_id = %s)
          AND (%s::text IS NULL OR porte = %s)
        ORDER BY {_PER_CAPITA_ORDER_SQL[order]}
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cluster, cluster, porte, porte, limit))
        return [PerCapitaOut(**r) for r in cur.fetchall()]


@app.get(
    "/tce-pr/per-capita.csv",
    response_class=Response,
    tags=["tce-pr"],
    summary="Per capita em CSV (PLANO §19.3 + §19.7)",
)
def tce_pr_per_capita_csv(
    conn: ConnDep,
    cluster: str | None = None,
    porte: str | None = None,
    order: Literal[
        "per_capita_desc", "per_capita_asc", "total_desc", "n_desc"
    ] = "per_capita_desc",
    limit: int = Query(default=500, ge=1, le=5000),
) -> Response:
    """Ranking per capita em CSV. Mesmos filtros do endpoint JSON."""
    sql = f"""
        {_PER_CAPITA_BASE_SELECT}
        WHERE (%s::text IS NULL OR cluster_id = %s)
          AND (%s::text IS NULL OR porte = %s)
        ORDER BY {_PER_CAPITA_ORDER_SQL[order]}
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cluster, cluster, porte, porte, limit))
        rows = cur.fetchall()
    suffix = f"_{cluster}" if cluster else ""
    return _rows_to_csv_response(
        rows,
        fieldnames=[
            "cluster_id", "cluster_version", "cd_tce", "cd_ibge",
            "municipio", "porte", "populacao", "n_contratos",
            "gasto_total", "gasto_per_capita", "mediana_valor_contrato",
        ],
        filename=f"per_capita{suffix}_quantopagou.csv",
    )


@app.get(
    "/tce-pr/municipio/{cd_ibge}/per-capita",
    response_model=list[PerCapitaOut],
    tags=["tce-pr"],
    summary="Gasto per capita por cluster de um municipio (PLANO §19.7)",
)
def tce_pr_municipio_per_capita(
    conn: ConnDep,
    cd_ibge: str,
    order: Literal[
        "per_capita_desc", "per_capita_asc", "total_desc", "n_desc"
    ] = Query(default="per_capita_desc"),
    limit: int = Query(default=20, ge=1, le=200),
) -> list[PerCapitaOut]:
    """Top clusters de um municipio por gasto_per_capita.

    Alimenta o card "Gasto per capita por cluster" da pagina /municipio/[cd_tce].
    """
    sql = f"""
        {_PER_CAPITA_BASE_SELECT}
        WHERE cd_ibge = %s
        ORDER BY {_PER_CAPITA_ORDER_SQL[order]}
        LIMIT %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (cd_ibge, limit))
        return [PerCapitaOut(**r) for r in cur.fetchall()]


# ----------------------------- Correcoes (LGPD L.12) ------------------

# Mapa tipo -> sla_classe. factual_48h pra erro de fato; lgpd_15d pra
# pedidos LGPD (art. 19) e tudo o que envolve direito do titular ou
# classificacao de fornecedor (impacto sobre titular precisa avaliacao
# proporcional).
_SLA_POR_TIPO = {
    "factual": "factual_48h",
    "outro": "factual_48h",
    "lgpd_acesso": "lgpd_15d",
    "lgpd_correcao": "lgpd_15d",
    "lgpd_eliminacao": "lgpd_15d",
    "classificacao_pj": "lgpd_15d",
    "revisao_ranking": "lgpd_15d",
}

_STATUS_TERMINAL = {"resolvido_corrigido", "resolvido_sem_correcao", "rejeitado"}


def _correcao_row_to_out(row: dict) -> CorrecaoTicketOut:
    """Converte linha do banco em DTO publico aplicando regras de privacidade.

    Descricao so vai pra fora se publicar_descricao=TRUE ou se o ticket
    ainda esta ativo (reportador precisa ver o que reportou pra acompanhar).
    Email NUNCA sai do banco — auditavel mas nao publico.
    """
    expor_descricao = (
        row.get("publicar_descricao")
        or row.get("status") not in _STATUS_TERMINAL
    )
    prazo = None
    if row.get("criado_em") and row.get("sla_classe"):
        delta_horas = 48 if row["sla_classe"] == "factual_48h" else 15 * 24
        prazo = (row["criado_em"] + timedelta(hours=delta_horas)).isoformat()
    return CorrecaoTicketOut(
        ticket_id=row["ticket_id"],
        criado_em=row["criado_em"].isoformat(),
        tipo=row["tipo"],
        sla_classe=row["sla_classe"],
        status=row["status"],
        descricao_publica=row["descricao"] if expor_descricao else None,
        url_afetada=row.get("url_afetada"),
        raw_id_afetado=row.get("raw_id_afetado"),
        fornecedor_cnpj=row.get("fornecedor_cnpj"),
        resolvido_em=row["resolvido_em"].isoformat() if row.get("resolvido_em") else None,
        resolucao_publica=row.get("resolucao_publica"),
        prazo_iso=prazo,
    )


@app.post(
    "/correcoes/ticket",
    response_model=CorrecaoTicketOut,
    tags=["correcoes"],
    status_code=201,
)
def criar_correcao_ticket(
    conn: ConnDep, payload: CorrecaoTicketIn
) -> CorrecaoTicketOut:
    """Cria ticket de correcao com ID publico QP-AAAA-XXXX.

    Audit_log (L.10) registra automaticamente via trigger.
    """
    sla = _SLA_POR_TIPO[payload.tipo]
    with conn.cursor() as cur:
        # SET LOCAL nao aceita parametros prepared — usar Literal pra escape seguro.
        cur.execute(
            psycopg_sql.SQL("SET LOCAL app.audit_actor = {}").format(
                psycopg_sql.Literal("/correcoes/ticket (public)")
            )
        )
        cur.execute(
            psycopg_sql.SQL("SET LOCAL app.audit_base_legal = {}").format(
                psycopg_sql.Literal(
                    "LGPD art. 18 — direitos do titular / correcao"
                )
            )
        )
        cur.execute("SELECT analytics.fn_gerar_ticket_id() AS tid")
        ticket_id = cur.fetchone()["tid"]
        cur.execute(
            """
            INSERT INTO analytics.correcao_ticket
                (ticket_id, tipo, sla_classe, url_afetada, raw_id_afetado,
                 fornecedor_cnpj, descricao, fonte_correta, publicar_descricao,
                 contato_email)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                ticket_id, payload.tipo, sla,
                payload.url_afetada, payload.raw_id_afetado,
                payload.fornecedor_cnpj, payload.descricao,
                payload.fonte_correta, payload.publicar_descricao,
                payload.contato_email,
            ),
        )
        row = cur.fetchone()
    conn.commit()
    return _correcao_row_to_out(row)


@app.get(
    "/correcoes/ticket/{ticket_id}",
    response_model=CorrecaoTicketOut,
    tags=["correcoes"],
)
def get_correcao_ticket(
    conn: ConnDep, ticket_id: str
) -> CorrecaoTicketOut:
    """Consulta status publico do ticket. Email do reportador nunca sai;
    descricao so sai se publicar_descricao=TRUE ou ticket ainda ativo."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM analytics.correcao_ticket WHERE ticket_id = %s",
            (ticket_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(404, f"ticket {ticket_id} não encontrado")
    return _correcao_row_to_out(row)


@app.get(
    "/correcoes/recentes",
    response_model=list[CorrecaoTicketOut],
    tags=["correcoes"],
)
def list_correcoes_recentes(
    conn: ConnDep,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[CorrecaoTicketOut]:
    """Vitrine publica das ultimas correcoes resolvidas (PLANO §6.6).

    So inclui tickets em estado terminal. Descricao aparece apenas se
    publicar_descricao=TRUE; caso contrario o ticket aparece como
    'correcao processada' sem detalhe — mas resolucao_publica e
    visivel para todos os terminais.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM analytics.correcao_ticket
            WHERE status IN ('resolvido_corrigido','resolvido_sem_correcao','rejeitado')
            ORDER BY resolvido_em DESC NULLS LAST, criado_em DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
    return [_correcao_row_to_out(r) for r in rows]
