"""Expurga raw_payload redundante de raw.compras (LGPD L.9.b).

Política de retenção em docs/legal/RETENCAO.md: o JSONB original em
`raw.compras.raw_payload` e redundante com as colunas dedicadas APOS
canonicalizacao validada. Apos 90 dias com canonicalizacao em
`analytics.item_canonical`, podemos substituir o JSONB por '{}'::jsonb
(coluna e NOT NULL — nao podemos deletar). Snapshot bruto original
permanece em raw.snapshots (auditoria contra falsificacao).

Uso:
    # default: dry-run, mostra impacto, NAO altera nada
    python -m uv run python scripts/expurgar_raw_payload.py

    # config:
    python -m uv run python scripts/expurgar_raw_payload.py --days 90

    # APLICA expurgo (irreversivel a nivel de tabela; o snapshot raw
    # original permanece em raw.snapshots, entao a base e auditavel
    # ainda; mas o reprocessamento via raw.compras.raw_payload deixa
    # de ser possivel):
    python -m uv run python scripts/expurgar_raw_payload.py --apply

Criterios para uma linha ser expurgada:
    1. raw.compras.ingested_at < NOW() - INTERVAL 'N days' (default 90)
    2. JOIN com analytics.item_canonical (canonicalizacao bem-sucedida)
    3. raw_payload <> '{}'::jsonb (ainda nao expurgado)
    4. snapshot original existe (garantido por FK)

Aplicacao em batches (default 5000 linhas/commit) para nao prender
escrita longa. Cada batch seta app.audit_actor pra audit_log (L.10)
capturar quem rodou (apesar de raw.compras nao ter trigger de audit
hoje — vide TODO no fim deste arquivo).
"""

from __future__ import annotations

import argparse
import sys
from typing import Final

import psycopg
from psycopg import sql as psycopg_sql
from psycopg.rows import dict_row
from rich.console import Console
from rich.table import Table

from ingest.config import settings


PAYLOAD_VAZIO: Final[str] = "{}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scripts/expurgar_raw_payload.py")
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Idade minima em dias (default 90)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="EXECUTA o expurgo. Sem essa flag, so mostra dry-run.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Linhas por batch/commit (default 5000)",
    )
    parser.add_argument(
        "--ator",
        default="cli:expurgar_raw_payload",
        help="Ator registrado em app.audit_actor (default: cli:expurgar_raw_payload)",
    )
    args = parser.parse_args(argv)

    console = Console()
    modo = "APPLY" if args.apply else "DRY-RUN"
    console.rule(f"[bold]expurgar_raw_payload — {modo}[/]")
    console.print(f"  idade minima: {args.days} dias")
    console.print(f"  batch size:   {args.batch_size}")
    console.print(f"  ator:         {args.ator}")

    with psycopg.connect(settings.database_url) as conn:
        # 1. contagens + impacto
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS n,
                       COALESCE(SUM(pg_column_size(rc.raw_payload)), 0) AS bytes_payload
                FROM raw.compras rc
                JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
                WHERE rc.ingested_at < NOW() - make_interval(days => %s)
                  AND rc.raw_payload <> '{}'::jsonb
                """,
                (args.days,),
            )
            resumo = cur.fetchone()
            n_candidatos = int(resumo["n"])
            bytes_payload = int(resumo["bytes_payload"])

            cur.execute(
                """
                SELECT rc.source,
                       EXTRACT(YEAR FROM rc.ingested_at)::int AS ano,
                       COUNT(*) AS n,
                       COALESCE(SUM(pg_column_size(rc.raw_payload)), 0) AS bytes
                FROM raw.compras rc
                JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
                WHERE rc.ingested_at < NOW() - make_interval(days => %s)
                  AND rc.raw_payload <> '{}'::jsonb
                GROUP BY 1, 2
                ORDER BY 1, 2
                """,
                (args.days,),
            )
            por_src_ano = cur.fetchall()

        console.print()
        console.print(f"[bold]Candidatos:[/] {n_candidatos:,}".replace(",", "."))
        console.print(
            f"[bold]Espaco a liberar:[/] {bytes_payload:,} B "
            f"(~{bytes_payload / (1024 * 1024):.1f} MiB)".replace(",", ".")
        )

        if n_candidatos == 0:
            console.print(
                "[green]Nada a expurgar — saindo.[/] "
                "(Pode ser que ja foi expurgado, ou que o banco ainda nao "
                "tem dados antigos suficientes.)"
            )
            return 0

        tbl = Table(title="Distribuicao por (source, ano)")
        tbl.add_column("source")
        tbl.add_column("ano")
        tbl.add_column("linhas", justify="right")
        tbl.add_column("bytes", justify="right")
        for r in por_src_ano:
            tbl.add_row(
                str(r["source"]),
                str(r["ano"]),
                f"{int(r['n']):,}".replace(",", "."),
                f"{int(r['bytes']):,}".replace(",", "."),
            )
        console.print(tbl)

        if not args.apply:
            console.print()
            console.print(
                "[yellow]DRY-RUN — nada foi alterado. Use --apply para executar.[/]"
            )
            console.print(
                "[dim]Validacao recomendada (PLANO §18 L.9.b): rodar dry-run em pelo "
                "menos 1 ciclo, conferir distribuicao, e SO ENTAO executar com "
                "--apply. Workflow automatico (L.9.c) deve seguir o mesmo passo.[/]"
            )
            return 0

        # 2. APPLY — UPDATE em batches
        console.print()
        console.print("[bold red]APPLY:[/] expurgando em batches...")
        total_atualizado = 0
        while True:
            with conn.cursor() as cur:
                cur.execute(
                    psycopg_sql.SQL("SET LOCAL app.audit_actor = {}").format(
                        psycopg_sql.Literal(args.ator)
                    )
                )
                cur.execute(
                    psycopg_sql.SQL(
                        "SET LOCAL app.audit_base_legal = {}"
                    ).format(
                        psycopg_sql.Literal(
                            "LGPD L.9.b — politica de retencao (docs/legal/RETENCAO.md)"
                        )
                    )
                )
                # Selecionar ids do batch + UPDATE.
                cur.execute(
                    """
                    WITH batch AS (
                        SELECT rc.id
                        FROM raw.compras rc
                        JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
                        WHERE rc.ingested_at < NOW() - make_interval(days => %s)
                          AND rc.raw_payload <> '{}'::jsonb
                        LIMIT %s
                    )
                    UPDATE raw.compras rc
                       SET raw_payload = '{}'::jsonb
                      FROM batch
                     WHERE rc.id = batch.id
                    """,
                    (args.days, args.batch_size),
                )
                atualizado = cur.rowcount or 0
            conn.commit()
            total_atualizado += atualizado
            console.print(
                f"  batch: {atualizado:,} linhas (total: {total_atualizado:,})".replace(
                    ",", "."
                )
            )
            if atualizado < args.batch_size:
                break

        console.print()
        console.print(
            f"[green]Expurgo concluido: {total_atualizado:,} linhas atualizadas.[/]".replace(
                ",", "."
            )
        )
        console.print(
            "[dim]Snapshots brutos em raw.snapshots permanecem inalterados — "
            "auditoria contra falsificacao preservada.[/]"
        )
    return 0


# TODO L.10.b — adicionar trigger de audit em raw.compras (UPDATE de raw_payload)
# pra capturar o expurgo cirurgicamente. Hoje o expurgo nao gera audit_log row
# porque raw.compras nao tem trigger; mas o setting app.audit_actor fica
# documentado no log da sessao do Postgres e o commit deste script no git.


if __name__ == "__main__":
    sys.exit(main())
