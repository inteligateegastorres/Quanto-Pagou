"""Carrega populacao Censo 2022 do IBGE para os 397 municipios PR.

Antes desse script, analytics.municipio_pr tinha so 35 cidades catalogadas.
Pos-rodada: 397+ municipios (incluindo todos que aparecem em raw.compras).

Mapping cd_tce <-> cd_ibge: feito por NOME normalizado (uppercase, strip
accents, sem sufixo ' - PR'). Cidades sem match imprime warning.

Uso:
    python -m uv run python scripts/load_ibge_populacao.py
    python -m uv run python scripts/load_ibge_populacao.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import unicodedata

import httpx
import psycopg
from psycopg.rows import dict_row
from rich.console import Console

from ingest.config import settings


IBGE_MUNICIPIOS_URL = (
    "https://servicodados.ibge.gov.br/api/v1/localidades/estados/41/municipios"
)
IBGE_POPULACAO_URL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/4709/periodos/2022/"
    "variaveis/93?localidades=N6[N3[41]]"
)


def normalizar(nome: str) -> str:
    """UPPERCASE, strip accents, sem ' - PR' suffix."""
    nome = nome.upper().strip()
    if nome.endswith(" - PR"):
        nome = nome[:-5].strip()
    nfkd = unicodedata.normalize("NFKD", nome)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def porte_por_populacao(pop: int) -> str:
    """Classificacao do porte municipal (consistente com regras existentes)."""
    if pop < 30_000:
        return "municipio_pr_pequeno"
    if pop < 200_000:
        return "municipio_pr_medio"
    return "municipio_pr_grande"


def main() -> int:
    parser = argparse.ArgumentParser(prog="scripts/load_ibge_populacao.py")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    console = Console()

    console.rule("[bold]load_ibge_populacao[/]")

    # 1. Lista de municipios PR via IBGE (cd_ibge + nome)
    console.print("[dim]GET IBGE municipios PR...[/]")
    try:
        municipios = httpx.get(IBGE_MUNICIPIOS_URL, timeout=30.0).raise_for_status().json()
    except httpx.HTTPError as e:
        console.print(f"[red]Falhou IBGE municipios: {e}[/]")
        return 1
    console.print(f"  {len(municipios)} municipios PR no IBGE")

    # 2. Populacao Censo 2022 por cd_ibge
    console.print("[dim]GET IBGE Censo 2022 populacao...[/]")
    try:
        pop_resp = httpx.get(IBGE_POPULACAO_URL, timeout=30.0).raise_for_status().json()
    except httpx.HTTPError as e:
        console.print(f"[red]Falhou IBGE populacao: {e}[/]")
        return 1
    pop_por_cd_ibge: dict[str, int] = {}
    for serie in pop_resp[0]["resultados"][0]["series"]:
        cd_ibge = serie["localidade"]["id"]
        valor = serie["serie"].get("2022")
        if valor and valor.isdigit():
            pop_por_cd_ibge[cd_ibge] = int(valor)
    console.print(f"  {len(pop_por_cd_ibge)} populacoes carregadas")

    # 3. Distintos (cd_tce, nome) de raw.compras (TCE-PR)
    console.print("[dim]Lendo cd_tce + nome de raw.compras...[/]")
    tce_por_nome: dict[str, tuple[str, str]] = {}  # nome_norm -> (cd_tce, nome_original)
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT DISTINCT
                    raw_payload->>'cd_tce' AS cd_tce,
                    raw_payload->>'municipio' AS nome
                FROM raw.compras
                WHERE source = 'tce_pr/contrato'
                  AND raw_payload->>'cd_tce' IS NOT NULL
                  AND raw_payload->>'municipio' IS NOT NULL
                """
            )
            for r in cur.fetchall():
                nome_norm = normalizar(r["nome"])
                tce_por_nome[nome_norm] = (r["cd_tce"], r["nome"])
    console.print(f"  {len(tce_por_nome)} cd_tce distintos em raw.compras")

    # 4. Match por nome normalizado
    rows_para_upsert: list[tuple[str, str, str, str, int]] = []
    sem_match: list[str] = []
    for m in municipios:
        cd_ibge = str(m["id"])
        nome_ibge = m["nome"]
        nome_norm = normalizar(nome_ibge)
        if nome_norm not in tce_por_nome:
            sem_match.append(f"{nome_ibge} (cd_ibge={cd_ibge})")
            continue
        cd_tce, nome_orig = tce_por_nome[nome_norm]
        pop = pop_por_cd_ibge.get(cd_ibge)
        if pop is None:
            sem_match.append(f"{nome_ibge} (sem populacao)")
            continue
        porte = porte_por_populacao(pop)
        rows_para_upsert.append((cd_tce, cd_ibge, nome_orig, porte, pop))

    console.print(f"\n[green]{len(rows_para_upsert)} linhas para UPSERT[/]")
    if sem_match:
        console.print(f"[yellow]{len(sem_match)} sem match no TCE-PR (esperado para municipios sem contratos):[/]")
        for s in sem_match[:5]:
            console.print(f"  - {s}")
        if len(sem_match) > 5:
            console.print(f"  ... e mais {len(sem_match) - 5}")

    # 5. UPSERT
    if args.dry_run:
        console.print("[yellow]--dry-run: nao escreveu no banco[/]")
        return 0

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO analytics.municipio_pr
                    (cd_tce, cd_ibge, nome, porte, populacao)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (cd_tce) DO UPDATE SET
                    cd_ibge = EXCLUDED.cd_ibge,
                    nome = EXCLUDED.nome,
                    porte = EXCLUDED.porte,
                    populacao = EXCLUDED.populacao,
                    atualizado_em = NOW()
                """,
                rows_para_upsert,
            )
        conn.commit()

    # Stats finais
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(populacao) AS com_populacao,
                    SUM(populacao) AS pop_estado
                FROM analytics.municipio_pr
                """
            )
            stats = cur.fetchone()
            cur.execute(
                """
                SELECT porte, COUNT(*) AS n
                FROM analytics.municipio_pr WHERE populacao IS NOT NULL
                GROUP BY porte ORDER BY n DESC
                """
            )
            portes = cur.fetchall()

    console.rule("[bold green]OK[/]")
    console.print(f"  Total municipios na tabela : {stats['total']}")
    console.print(f"  Com populacao              : {stats['com_populacao']}")
    console.print(f"  Populacao total PR (Censo) : {stats['pop_estado']:,}".replace(",", "."))
    for p in portes:
        console.print(f"  {p['porte']:<24} {p['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
