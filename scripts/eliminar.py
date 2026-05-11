"""Registra eliminacao de raw_id (LGPD art. 18 IV).

Resolve achado 1.6 do parecer juridico (PLANO §18 L.1).

Uso:
    python -m uv run python scripts/eliminar.py \\
        --raw-id 12345 \\
        --motivo "Solicitacao do titular via /correcoes#42" \\
        --fundamento "LGPD art. 18 IV (eliminacao)" \\
        --ator "dpo@quantopagou.org" \\
        --ticket-ref "correcao-42"

Apos registrar:
- raw.snapshots e raw.compras NAO mudam (integridade do snapshot bruto)
- analytics.item_canonical.eliminada_em e setado via trigger
- MVs filtram pelo novo flag (precisa REFRESH MATERIALIZED VIEW
  CONCURRENTLY pra refletir; este script faz automaticamente)
- Endpoint /contrato/{raw_id} passa a retornar 410 Gone com motivo
- Endpoint /eliminacoes/publicas lista (ID + motivo + data, sem dado)
"""

from __future__ import annotations

import argparse
import sys

import psycopg
from psycopg.rows import dict_row
from rich.console import Console

from ingest.config import settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scripts/eliminar.py")
    parser.add_argument("--raw-id", type=int, required=True, help="raw.compras.id a eliminar")
    parser.add_argument("--motivo", required=True, help="Motivo legivel (vai pro log publico)")
    parser.add_argument(
        "--fundamento",
        default="LGPD art. 18 IV (eliminacao)",
        help="Fundamento legal (default: LGPD art. 18 IV)",
    )
    parser.add_argument("--ator", required=True, help="Ator (email do DPO ou ID do ticket)")
    parser.add_argument("--ticket-ref", default=None, help="Referencia opcional ao ticket")
    parser.add_argument(
        "--no-refresh",
        action="store_true",
        help="Pula REFRESH MATERIALIZED VIEW (use se vai eliminar varios em batch)",
    )
    args = parser.parse_args(argv)
    console = Console()
    console.rule("[bold]eliminar[/]")

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Verifica que raw_id existe
            cur.execute(
                "SELECT id, source, descricao FROM raw.compras WHERE id = %s",
                (args.raw_id,),
            )
            raw = cur.fetchone()
            if raw is None:
                console.print(f"[red]raw_id {args.raw_id} nao existe em raw.compras[/]")
                return 1

            # Verifica se ja foi eliminado
            cur.execute(
                "SELECT eliminada_em, motivo FROM analytics.eliminacao WHERE raw_id = %s",
                (args.raw_id,),
            )
            ja = cur.fetchone()
            if ja:
                console.print(
                    f"[yellow]raw_id {args.raw_id} ja eliminado em {ja['eliminada_em']}: "
                    f"{ja['motivo']}[/]"
                )
                return 0

            console.print(f"raw_id={args.raw_id} source={raw['source']}")
            console.print(f"  descricao: {raw['descricao'][:100]}...")
            console.print(f"  motivo: {args.motivo}")
            console.print(f"  fundamento: {args.fundamento}")
            console.print(f"  ator: {args.ator}")

            # Setting de sessao capturado pelo trigger analytics.fn_audit_log
            # (L.10). Trigger tem fallback pra coluna ator do INSERT, mas
            # explicitar aqui mantem o padrao pra futuros writes.
            cur.execute("SET LOCAL app.audit_actor = %s", (args.ator,))
            cur.execute("SET LOCAL app.audit_base_legal = %s", (args.fundamento,))

            # Insere — trigger sincroniza item_canonical.eliminada_em
            cur.execute(
                """
                INSERT INTO analytics.eliminacao
                    (raw_id, motivo, fundamento_legal, ator, ticket_ref)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (args.raw_id, args.motivo, args.fundamento, args.ator, args.ticket_ref),
            )
        conn.commit()
        console.print("[green]Eliminacao registrada.[/]")

        # Refresh das MVs (concurrently — nao bloqueia leituras)
        if not args.no_refresh:
            console.print("[dim]REFRESH MATERIALIZED VIEW CONCURRENTLY (~50s)...[/]")
            for mv in (
                "analytics.mart_pares",
                "analytics.mart_orgao_cluster",
                "analytics.mart_contratos_municipio",
                "analytics.mart_fornecedores_municipio",
                "analytics.cluster_discrepancias",
            ):
                try:
                    conn.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}")
                except psycopg.errors.UndefinedTable:
                    conn.rollback()
            conn.commit()
            console.print("[green]MVs refrescadas. Eliminacao efetiva na vitrine publica.[/]")
        else:
            console.print(
                "[yellow]MVs nao refrescadas (--no-refresh). Rode "
                "`python -m uv run python -m analytics.build_marts` quando terminar o batch.[/]"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
