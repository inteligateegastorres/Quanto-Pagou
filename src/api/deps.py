"""Dependencias compartilhadas entre routers da API.

Pool de conexao psycopg + lifespan + ConnDep + constantes de produto
(threshold de fornecedor §6.5).

Routers em src/api/routers/* importam ConnDep daqui; main.py importa
o lifespan pra injetar no FastAPI.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from ingest.config import settings

# Threshold de contratos para gerar perfil publico de fornecedor (guardrail
# §6.5 do plano: filtra fornecedores eventuais, reduz risco de exposicao
# injusta). Reusado em /fornecedor/{cnpj} e em /fornecedores (listagem).
FORNECEDOR_THRESHOLD = 5


# ----------------------------- pool -----------------------------------

_pool: ConnectionPool | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _pool
    _pool = ConnectionPool(
        conninfo=settings.database_url,
        min_size=1,
        max_size=10,
        kwargs={"row_factory": dict_row},
        open=True,
    )
    yield
    _pool.close()


def get_conn():
    # NAO use assert: python -O remove asserts em producao.
    if _pool is None:
        raise RuntimeError("pool not initialized — lifespan nao rodou?")
    with _pool.connection() as conn:
        yield conn


ConnDep = Annotated[psycopg.Connection, Depends(get_conn)]
