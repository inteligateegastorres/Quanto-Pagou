"""Sumario de marts analytics. Roda apos build_marts."""

from __future__ import annotations

import psycopg

from ingest.config import settings


def main() -> None:
    with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
        # mart_pares
        cur.execute(
            """
            SELECT cluster_id, ente_nivel, uf, porte, n,
                   minimo, p25, mediana, p75, maximo, iqr
            FROM analytics.mart_pares
            ORDER BY cluster_id
            """
        )
        rows = cur.fetchall()
        print(f"\nmart_pares ({len(rows)} grupos):")
        if rows:
            print(
                f"  {'cluster':<28} {'ente':<10} {'uf':<5} {'porte':<20} "
                f"{'n':>3}  {'min':>7}  {'p25':>7}  {'med':>7}  {'p75':>7}  "
                f"{'max':>7}  {'iqr':>6}"
            )
            for r in rows:
                print(
                    f"  {r[0]:<28} {r[1]:<10} {r[2]:<5} {r[3]:<20} "
                    f"{r[4]:>3}  {float(r[5]):>7.2f}  {float(r[6]):>7.2f}  "
                    f"{float(r[7]):>7.2f}  {float(r[8]):>7.2f}  "
                    f"{float(r[9]):>7.2f}  {float(r[10]):>6.2f}"
                )

        # Top 5 orgaos com maior mediana, por cluster (gancho viral).
        cur.execute(
            """
            WITH ranked AS (
                SELECT
                    cluster_id, orgao_codigo, orgao_nome, n_compras,
                    mediana_orgao,
                    ROW_NUMBER() OVER (
                        PARTITION BY cluster_id
                        ORDER BY mediana_orgao DESC
                    ) AS rn
                FROM analytics.mart_orgao_cluster
            )
            SELECT cluster_id, orgao_nome, n_compras, mediana_orgao
            FROM ranked
            WHERE rn <= 3
            ORDER BY cluster_id, rn
            """
        )
        rows = cur.fetchall()
        print(f"\nTop 3 orgaos por mediana, por cluster ({len(rows)} linhas):")
        if rows:
            current_cluster = None
            for r in rows:
                if r[0] != current_cluster:
                    print(f"\n  [{r[0]}]")
                    current_cluster = r[0]
                print(
                    f"    n={r[2]:>2}  med=R$ {float(r[3]):>7.2f}  {r[1]}"
                )

        # Quarentena por motivo.
        cur.execute("SELECT * FROM analytics.v_quarentena_resumo")
        rows = cur.fetchall()
        print(f"\nQuarentena ({len(rows)} categorias x motivos):")
        if not rows:
            print("  (vazio - todos os itens passaram)")
        for r in rows:
            print(f"  categoria={r[0]:<20}  motivo={r[1]:<40}  n={r[2]}")

        # Confianca/metodo
        cur.execute(
            """
            SELECT metodo_resolucao, COUNT(*) AS n,
                   ROUND(AVG(confianca_resolucao)::numeric, 2) AS conf_media
            FROM analytics.item_canonical
            GROUP BY metodo_resolucao
            ORDER BY n DESC
            """
        )
        rows = cur.fetchall()
        print(f"\nResolucao por metodo ({len(rows)} metodos):")
        for r in rows:
            print(f"  {r[0]:<32}  n={r[1]:>4}  conf_media={float(r[2])}")


if __name__ == "__main__":
    main()
