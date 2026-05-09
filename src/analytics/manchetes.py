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
_SELECT_CANDIDATOS = """
SELECT
    cd.cluster_id,
    cd.cluster_version,
    cd.cd_tce,
    m.cd_ibge,
    m.nome           AS municipio_nome,
    m.porte,
    m.populacao,
    cd.n_sujeito,
    cd.valor_total_sujeito,
    cd.med_sujeito,
    cd.med_cluster,
    cd.spread,
    cd.iqr_sujeito,
    cd.iqr_cluster,
    cd.comparab_proxy,
    -- Score do ranker: ln(volume) * ln(spread) * comparab.
    -- ln para evitar 1 fator dominar; comparab penaliza categoria ruidosa.
    (LN(cd.valor_total_sujeito) * LN(cd.spread) * cd.comparab_proxy) AS rank_score
FROM analytics.cluster_discrepancias cd
JOIN analytics.municipio_pr m ON m.cd_tce = cd.cd_tce
WHERE cd.n_cluster        >= %(cluster_n_min)s
  AND cd.n_sujeito        >= %(sujeito_n_min)s
  AND cd.valor_total_sujeito >= %(sujeito_valor_total_min)s
  AND cd.spread           >= %(spread_min)s
  AND cd.iqr_sujeito      >= %(iqr_sujeito_min)s
  AND cd.iqr_sujeito      <= %(iqr_relativo_max_k)s * cd.iqr_cluster
  AND cd.comparab_proxy   >= %(comparab_min)s
ORDER BY rank_score DESC
"""


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

    with psycopg.connect(settings.database_url) as conn:
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
                        rank_score, rank_no_dia, parametros_hash
                    ) VALUES (
                        %(manchete_id)s, %(cluster_id)s, %(cluster_version)s,
                        %(cd_tce)s, %(cd_ibge)s, %(municipio_nome)s, %(porte)s,
                        %(populacao)s, %(n_sujeito)s, %(valor_total_sujeito)s,
                        %(med_sujeito)s, %(med_cluster)s, %(spread)s,
                        %(iqr_sujeito)s, %(iqr_cluster)s, %(comparab_proxy)s,
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
