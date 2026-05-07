"""CLI para ingest TCE-PR.

Uso:
    # Sample (Curitiba apenas, 2026, ZIP local ja baixado)
    python -m uv run python scripts/run_tce_pr.py \
        --ano 2026 \
        --zip .dev/tce_pr_sample/2026_PIT.zip \
        --municipios 410690

    # Ano completo (baixa do TCE-PR)
    python -m uv run python scripts/run_tce_pr.py --ano 2025

    # Ano completo a partir de ZIP ja baixado
    python -m uv run python scripts/run_tce_pr.py \
        --ano 2025 --zip /path/to/2025_PIT.zip
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from ingest.config import settings
from ingest.tce_pr import _MunicipioStats, ingest_year


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_tce_pr")
    parser.add_argument("--ano", type=int, required=True, help="Ano do ZIP (ex: 2025)")
    parser.add_argument(
        "--zip",
        type=Path,
        default=None,
        help="Caminho do ZIP anual (se ausente, baixa de pit.tce.pr.gov.br)",
    )
    parser.add_argument(
        "--municipios",
        nargs="*",
        default=None,
        help="Codigos TCE-PR de municipios a processar (default: todos 399). Ex: 410690 411370",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suprime log por municipio"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=settings.log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=False)],
    )

    console = Console()
    municipios_str = ",".join(args.municipios) if args.municipios else "todos"
    console.rule(f"[bold]TCE-PR ingest[/] ano={args.ano} municipios={municipios_str}")

    def _on_municipio(stats: _MunicipioStats) -> None:
        if args.quiet:
            return
        if stats.n_contratos > 0:
            console.print(
                f"  [green]OK[/]  cd_tce={stats.cd_tce}  contratos={stats.n_contratos}"
            )
        elif stats.error:
            console.print(
                f"  [red]FAIL[/]  cd_tce={stats.cd_tce}  {stats.error[:120]}"
            )
        else:
            console.print(f"  [dim]vazio[/]  cd_tce={stats.cd_tce}")

    try:
        result = ingest_year(
            args.ano,
            year_zip_path=args.zip,
            municipios=args.municipios,
            on_municipio=_on_municipio,
        )
    except Exception as exc:
        console.print(f"[red]ERRO:[/] {exc}")
        raise

    console.rule("[bold green]OK")
    console.print(f"  snapshot_id        : {result.snapshot_id}")
    console.print(f"  ano                : {result.ano}")
    console.print(f"  municipios proc.   : {result.municipios_processados}")
    console.print(f"  contratos inseridos: {result.contratos_inseridos}")
    console.print(f"  sha256             : {result.hash_sha256[:16]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
