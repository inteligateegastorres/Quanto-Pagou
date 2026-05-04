"""Sanity check: Python -> Postgres connection works, expected schema exists."""

from __future__ import annotations

import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

dsn = os.getenv(
    "DATABASE_URL",
    "postgresql://quantopagou:quantopagou_dev@localhost:5433/quantopagou",
)

with psycopg.connect(dsn) as conn, conn.cursor() as cur:
    cur.execute(
        "SELECT table_schema, table_name "
        "FROM information_schema.tables "
        "WHERE table_schema IN ('raw','analytics') "
        "ORDER BY 1, 2"
    )
    tables = cur.fetchall()
    print("Tabelas:", tables)

    cur.execute("SELECT count(*) FROM raw.compras")
    print("raw.compras rows:", cur.fetchone()[0])

    cur.execute("SELECT count(*) FROM raw.snapshots")
    print("raw.snapshots rows:", cur.fetchone()[0])

print("OK: conexao Python -> Postgres funcional")
