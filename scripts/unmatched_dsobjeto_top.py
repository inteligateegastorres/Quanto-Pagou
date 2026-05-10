"""Ranqueia descricoes de contrato sem cluster keyword (em quarentena).

Resolve critica externa (PLANO §17.B.2): 66% dos contratos TCE-PR caem
em quarentena por nao casar com nenhum cluster keyword. Sem visibilidade
sobre QUAIS, o YAML de cluster_keywords nao evolui.

Output: CSV ranqueado em `data/unmatched/top_dsobjeto.csv` com top N
descricoes normalizadas + n_contratos + valor_total + exemplo. PR no
YAML usa esse CSV pra escolher proximas keywords.

Uso:
    python -m uv run python scripts/unmatched_dsobjeto_top.py
    python -m uv run python scripts/unmatched_dsobjeto_top.py --top 500
    python -m uv run python scripts/unmatched_dsobjeto_top.py --out data/unmatched/custom.csv

CI: roda em ingest-weekly.yml como artifact (apos build_marts).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from rich.console import Console

from ingest.config import settings

# Prefixos comuns que poluem a normalizacao. Strip iterativamente ate chegar
# no substantivo. Cada padrao casa um "boilerplate" de inicio de objeto.
PREFIXOS_LIXO = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^[\(\)\.,;:\-/]+",  # pontuacao no inicio
        r"^sistema\s+de\s+registro\s+de\s+precos?\s+(\(srp\)\s+)?",
        r"^formacao\s+(de\s+)?registro\s+de\s+precos?\s+",
        r"^registro\s+de\s+precos?\s+",
        r"^para\s+(futura\s+(e\s+)?eventual\s+)?",
        r"^para\s+(possivel\s+(e\s+)?futur[ao]\s+)?",
        r"^pelo\s+periodo\s+de\s+",
        r"^visando\s+(a\s+|ao\s+)?",
        r"^o\s+objeto\s+(do\s+presente\s+)?(termo\s+)?refere-se\s+(a\s+|ao\s+)?",
        r"^o\s+presente\s+(termo\s+|contrato\s+)?(tem\s+por\s+objeto\s+)?",
        r"^contratacao\s+de\s+(empresa\s+(especializada\s+)?)?",
        r"^prestacao\s+de\s+servicos?\s+(especializados?\s+)?(de\s+|na\s+)?",
        r"^servicos?\s+(especializados?\s+)?de\s+",
        r"^aquisicao\s+(de\s+|do\s+|da\s+|dos\s+|das\s+)?",
        r"^fornecimento\s+(de\s+|parcelado\s+de\s+|continuo\s+de\s+)?",
        r"^locacao\s+(de\s+|do\s+)?",
        r"^aluguel\s+(de\s+|do\s+)?",
        r"<num>\.?\s+",  # numero solto no inicio
        r"^compra\s+(de\s+|do\s+)?",
        r"^execucao\s+(de\s+|dos\s+)?",
        r"^(para|na|no|com|em)\s+(o\s+|a\s+|os\s+|as\s+)?",
    ]
]

# Numeros + ordinais + datas + IDs viram <NUM> pra agrupar variantes.
NUMEROS = re.compile(r"\b\d+(?:[\.,]\d+)?\b")


def normalizar_descricao(desc: str, max_palavras: int = 8) -> str:
    """UPPERCASE, strip accents nao, mas:
    - remove prefixos lixo
    - substitui numeros por <NUM>
    - colapsa espacos
    - trunca em max_palavras palavras
    """
    s = desc.strip().lower()
    # Strip acentos antes pra regex casar "precos" e "preços" igual.
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = NUMEROS.sub("<num>", s)
    # Aplica cada regex iterativamente ate nao mudar mais (pra cascatear
    # "registro de precos > para futura eventual > aquisicao de" etc).
    for _ in range(8):
        anterior = s
        for pat in PREFIXOS_LIXO:
            s = pat.sub("", s).strip()
        if s == anterior:
            break
    s = re.sub(r"\s+", " ", s).strip()
    palavras = s.split()
    return " ".join(palavras[:max_palavras])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scripts/unmatched_dsobjeto_top.py")
    parser.add_argument("--top", type=int, default=200, help="Top N descricoes (default 200)")
    parser.add_argument(
        "--out",
        default="data/unmatched/top_dsobjeto.csv",
        help="Caminho do CSV (default data/unmatched/top_dsobjeto.csv)",
    )
    parser.add_argument(
        "--max-palavras",
        type=int,
        default=8,
        help="Truncar descricao normalizada em N palavras (default 8)",
    )
    args = parser.parse_args(argv)
    console = Console()
    console.rule("[bold]unmatched_dsobjeto_top[/]")

    # Pega so contratos TCE-PR em quarentena por sem_cluster_keyword.
    sql = """
        SELECT rc.descricao, rc.valor_total::numeric AS valor
        FROM raw.compras rc
        JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
        WHERE rc.source = 'tce_pr/contrato'
          AND ic.em_quarentena = TRUE
          AND ic.motivo_quarentena = 'sem_cluster_keyword'
          AND rc.descricao IS NOT NULL
    """

    # Agregador: nome_normalizado -> (n, valor_total, exemplo_original)
    agg: dict[str, dict] = defaultdict(lambda: {"n": 0, "valor": 0, "exemplo": None})

    n_lidos = 0
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            for row in cur:
                n_lidos += 1
                desc = row["descricao"]
                norm = normalizar_descricao(desc, args.max_palavras)
                if not norm:
                    continue
                a = agg[norm]
                a["n"] += 1
                a["valor"] += float(row["valor"] or 0)
                if a["exemplo"] is None:
                    a["exemplo"] = desc[:200]

    console.print(f"  {n_lidos:,} contratos em quarentena lidos".replace(",", "."))
    console.print(f"  {len(agg):,} grupos distintos apos normalizacao".replace(",", "."))

    # Top N por contagem
    top = sorted(agg.items(), key=lambda x: x[1]["n"], reverse=True)[: args.top]

    # Escreve CSV
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "n_contratos", "valor_total_brl", "descricao_normalizada", "exemplo_original"])
        for rank, (norm, data) in enumerate(top, start=1):
            w.writerow([rank, data["n"], f"{data['valor']:.2f}", norm, data["exemplo"]])

    console.print(f"\n[green]Top {args.top} salvo em {out_path}[/]")
    if top:
        console.print("\nAmostra (top 5):")
        for rank, (norm, data) in enumerate(top[:5], start=1):
            console.print(
                f"  #{rank}  n={data['n']:>5}  "
                f"R$ {data['valor']/1000:>10,.0f} mil  {norm}".replace(",", ".")
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
