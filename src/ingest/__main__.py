"""CLI: python -m ingest <start> <end> [--page-size N] [--max-pages N] [--fixture PATH]."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from ingest.compras import DEFAULT_PAGE_SIZE, ingest, ingest_fixture
from ingest.config import settings


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ingest",
        description="Ingere itens de contratos federais (Compras.gov.br) numa janela de datas.",
    )
    today = date.today()
    parser.add_argument(
        "start",
        nargs="?",
        type=_parse_date,
        default=today - timedelta(days=7),
        help="dataVigenciaInicialMin (YYYY-MM-DD). Default: 7 dias atras.",
    )
    parser.add_argument(
        "end",
        nargs="?",
        type=_parse_date,
        default=today,
        help="dataVigenciaInicialMax (YYYY-MM-DD). Default: hoje.",
    )
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limita paginas (smoke test). Default: sem limite.",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="Carrega de JSONL local em vez da API (uso quando upstream esta caido).",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=settings.log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=False)],
    )

    console = Console()
    mode = f"fixture={args.fixture}" if args.fixture else "API live"
    console.rule(f"[bold]Compras.gov.br ingest[/] {args.start} -> {args.end} ({mode})")

    def _progress(page: int, total_pages: int, items_so_far: int) -> None:
        console.print(
            f"  pagina {page}/{total_pages or '?'}  itens acumulados: {items_so_far}"
        )

    try:
        if args.fixture:
            result = ingest_fixture(
                args.fixture,
                period_start=args.start,
                period_end=args.end,
                on_progress=_progress,
            )
        else:
            result = ingest(
                args.start,
                args.end,
                page_size=args.page_size,
                max_pages=args.max_pages,
                on_progress=_progress,
            )
    except Exception as exc:
        console.print(f"[red]ERRO:[/] {exc}")
        raise

    console.rule("[bold green]OK")
    console.print(f"  snapshot_id   : {result.snapshot_id}")
    console.print(f"  snapshot_path : {result.snapshot_path}")
    console.print(f"  paginas       : {result.pages_fetched}")
    console.print(f"  itens         : {result.items_inserted}")
    console.print(f"  sha256        : {result.hash_sha256[:16]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
