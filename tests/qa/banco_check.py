"""QA §A.6 automatizado — bate Postgres contra API.

Resolve a maior area cega da rodada anterior de QA: integridade do banco
vs payload da API. Roda 10 checks; cada um imprime PASS/FAIL com numeros
e diff (quando aplicavel).

Uso:
    python -m uv run python tests/qa/banco_check.py
    python -m uv run python tests/qa/banco_check.py --api http://127.0.0.1:8001

Exit code 0 se tudo PASS, 1 se algum FAIL. Pode ir em CI mais tarde.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any

import httpx
import psycopg
from psycopg.rows import dict_row
from rich.console import Console
from rich.table import Table

from ingest.config import settings


@dataclass
class Check:
    name: str
    sql: str
    api_path: str
    api_field: str
    # Tolerancia em valor absoluto (para checks com timing/snapshot drift).
    # 0 = match exato. Default 0.
    tolerancia: int = 0


# Os 10 checks que cobrem §A.6 da CHECKLIST.md.
CHECKS: list[Check] = [
    Check(
        name="raw.compras count",
        sql="SELECT COUNT(*) AS n FROM raw.compras",
        api_path="/health",
        api_field="raw_compras",
    ),
    Check(
        name="item_canonical count",
        sql="SELECT COUNT(*) AS n FROM analytics.item_canonical",
        api_path="/health",
        api_field="item_canonical",
    ),
    Check(
        name="em_quarentena count",
        sql="SELECT COUNT(*) AS n FROM analytics.item_canonical WHERE em_quarentena = TRUE",
        api_path="/health",
        api_field="em_quarentena",
    ),
    Check(
        name="mart_pares row count",
        sql="SELECT COUNT(*) AS n FROM analytics.mart_pares",
        api_path="/health",
        api_field="mart_pares_rows",
    ),
    Check(
        name="mart_orgao_cluster row count",
        sql="SELECT COUNT(*) AS n FROM analytics.mart_orgao_cluster",
        api_path="/health",
        api_field="mart_orgao_rows",
    ),
    Check(
        name="snapshots count",
        sql="SELECT COUNT(*) AS n FROM raw.snapshots",
        api_path="/health",
        api_field="snapshots",
    ),
    Check(
        name="total_contratos PR",
        sql=(
            "SELECT COUNT(*) AS n FROM raw.compras "
            "WHERE source = 'tce_pr/contrato'"
        ),
        api_path="/stats/pr",
        api_field="total_contratos",
    ),
    Check(
        name="total_municipios PR (distinct cd_tce)",
        sql=(
            "SELECT COUNT(DISTINCT raw_payload->>'cd_tce') AS n "
            "FROM raw.compras WHERE source = 'tce_pr/contrato' "
            "  AND raw_payload->>'cd_tce' IS NOT NULL"
        ),
        api_path="/stats/pr",
        api_field="total_municipios",
    ),
    Check(
        # API conta DISTINCT (cnpj, nome) — TCE-PR mascara CPFs de pessoas
        # fisicas em CNPJs comuns, entao desambiguamos pelo nome.
        name="total_fornecedores PR (distinct cnpj+nome)",
        sql=(
            "SELECT COUNT(*) AS n FROM ("
            "  SELECT DISTINCT fornecedor_cnpj, fornecedor_nome "
            "  FROM raw.compras "
            "  WHERE source = 'tce_pr/contrato' AND fornecedor_cnpj IS NOT NULL"
            ") sub"
        ),
        api_path="/stats/pr",
        api_field="total_fornecedores",
    ),
    Check(
        name="n_em_cluster (PR contratos com cluster_id)",
        sql=(
            "SELECT COUNT(*) AS n "
            "FROM raw.compras rc "
            "JOIN analytics.item_canonical ic ON ic.raw_id = rc.id "
            "WHERE rc.source = 'tce_pr/contrato' "
            "  AND ic.cluster_id IS NOT NULL"
        ),
        api_path="/stats/pr",
        api_field="n_em_cluster",
    ),
]


# Invariantes adicionais que nao sao "API vs banco" mas sao importantes:
INVARIANTES_SQL: list[tuple[str, str, Any]] = [
    (
        "cluster_version unico (so v1 esperado)",
        (
            "SELECT cluster_version FROM analytics.item_canonical "
            "WHERE cluster_id IS NOT NULL "
            "GROUP BY cluster_version"
        ),
        ["v1"],  # esperado: lista de cluster_versions
    ),
    (
        "item_canonical e 1:1 com raw.compras",
        (
            "SELECT "
            "  (SELECT COUNT(*) FROM raw.compras) AS raw, "
            "  (SELECT COUNT(*) FROM analytics.item_canonical) AS canonical"
        ),
        "equal",  # esperado: raw == canonical
    ),
    (
        "quarentenados nao foram removidos (count > 0 esperado)",
        "SELECT COUNT(*) AS n FROM analytics.item_canonical WHERE em_quarentena = TRUE",
        "positive",
    ),
]


def fetch_api(api_base: str, path: str) -> dict[str, Any]:
    r = httpx.get(f"{api_base}{path}", timeout=10.0)
    r.raise_for_status()
    return r.json()


def main() -> int:
    parser = argparse.ArgumentParser(prog="tests/qa/banco_check.py")
    parser.add_argument(
        "--api",
        default="http://127.0.0.1:8001",
        help="URL base da API (default: http://127.0.0.1:8001)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="So imprime FAIL e o resumo final",
    )
    args = parser.parse_args()

    console = Console()
    console.rule("[bold]banco_check (QA §A.6 automatizado)[/]")

    # Cache /health e /stats/pr para nao bater 1x por check
    api_cache: dict[str, dict[str, Any]] = {}
    paths = {c.api_path for c in CHECKS}
    try:
        for p in paths:
            api_cache[p] = fetch_api(args.api, p)
    except (httpx.HTTPError, httpx.ConnectError) as e:
        console.print(f"[red]API inalcancavel em {args.api}: {e}[/]")
        return 1

    # Conexao DB
    try:
        conn = psycopg.connect(settings.database_url)
    except psycopg.OperationalError as e:
        console.print(f"[red]Postgres inalcancavel: {e}[/]")
        return 1

    pass_count = 0
    fail_count = 0

    table = Table(show_header=True, header_style="bold")
    table.add_column("check", style="cyan", no_wrap=False)
    table.add_column("DB", justify="right", style="white")
    table.add_column("API", justify="right", style="white")
    table.add_column("diff", justify="right")
    table.add_column("status", justify="center")

    with conn, conn.cursor(row_factory=dict_row) as cur:
        for c in CHECKS:
            cur.execute(c.sql)
            row = cur.fetchone()
            if row is None or "n" not in row:
                table.add_row(c.name, "—", "—", "—", "[red]ERR[/]")
                fail_count += 1
                continue
            db_val = row["n"]
            api_val = api_cache[c.api_path].get(c.api_field)
            if api_val is None:
                table.add_row(c.name, str(db_val), "(missing)", "—", "[red]FAIL[/]")
                fail_count += 1
                continue
            diff = abs(int(db_val) - int(api_val))
            status = "[green]PASS[/]" if diff <= c.tolerancia else "[red]FAIL[/]"
            if diff <= c.tolerancia:
                pass_count += 1
            else:
                fail_count += 1
            if not args.quiet or status == "[red]FAIL[/]":
                table.add_row(
                    c.name,
                    f"{db_val:,}".replace(",", "."),
                    f"{api_val:,}".replace(",", "."),
                    str(diff) if diff > 0 else "—",
                    status,
                )

    console.print(table)

    # Invariantes
    console.rule("[bold]Invariantes (sem comparar com API)[/]")
    inv_table = Table(show_header=True, header_style="bold")
    inv_table.add_column("invariante", style="cyan")
    inv_table.add_column("resultado", style="white")
    inv_table.add_column("status", justify="center")

    with psycopg.connect(settings.database_url) as conn2:
        with conn2.cursor(row_factory=dict_row) as cur:
            for nome, sql, esperado in INVARIANTES_SQL:
                cur.execute(sql)
                rows = cur.fetchall()
                if esperado == ["v1"]:
                    versions = [r["cluster_version"] for r in rows]
                    ok = versions == ["v1"]
                    inv_table.add_row(
                        nome,
                        ",".join(versions) if versions else "(vazio)",
                        "[green]PASS[/]" if ok else "[red]FAIL[/]",
                    )
                    pass_count += int(ok)
                    fail_count += int(not ok)
                elif esperado == "equal":
                    r0 = rows[0]
                    ok = int(r0["raw"]) == int(r0["canonical"])
                    inv_table.add_row(
                        nome,
                        f"raw={r0['raw']:,} canonical={r0['canonical']:,}".replace(
                            ",", "."
                        ),
                        "[green]PASS[/]" if ok else "[red]FAIL[/]",
                    )
                    pass_count += int(ok)
                    fail_count += int(not ok)
                elif esperado == "positive":
                    r0 = rows[0]
                    ok = int(r0["n"]) > 0
                    inv_table.add_row(
                        nome,
                        f"{r0['n']:,}".replace(",", "."),
                        "[green]PASS[/]" if ok else "[yellow]WARN[/]",
                    )
                    pass_count += int(ok)
                    # WARN nao conta como fail; quarentena vazia e ok mas suspeito

    console.print(inv_table)

    cor = "green" if fail_count == 0 else "red"
    console.rule(f"[bold {cor}]{pass_count} PASS · {fail_count} FAIL[/]")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
