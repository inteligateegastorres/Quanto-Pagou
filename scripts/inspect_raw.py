"""Sumario rapido do estado de raw.compras / raw.snapshots."""

from __future__ import annotations

import psycopg

from ingest.config import settings


def main() -> None:
    with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, source, records_count, period_start, period_end, ingested_at "
            "FROM raw.snapshots ORDER BY ingested_at"
        )
        snaps = cur.fetchall()
        print(f"Snapshots ({len(snaps)}):")
        for s in snaps:
            print(f"  {s[0]}  src={s[1]}  rows={s[2]}  [{s[3]} -> {s[4]}]  {s[5]}")

        cur.execute("SELECT COUNT(*) FROM raw.compras")
        print(f"\nraw.compras: {cur.fetchone()[0]} linhas")

        cur.execute(
            """
            SELECT
                catmat_id,
                COUNT(*) AS n,
                ROUND(MIN(valor_unitario)::numeric, 2) AS minimo,
                ROUND(
                    percentile_cont(0.25) WITHIN GROUP (ORDER BY valor_unitario)::numeric,
                    2
                ) AS p25,
                ROUND(
                    percentile_cont(0.5) WITHIN GROUP (ORDER BY valor_unitario)::numeric,
                    2
                ) AS mediana,
                ROUND(
                    percentile_cont(0.75) WITHIN GROUP (ORDER BY valor_unitario)::numeric,
                    2
                ) AS p75,
                ROUND(MAX(valor_unitario)::numeric, 2) AS maximo
            FROM raw.compras
            WHERE catmat_id IS NOT NULL
            GROUP BY catmat_id
            ORDER BY 1
            """
        )
        rows = cur.fetchall()
        if rows:
            print("\nDistribuicao de preco por CATMAT:")
            print(f"  {'catmat':<10}  {'n':>3}  {'min':>8}  {'p25':>8}  "
                  f"{'mediana':>8}  {'p75':>8}  {'max':>8}")
            for r in rows:
                print(f"  {r[0]:<10}  {r[1]:>3}  {r[2]:>8}  {r[3]:>8}  "
                      f"{r[4]:>8}  {r[5]:>8}  {r[6]:>8}")


if __name__ == "__main__":
    main()
