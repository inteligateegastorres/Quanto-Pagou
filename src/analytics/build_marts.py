"""Pipeline de canonicalizacao + marts (Day 3-4).

Le raw.compras, popula analytics.cluster_registry + analytics.item_canonical,
refresca os marts. Idempotente: pode rodar varias vezes seguidas.

CLI:
    python -m uv run python -m analytics.build_marts
    python -m uv run python -m analytics.build_marts --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row
from rich.console import Console
from rich.logging import RichHandler

from analytics.escolas import extrair_escola
from analytics.resolution import (
    CanonicalRow,
    GoldenCluster,
    KeywordCluster,
    _compile_patterns,
    canonicalize,
    canonicalize_tce_pr_row,
    load_golden_set,
    load_keyword_clusters,
    load_unit_conversion,
)
from ingest.config import settings

logger = logging.getLogger(__name__)


_SELECT_RAW = """
SELECT id, source, catmat_id, catser_id, descricao, valor_unitario, valor_total, raw_payload
FROM raw.compras
"""


_UPSERT_REGISTRY = """
INSERT INTO analytics.cluster_registry
    (cluster_id, cluster_version, descricao_canonica, categoria)
VALUES (%s, %s, %s, %s)
ON CONFLICT (cluster_id, cluster_version) DO NOTHING
"""


_UPSERT_CANONICAL = """
INSERT INTO analytics.item_canonical (
    raw_id, cluster_id, cluster_version, metodo_resolucao, confianca_resolucao,
    unidade_label, unidade_base, fator_conversao, valor_unitario_normalizado,
    ente_nivel, uf, porte, em_quarentena, motivo_quarentena, resolved_at
) VALUES (
    %(raw_id)s, %(cluster_id)s, %(cluster_version)s, %(metodo_resolucao)s,
    %(confianca_resolucao)s, %(unidade_label)s, %(unidade_base)s,
    %(fator_conversao)s, %(valor_unitario_normalizado)s, %(ente_nivel)s,
    %(uf)s, %(porte)s, %(em_quarentena)s, %(motivo_quarentena)s, NOW()
)
ON CONFLICT (raw_id) DO UPDATE SET
    cluster_id = EXCLUDED.cluster_id,
    cluster_version = EXCLUDED.cluster_version,
    metodo_resolucao = EXCLUDED.metodo_resolucao,
    confianca_resolucao = EXCLUDED.confianca_resolucao,
    unidade_label = EXCLUDED.unidade_label,
    unidade_base = EXCLUDED.unidade_base,
    fator_conversao = EXCLUDED.fator_conversao,
    valor_unitario_normalizado = EXCLUDED.valor_unitario_normalizado,
    ente_nivel = EXCLUDED.ente_nivel,
    uf = EXCLUDED.uf,
    porte = EXCLUDED.porte,
    em_quarentena = EXCLUDED.em_quarentena,
    motivo_quarentena = EXCLUDED.motivo_quarentena,
    resolved_at = NOW()
"""


def seed_cluster_registry(
    conn: psycopg.Connection, clusters: list[GoldenCluster]
) -> int:
    if not clusters:
        return 0
    rows = [
        (c.cluster_id, c.cluster_version, c.descricao_canonica, c.categoria)
        for c in clusters
    ]
    with conn.cursor() as cur:
        cur.executemany(_UPSERT_REGISTRY, rows)
    return len(rows)


def _row_to_dict(cr: CanonicalRow) -> dict[str, Any]:
    return {
        "raw_id": cr.raw_id,
        "cluster_id": cr.cluster_id,
        "cluster_version": cr.cluster_version,
        "metodo_resolucao": cr.metodo_resolucao,
        "confianca_resolucao": cr.confianca_resolucao,
        "unidade_label": cr.unidade_label,
        "unidade_base": cr.unidade_base,
        "fator_conversao": cr.fator_conversao,
        "valor_unitario_normalizado": cr.valor_unitario_normalizado,
        "ente_nivel": cr.ente_nivel,
        "uf": cr.uf,
        "porte": cr.porte,
        "em_quarentena": cr.em_quarentena,
        "motivo_quarentena": cr.motivo_quarentena,
    }


def run(dry_run: bool = False) -> dict[str, Any]:
    """Executa o pipeline analytics completo. Devolve estatisticas para log."""
    console = Console()
    started = datetime.now()
    golden_by_catmat, all_clusters = load_golden_set()
    conv = load_unit_conversion()
    compiled = _compile_patterns(conv)
    keyword_clusters = load_keyword_clusters()
    logger.info(
        "Carregado: %d clusters golden / %d catmat_ids mapeados / %d patterns / %d clusters keyword",
        len(all_clusters),
        len(golden_by_catmat),
        len(compiled),
        len(keyword_clusters),
    )

    sintetico_clusters: dict[tuple[str, str], dict[str, Any]] = {}
    canonicals: list[CanonicalRow] = []

    with psycopg.connect(settings.database_url) as conn:
        seeded = seed_cluster_registry(conn, all_clusters)
        if not dry_run:
            conn.commit()
        logger.info("cluster_registry: %d clusters golden seeded", seeded)

        # Seed clusters de keyword no registry (TCE-PR e similares).
        if keyword_clusters:
            with conn.cursor() as cur:
                cur.executemany(
                    _UPSERT_REGISTRY,
                    [
                        (
                            kc.cluster_id,
                            kc.cluster_version,
                            kc.descricao_canonica,
                            kc.categoria,
                        )
                        for kc in keyword_clusters
                    ],
                )
            if not dry_run:
                conn.commit()
            logger.info(
                "cluster_registry: %d clusters keyword (Tier 1.5)",
                len(keyword_clusters),
            )

        n_tce_pr = 0
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(_SELECT_RAW)
            for raw in cur:
                source = raw.get("source") or ""
                if source.startswith("tce_pr/"):
                    cr = canonicalize_tce_pr_row(raw, keyword_clusters)
                    n_tce_pr += 1
                else:
                    cr = canonicalize(raw, golden_by_catmat, conv, _compiled=compiled)
                canonicals.append(cr)
                # Cluster sinteticos descobertos durante a resolucao
                if cr.cluster_id and cr.metodo_resolucao == "tier1_catmat_sintetico":
                    key = (cr.cluster_id, cr.cluster_version or "v1")
                    sintetico_clusters.setdefault(
                        key,
                        {
                            "cluster_id": cr.cluster_id,
                            "cluster_version": cr.cluster_version or "v1",
                            "descricao_canonica": (
                                f"CATMAT {cr.cluster_id.removeprefix('catmat_')}"
                            ),
                            "categoria": "desconhecida",
                        },
                    )

        # Registra clusters sinteticos antes de inserir item_canonical.
        if sintetico_clusters:
            with conn.cursor() as cur:
                cur.executemany(
                    _UPSERT_REGISTRY,
                    [
                        (
                            v["cluster_id"],
                            v["cluster_version"],
                            v["descricao_canonica"],
                            v["categoria"],
                        )
                        for v in sintetico_clusters.values()
                    ],
                )
            logger.info(
                "cluster_registry: %d clusters sinteticos (catmat fora do golden)",
                len(sintetico_clusters),
            )
            if not dry_run:
                conn.commit()

        # Insert item_canonical em batches.
        n_quarentena = sum(1 for cr in canonicals if cr.em_quarentena)
        if not dry_run:
            with conn.cursor() as cur:
                cur.executemany(
                    _UPSERT_CANONICAL,
                    [_row_to_dict(cr) for cr in canonicals],
                )
            conn.commit()
            logger.info("item_canonical: %d linhas upserted", len(canonicals))

            # Popula analytics.escola_mencao a partir do dsObjeto dos
            # contratos TCE-PR. Limpa antes (extracao e funcao pura).
            console.print("[dim]Reconstruindo analytics.escola_mencao...[/]")
            # cursor com row_factory=dict_row para acessar por nome
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("TRUNCATE analytics.escola_mencao")
                cur.execute(
                    """
                    SELECT id, descricao, raw_payload->>'cd_tce' AS cd_tce
                    FROM raw.compras WHERE source = 'tce_pr/contrato'
                    """
                )
                rows_para_inserir: list[tuple[int, str, str, str, str | None]] = []
                for r in cur.fetchall():
                    ext = extrair_escola(r["descricao"])
                    if ext is None:
                        continue
                    rows_para_inserir.append(
                        (r["id"], ext.nome, ext.slug, ext.padrao, r["cd_tce"])
                    )
                if rows_para_inserir:
                    with conn.cursor() as cur2:
                        cur2.executemany(
                            """
                            INSERT INTO analytics.escola_mencao
                                (raw_id, escola_nome, escola_slug, padrao, cd_tce)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (raw_id) DO NOTHING
                            """,
                            rows_para_inserir,
                        )
            conn.commit()
            logger.info(
                "escola_mencao: %d mencoes detectadas",
                len(rows_para_inserir),
            )

            # Refresh marts (federal + tce_pr).
            for mv in (
                "analytics.mart_pares",
                "analytics.mart_orgao_cluster",
                "analytics.mart_contratos_municipio",
                "analytics.mart_fornecedores_municipio",
            ):
                console.print(f"[dim]REFRESH MATERIALIZED VIEW {mv}...[/]")
                try:
                    conn.execute(f"REFRESH MATERIALIZED VIEW {mv}")
                except psycopg.errors.UndefinedTable:
                    conn.rollback()
                    logger.warning(
                        "MV %s nao existe ainda — rode sql/003_tce_pr.sql primeiro",
                        mv,
                    )
            conn.commit()
        else:
            logger.info("[dry-run] %d linhas seriam upserted", len(canonicals))

        # Estatisticas finais.
        stats = {
            "linhas_raw": len(canonicals),
            "linhas_canonical": len(canonicals),
            "linhas_tce_pr": n_tce_pr,
            "em_quarentena": n_quarentena,
            "clusters_golden": len(all_clusters),
            "clusters_keyword": len(keyword_clusters),
            "clusters_sinteticos": len(sintetico_clusters),
            "elapsed_s": round((datetime.now() - started).total_seconds(), 2),
        }
        if not dry_run:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM analytics.mart_pares")
                stats["mart_pares_rows"] = cur.fetchone()[0]
                for mv in ("mart_contratos_municipio", "mart_fornecedores_municipio"):
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM analytics.{mv}")
                        stats[f"{mv}_rows"] = cur.fetchone()[0]
                    except psycopg.errors.UndefinedTable:
                        conn.rollback()
                cur.execute("SELECT COUNT(*) FROM analytics.mart_orgao_cluster")
                stats["mart_orgao_rows"] = cur.fetchone()[0]
        return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m analytics.build_marts")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=settings.log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=False)],
    )

    console = Console()
    console.rule("[bold]analytics build_marts[/]")
    stats = run(dry_run=args.dry_run)
    console.rule("[bold green]OK")
    for k, v in stats.items():
        console.print(f"  {k:<24} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
