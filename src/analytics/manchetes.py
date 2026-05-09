"""Selecao de manchetes (PLANO §13.5/14.X) - Camadas 2 e 3.

Camada 1 (analytics.cluster_discrepancias) e refrescada por build_marts.
Aqui aplicamos os thresholds do YAML versionado e populamos:
  - analytics.manchete            (substitui set ativo)
  - analytics.manchete_publicada  (append-only log de auditoria)

CLI:
    python -m uv run python -m analytics.manchetes refresh
    python -m uv run python -m analytics.manchetes refresh --config config/manchete_v1.yaml
    python -m uv run python -m analytics.manchetes refresh --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Any

import psycopg
import yaml
from psycopg.rows import dict_row
from rich.console import Console

from ingest.config import settings

logger = logging.getLogger(__name__)


DEFAULT_CONFIG = "config/manchete_v1.yaml"


def hash_config(config: dict[str, Any]) -> str:
    """Hash deterministico do YAML — vai junto com cada manchete pra auditoria."""
    canonical = json.dumps(config, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def carregar_config(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"YAML nao encontrado: {path}")
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# SQL que aplica thresholds do YAML sobre a Camada 1.
# Os parametros chegam como dict via psycopg %(nome)s placeholders.
#
# Estabilidade temporal: a clausula janelas_passadas conta para quantas das
# 3 janelas (90d, 180d, 365d) o spread_Nd >= spread_min (ignorando janelas
# com amostra menor que estabilidade_min_n_janela). Filtra >= min_janelas.
_SELECT_CANDIDATOS = """
WITH base AS (
    SELECT
        cd.*,
        m.cd_ibge,
        m.nome AS municipio_nome,
        m.porte,
        m.populacao,
        -- Conta janelas que passam: spread_Nd >= spread_min E n_sujeito_Nd >= min_n_janela.
        -- NULL spread_Nd (janela vazia) nao conta como passou nem como falhou.
        (
            (CASE WHEN cd.n_sujeito_90d  >= %(estabilidade_min_n_janela)s
                  AND cd.spread_90d  >= %(spread_min)s THEN 1 ELSE 0 END) +
            (CASE WHEN cd.n_sujeito_180d >= %(estabilidade_min_n_janela)s
                  AND cd.spread_180d >= %(spread_min)s THEN 1 ELSE 0 END) +
            (CASE WHEN cd.n_sujeito_365d >= %(estabilidade_min_n_janela)s
                  AND cd.spread_365d >= %(spread_min)s THEN 1 ELSE 0 END)
        ) AS janelas_passadas
    FROM analytics.cluster_discrepancias cd
    JOIN analytics.municipio_pr m ON m.cd_tce = cd.cd_tce
)
SELECT
    cluster_id, cluster_version, cd_tce, cd_ibge, municipio_nome,
    porte, populacao,
    n_sujeito, valor_total_sujeito, med_sujeito, med_cluster,
    spread, iqr_sujeito, iqr_cluster, comparab_proxy,
    spread_90d, spread_180d, spread_365d, janelas_passadas,
    -- Score do ranker: ln(volume) * ln(spread) * comparab.
    -- ln para evitar 1 fator dominar; comparab penaliza categoria ruidosa.
    (LN(valor_total_sujeito) * LN(spread) * comparab_proxy) AS rank_score
FROM base
WHERE n_cluster        >= %(cluster_n_min)s
  AND n_sujeito        >= %(sujeito_n_min)s
  AND valor_total_sujeito >= %(sujeito_valor_total_min)s
  AND spread           >= %(spread_min)s
  AND iqr_sujeito      >= %(iqr_sujeito_min)s
  AND iqr_sujeito      <= %(iqr_relativo_max_k)s * iqr_cluster
  AND comparab_proxy   >= %(comparab_min)s
  AND janelas_passadas >= %(estabilidade_min_janelas)s
ORDER BY rank_score DESC
"""


def _diagnosticar_motivo(
    cur: psycopg.Cursor[Any],
    manchete_id: str,
    cluster_id: str,
    cd_tce: str,
    config: dict[str, Any],
) -> str:
    """Diagnostica por que uma manchete antes ativa nao esta mais. Le
    cluster_discrepancias atual e identifica o primeiro threshold que falhou."""
    cur.execute(
        """
        SELECT
            cd.n_cluster, cd.n_sujeito, cd.valor_total_sujeito,
            cd.spread, cd.iqr_sujeito, cd.iqr_cluster, cd.comparab_proxy,
            cd.spread_90d, cd.spread_180d, cd.spread_365d,
            cd.n_sujeito_90d, cd.n_sujeito_180d, cd.n_sujeito_365d,
            (m.cd_tce IS NOT NULL) AS municipio_catalogado
        FROM analytics.cluster_discrepancias cd
        LEFT JOIN analytics.municipio_pr m ON m.cd_tce = cd.cd_tce
        WHERE cd.cluster_id = %s AND cd.cd_tce = %s
        """,
        (cluster_id, cd_tce),
    )
    row = cur.fetchone()
    if row is None:
        return "removida do cluster_discrepancias (sem contratos elegiveis no snapshot)"

    cfg = config
    if not row["municipio_catalogado"]:
        return "municipio nao catalogado em municipio_pr"
    if row["n_cluster"] < cfg["cluster_n_min"]:
        return f"cluster encolheu para {row['n_cluster']} contratos (limiar {cfg['cluster_n_min']})"
    if row["n_sujeito"] < cfg["sujeito_n_min"]:
        return f"n_sujeito caiu para {row['n_sujeito']} (limiar {cfg['sujeito_n_min']})"
    if row["valor_total_sujeito"] < cfg["sujeito_valor_total_min"]:
        return f"valor total caiu para R$ {float(row['valor_total_sujeito']):,.0f} (limiar R$ {cfg['sujeito_valor_total_min']:,.0f})".replace(",", ".")
    if row["spread"] < cfg["spread_min"]:
        return f"spread caiu para {float(row['spread']):.1f}x (limiar {cfg['spread_min']}x)"
    if row["iqr_sujeito"] < cfg["iqr_sujeito_min"]:
        return f"IQR sujeito caiu para {float(row['iqr_sujeito']):.1f} (limiar {cfg['iqr_sujeito_min']})"
    if row["iqr_sujeito"] > cfg["iqr_relativo_max_k"] * row["iqr_cluster"]:
        return f"IQR sujeito ({float(row['iqr_sujeito']):.1f}) > {cfg['iqr_relativo_max_k']}x IQR cluster ({float(row['iqr_cluster']):.1f}) — sujeito ficou heterogeneo"
    if row["comparab_proxy"] < cfg["comparab_min"]:
        return f"comparabilidade caiu para {float(row['comparab_proxy']):.2f} (limiar {cfg['comparab_min']})"
    # Estabilidade
    janelas_passadas = sum(
        1 for n_field, sp_field in [
            ("n_sujeito_90d", "spread_90d"),
            ("n_sujeito_180d", "spread_180d"),
            ("n_sujeito_365d", "spread_365d"),
        ]
        if row[n_field] >= cfg["estabilidade_min_n_janela"]
        and row[sp_field] is not None
        and row[sp_field] >= cfg["spread_min"]
    )
    if janelas_passadas < cfg["estabilidade_min_janelas"]:
        return f"estabilidade caiu para {janelas_passadas}/3 janelas (limiar {cfg['estabilidade_min_janelas']})"
    return "saiu do top N publicado (passou todos os thresholds, mas com rank pior)"


def refresh(config: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    """Aplica thresholds, popula Camadas 2 e 3. Devolve stats."""
    parametros_hash = hash_config(config)
    logger.info("config hash=%s versao=%s", parametros_hash, config.get("versao"))

    candidatos: list[dict[str, Any]] = []
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(_SELECT_CANDIDATOS, config)
            candidatos = cur.fetchall()

    logger.info("%d candidatos selecionados", len(candidatos))

    if dry_run:
        return {
            "n_candidatos": len(candidatos),
            "parametros_hash": parametros_hash,
            "dry_run": True,
        }

    top_n = int(config.get("top_n_publicado", 20))
    publicados = candidatos[:top_n]
    novos_ids = {f"{c['cluster_id']}__{c['cd_tce']}" for c in publicados}

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Persiste config aplicada (busca reversa em /manchetes precisa dela).
            cur.execute(
                """
                INSERT INTO analytics.manchete_config_aplicada
                    (parametros_hash, config_json)
                VALUES (%s, %s::jsonb)
                ON CONFLICT (parametros_hash) DO UPDATE SET
                    ultima_aplicacao = NOW()
                """,
                (parametros_hash, json.dumps(config, default=str)),
            )

            # ANTES de truncar: capturar IDs ativos para detectar saidas.
            cur.execute("SELECT manchete_id, cluster_id, cd_tce FROM analytics.manchete")
            ativos_antes = cur.fetchall()
            saidas = [a for a in ativos_antes if a["manchete_id"] not in novos_ids]
            logger.info("%d manchetes ativas antes; %d saidas detectadas", len(ativos_antes), len(saidas))

            # Diagnostica + registra saidas em manchete_saida.
            for s in saidas:
                # Busca payload da ultima publicacao ativa
                cur.execute(
                    """
                    SELECT payload_json
                    FROM analytics.manchete_publicada
                    WHERE manchete_id = %s
                    ORDER BY publicada_em DESC LIMIT 1
                    """,
                    (s["manchete_id"],),
                )
                ultimo = cur.fetchone()
                payload_anterior = ultimo["payload_json"] if ultimo else {}
                motivo = _diagnosticar_motivo(
                    cur, s["manchete_id"], s["cluster_id"], s["cd_tce"], config
                )
                cur.execute(
                    """
                    INSERT INTO analytics.manchete_saida
                        (manchete_id, motivo, payload_anterior, parametros_hash)
                    VALUES (%s, %s, %s::jsonb, %s)
                    ON CONFLICT (saiu_em, manchete_id) DO NOTHING
                    """,
                    (s["manchete_id"], motivo, json.dumps(payload_anterior, default=str), parametros_hash),
                )

        with conn.cursor() as cur:
            # Camada 2: substitui o set ativo (TRUNCATE + INSERT).
            cur.execute("TRUNCATE analytics.manchete")
            for rank, c in enumerate(publicados, start=1):
                manchete_id = f"{c['cluster_id']}__{c['cd_tce']}"
                cur.execute(
                    """
                    INSERT INTO analytics.manchete (
                        manchete_id, cluster_id, cluster_version, cd_tce, cd_ibge,
                        municipio_nome, porte, populacao,
                        n_sujeito, valor_total_sujeito, med_sujeito, med_cluster,
                        spread, iqr_sujeito, iqr_cluster, comparab_proxy,
                        spread_90d, spread_180d, spread_365d, janelas_passadas,
                        rank_score, rank_no_dia, parametros_hash
                    ) VALUES (
                        %(manchete_id)s, %(cluster_id)s, %(cluster_version)s,
                        %(cd_tce)s, %(cd_ibge)s, %(municipio_nome)s, %(porte)s,
                        %(populacao)s, %(n_sujeito)s, %(valor_total_sujeito)s,
                        %(med_sujeito)s, %(med_cluster)s, %(spread)s,
                        %(iqr_sujeito)s, %(iqr_cluster)s, %(comparab_proxy)s,
                        %(spread_90d)s, %(spread_180d)s, %(spread_365d)s,
                        %(janelas_passadas)s,
                        %(rank_score)s, %(rank_no_dia)s, %(parametros_hash)s
                    )
                    """,
                    {**c, "manchete_id": manchete_id, "rank_no_dia": rank,
                     "parametros_hash": parametros_hash},
                )

            # Camada 3: log append-only com snapshot completo (json) por manchete.
            for rank, c in enumerate(publicados, start=1):
                manchete_id = f"{c['cluster_id']}__{c['cd_tce']}"
                payload = {
                    **{k: (str(v) if hasattr(v, "is_finite") else v) for k, v in c.items()},
                    "rank_no_dia": rank,
                }
                cur.execute(
                    """
                    INSERT INTO analytics.manchete_publicada
                        (manchete_id, parametros_hash, payload_json)
                    VALUES (%s, %s, %s::jsonb)
                    """,
                    (manchete_id, parametros_hash, json.dumps(payload, default=str)),
                )
        conn.commit()

    return {
        "n_candidatos": len(candidatos),
        "n_publicados": len(publicados),
        "n_saidas": len(saidas),
        "parametros_hash": parametros_hash,
        "config_versao": config.get("versao"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m analytics.manchetes")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_ref = sub.add_parser("refresh", help="Aplica YAML e re-popula Camadas 2 e 3")
    p_ref.add_argument("--config", default=DEFAULT_CONFIG)
    p_ref.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=settings.log_level, format="%(message)s")
    console = Console()
    console.rule(f"[bold]manchetes {args.cmd}[/]")

    if args.cmd == "refresh":
        config = carregar_config(args.config)
        stats = refresh(config, dry_run=args.dry_run)
        console.rule("[bold green]OK[/]")
        for k, v in stats.items():
            console.print(f"  {k:<24} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
