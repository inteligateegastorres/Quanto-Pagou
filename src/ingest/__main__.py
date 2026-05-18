"""CLI ingest Compras.gov.br.

Forma legacy (contratos):
    python -m ingest <start> <end> [--page-size N] [--max-pages N] [--fixture PATH]

Forma nova (órgãos federais, L.19.11.a):
    python -m ingest orgaos [--page-size N] [--max-pages N] [--fixture PATH]
"""

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
    ingest_by_orgaos,
    ingest_fixture,
    load_orgaos_ativos_federais,
)
from ingest.compras_orgaos import (
    DEFAULT_PAGE_SIZE as ORGAOS_DEFAULT_PAGE_SIZE,
)
from ingest.compras_orgaos import (
    ingest_orgaos,
    ingest_orgaos_fixture,
)
from ingest.config import settings


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def _run_orgaos(argv: list[str]) -> int:
    """Subcomando 'orgaos': ingere cadastro de órgãos federais."""
    parser = argparse.ArgumentParser(
        prog="python -m ingest orgaos",
        description="Ingere cadastro de órgãos federais (Compras.gov.br /modulo-uasg).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=ORGAOS_DEFAULT_PAGE_SIZE,
        help=f"tamanhoPagina (default {ORGAOS_DEFAULT_PAGE_SIZE}).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limita páginas (smoke test). Default: sem limite.",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="Carrega de JSONL local em vez da API (uso em test/CI).",
    )
    parser.add_argument(
        "--inativos",
        action="store_true",
        help="Coleta órgãos inativos (statusOrgao=false) em vez de ativos.",
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
    status = "inativos" if args.inativos else "ativos"
    console.rule(f"[bold]Compras.gov.br /modulo-uasg[/] órgãos {status} ({mode})")

    def _progress(page: int, total_pages: int, orgaos_so_far: int) -> None:
        console.print(
            f"  pagina {page}/{total_pages or '?'}  orgaos acumulados: {orgaos_so_far}"
        )

    try:
        if args.fixture:
            result = ingest_orgaos_fixture(args.fixture, on_progress=_progress)
        else:
            result = ingest_orgaos(
                status_ativo=not args.inativos,
                page_size=args.page_size,
                max_pages=args.max_pages,
                on_progress=_progress,
            )
    except Exception as exc:
        console = Console()
        console.print(f"[red]ERRO:[/] {exc}")
        raise

    console.rule("[bold green]OK")
    console.print(f"  snapshot_id      : {result.snapshot_id}")
    console.print(f"  snapshot_path    : {result.snapshot_path}")
    console.print(f"  paginas          : {result.pages_fetched}")
    console.print(f"  orgaos total     : {result.orgaos_total}")
    console.print(f"  orgaos upserted  : {result.orgaos_upserted}")
    console.print(f"  sha256           : {result.hash_sha256[:16]}...")
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    # Dispatch subcomando 'orgaos' antes do parser legacy para não quebrar
    # o shape posicional (start, end) do ingest de contratos.
    if argv and argv[0] == "orgaos":
        return _run_orgaos(argv[1:])

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
        "--orgaos",
        type=str,
        default=None,
        help=(
            "'all' = todos os orgaos federais ativos (analytics.orgao_federal). "
            "Ou lista de codigos separada por virgula: '26298,20000'. "
            "Obrigatorio quando nao se usa --fixture (breaking change upstream, ver PLANO §19.11)."
        ),
    )
    parser.add_argument(
        "--orgaos-limit",
        type=int,
        default=None,
        help="Limita N primeiros orgaos quando --orgaos all (smoke test).",
    )
    parser.add_argument(
        "--no-split",
        action="store_true",
        help="Desativa window-splitting: cada orgao tenta a janela inteira de uma vez.",
    )
    parser.add_argument(
        "--min-window-days",
        type=int,
        default=1,
        help="Tamanho minimo da janela por orgao no split recursivo (default 1 = 1 dia).",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=settings.log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=False)],
    )

    console = Console()

    def _progress(page: int, total_pages: int, items_so_far: int) -> None:
        console.print(
            f"    pagina {page}/{total_pages or '?'}  itens acumulados: {items_so_far}"
        )

    def _window_event(event: str, ws, we, **kw) -> None:
        tag = {
            "start": "[dim]>>>",
            "ok":    "[green]OK ",
            "split": "[yellow]SPL",
            "fail":  "[red]FAIL",
            "fatal": "[red bold]FATAL",
        }.get(event, event)
        codigo = kw.get("codigo_orgao")
        prefix = f"orgao={codigo}  " if codigo is not None else ""
        extra = ""
        if event == "split" and "error" in kw:
            extra = f"  motivo: {kw['error'][:120]}"
        elif event == "fail" and "error" in kw:
            extra = f"  erro: {kw['error'][:120]}"
        elif event == "ok" and "result" in kw:
            r = kw["result"]
            extra = f"  paginas={r.pages_fetched} itens={r.items_inserted}"
        console.print(f"    {tag}[/] {prefix}{ws} -> {we}{extra}")

    def _orgao_event(event: str, codigo_orgao: int, **kw) -> None:
        idx = kw.get("idx", "?")
        total = kw.get("total", "?")
        if event == "start":
            console.print(f"[bold]>> orgao {codigo_orgao}[/]  ({idx}/{total})")
        elif event == "done":
            console.print(
                f"   [green]OK[/]  orgao {codigo_orgao}: "
                f"sub-janelas={kw.get('successes', 0)} falhas={kw.get('failures', 0)} "
                f"itens={kw.get('items', 0)}"
            )
        elif event == "fatal":
            console.print(
                f"   [red bold]FATAL[/]  orgao {codigo_orgao}: {kw.get('error', '')[:200]}"
            )

    # --- modo fixture: sem orgao, replay puro ---
    if args.fixture:
        console.rule(
            f"[bold]Compras.gov.br ingest[/] {args.start} -> {args.end} "
            f"(fixture={args.fixture})"
        )
        try:
            result = ingest_fixture(
                args.fixture,
                period_start=args.start,
                period_end=args.end,
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

    # --- modo live: precisa de --orgaos ---
    if args.orgaos is None:
        console.print(
            "[red]ERRO:[/] --orgaos é obrigatório no modo live "
            "(breaking change upstream — PLANO §19.11)."
        )
        console.print("Use [bold]--orgaos all[/] ou [bold]--orgaos 26298,20000[/].")
        return 2

    try:
        codigo_orgaos = _resolve_orgaos(args.orgaos, args.orgaos_limit)
    except (ValueError, RuntimeError) as exc:
        console.print(f"[red]ERRO:[/] {exc}")
        return 2

    # No-split = janela inteira por orgao (sem dividir por data).
    window_days = (args.end - args.start).days + 1
    min_window_days = window_days if args.no_split else args.min_window_days
    split_desc = "no-split" if args.no_split else f"split min={min_window_days}d"
    console.rule(
        f"[bold]Compras.gov.br ingest[/] {args.start} -> {args.end} "
        f"(API live, {len(codigo_orgaos)} orgaos, {split_desc})"
    )

    try:
        summary = ingest_by_orgaos(
            args.start,
            args.end,
            codigo_orgaos,
            page_size=args.page_size,
            max_pages=args.max_pages,
            min_window_days=min_window_days,
            on_progress=_progress,
            on_window_event=_window_event,
            on_orgao_event=_orgao_event,
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
    console.print(f"  orgaos rodados : {len(codigo_orgaos)}")
    console.print(f"  janelas OK     : {len(summary.successes)}")
    console.print(f"  janelas FAILED : {len(summary.failures)}")
    console.print(f"  paginas total  : {summary.pages_total}")
    console.print(f"  itens total    : {summary.items_total}")
    if summary.failures:
        console.print("  janelas com falha (primeiras 10):")
        for fw in summary.failures[:10]:
            console.print(
                f"    orgao={fw.codigo_orgao}  {fw.period_start} -> {fw.period_end}  "
                f"{fw.error[:120]}"
            )
        if len(summary.failures) > 10:
            console.print(f"    ... e mais {len(summary.failures) - 10}")
    # Exit codes: 0 = sucesso (total ou parcial); 2 = nada ingerido.
    return 0 if summary.has_any_success else 2


def _resolve_orgaos(spec: str, limit: int | None) -> list[int]:
    """Resolve o valor de --orgaos para uma lista de inteiros.

    'all' carrega de analytics.orgao_federal (esfera='F' + status_ativo).
    Senão, lista de códigos separada por vírgula.
    """
    if spec == "all":
        codigos = load_orgaos_ativos_federais(limit=limit)
        if not codigos:
            raise RuntimeError(
                "Nenhum orgao federal ativo em analytics.orgao_federal. "
                "Rode 'python -m ingest orgaos' primeiro para popular o cadastro."
            )
        return codigos

    if limit is not None:
        raise ValueError("--orgaos-limit só é válido com --orgaos all")

    try:
        codigos = [int(tok.strip()) for tok in spec.split(",") if tok.strip()]
    except ValueError as exc:
        raise ValueError(
            f"--orgaos invalido: {spec!r}. Use 'all' ou lista 'N,N,N' de inteiros."
        ) from exc
    if not codigos:
        raise ValueError("--orgaos não pode ser vazio")
    return codigos


if __name__ == "__main__":
    sys.exit(main())
