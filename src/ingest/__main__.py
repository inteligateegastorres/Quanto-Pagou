"""CLI: python -m ingest <start> <end> [--page-size N] [--max-pages N] [--fixture PATH]."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from ingest.compras import (
    DEFAULT_PAGE_SIZE,
    ingest,
    ingest_fixture,
    ingest_with_split,
)
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
    parser.add_argument(
        "--no-split",
        action="store_true",
        help="Desativa window-splitting: tenta a janela inteira de uma vez (modo legacy).",
    )
    parser.add_argument(
        "--min-window-days",
        type=int,
        default=1,
        help="Tamanho minimo da janela durante o split recursivo (default 1 = 1 dia).",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=settings.log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=False)],
    )

    console = Console()
    if args.fixture:
        mode = f"fixture={args.fixture}"
    elif args.no_split:
        mode = "API live (no-split)"
    else:
        mode = f"API live (split, min={args.min_window_days}d)"
    console.rule(f"[bold]Compras.gov.br ingest[/] {args.start} -> {args.end} ({mode})")

    def _progress(page: int, total_pages: int, items_so_far: int) -> None:
        console.print(
            f"  pagina {page}/{total_pages or '?'}  itens acumulados: {items_so_far}"
        )

    def _window_event(event: str, ws, we, **kw) -> None:
        tag = {
            "start": "[dim]>>>",
            "ok":    "[green]OK ",
            "split": "[yellow]SPL",
            "fail":  "[red]FAIL",
            "fatal": "[red bold]FATAL",
        }.get(event, event)
        extra = ""
        if event == "split" and "error" in kw:
            extra = f"  motivo: {kw['error'][:120]}"
        elif event == "fail" and "error" in kw:
            extra = f"  erro: {kw['error'][:120]}"
        elif event == "ok" and "result" in kw:
            r = kw["result"]
            extra = f"  paginas={r.pages_fetched} itens={r.items_inserted}"
        console.print(f"  {tag}[/] {ws} -> {we}{extra}")

    try:
        if args.fixture:
            result = ingest_fixture(
                args.fixture,
                period_start=args.start,
                period_end=args.end,
                on_progress=_progress,
            )
            console.rule("[bold green]OK")
            console.print(f"  snapshot_id   : {result.snapshot_id}")
            console.print(f"  snapshot_path : {result.snapshot_path}")
            console.print(f"  paginas       : {result.pages_fetched}")
            console.print(f"  itens         : {result.items_inserted}")
            console.print(f"  sha256        : {result.hash_sha256[:16]}...")
            return 0

        if args.no_split:
            result = ingest(
                args.start,
                args.end,
                page_size=args.page_size,
                max_pages=args.max_pages,
                on_progress=_progress,
            )
            console.rule("[bold green]OK")
            console.print(f"  snapshot_id   : {result.snapshot_id}")
            console.print(f"  snapshot_path : {result.snapshot_path}")
            console.print(f"  paginas       : {result.pages_fetched}")
            console.print(f"  itens         : {result.items_inserted}")
            console.print(f"  sha256        : {result.hash_sha256[:16]}...")
            return 0

        summary = ingest_with_split(
            args.start,
            args.end,
            page_size=args.page_size,
            max_pages=args.max_pages,
            min_window_days=args.min_window_days,
            on_progress=_progress,
            on_window_event=_window_event,
        )
    except Exception as exc:
        console.print(f"[red]ERRO:[/] {exc}")
        raise

    if summary.has_any_failure and summary.has_any_success:
        console.rule("[bold yellow]PARCIAL")
    elif summary.has_any_success:
        console.rule("[bold green]OK")
    else:
        console.rule("[bold red]FALHOU")
    console.print(f"  janelas OK     : {len(summary.successes)}")
    console.print(f"  janelas FAILED : {len(summary.failures)}")
    console.print(f"  paginas total  : {summary.pages_total}")
    console.print(f"  itens total    : {summary.items_total}")
    if summary.failures:
        console.print("  janelas com falha:")
        for fw in summary.failures:
            console.print(
                f"    {fw.period_start} -> {fw.period_end}  {fw.error[:120]}"
            )
    # Exit codes: 0 = sucesso (total ou parcial); 2 = nada ingerido.
    return 0 if summary.has_any_success else 2


if __name__ == "__main__":
    sys.exit(main())
