"""Probe do extrator de nome de escola em descricao de contrato (TCE-PR).

Roda regex contra raw.compras (cluster obras_edificacao + outros) e
mostra os nomes capturados. Objetivo: validar se sao utilizaveis ou se
saem com lixo (ex: "Escola Municipal e Maria Augusta do Amaral Picelli").
"""

from __future__ import annotations

import re
import sys
from collections import Counter

sys.path.insert(0, "src")
import psycopg
from psycopg.rows import dict_row

from ingest.config import settings


# Tokens que sinalizam fim do nome da escola.
# Inclui " e " (conjuncao que comeca proxima entidade) e variantes de
# "atraves" (frequente em obras: "atraves da construcao de salas").
_END_TOKENS = (
    r"para\s+",
    r"do\s+munic[ií]pio",
    r"da\s+rede",
    r"conforme",
    r"localizada",
    r"sito",
    r"situada",
    r"com\s+area",
    r"com\s+especif",
    r"objeto\s+",
    r"atrav[eé]s",
    r"emendas?\s+impositiv",
    r"\sem\s+atendimento",
    r"\se\s+(?:cmei|cme|emef|emei|escola|col[eé]gio|centro\s+municipal|creche)",
    r"\se\s+da\s+escola",
    r"\sda\s+rede\s+p[uú]blica",
)
_END_LOOKAHEAD = r"(?=" + "|".join(_END_TOKENS) + r"|[,\.;:\(\)]|$)"

# Os padroes em ordem de especificidade. Primeiro que casa vence.
PADROES: list[tuple[str, re.Pattern[str]]] = [
    (
        "escola_municipal",
        re.compile(
            r"\b(?:escola|col[eé]gio)\s+(?:municipal|estadual)\s+(?P<nome>[A-ZÀ-Ý][\wÀ-ÿ\s]{2,80}?)"
            + _END_LOOKAHEAD,
            re.IGNORECASE,
        ),
    ),
    (
        "sigla_cmei",
        re.compile(
            r"\b(?P<sigla>cmei|cme|emef|emei|emeief|cmaee)\b\s+(?P<nome>[A-ZÀ-Ý][\wÀ-ÿ\s]{2,80}?)"
            + _END_LOOKAHEAD,
            re.IGNORECASE,
        ),
    ),
    (
        "centro_municipal",
        # "Centro Municipal de Educacao [Infantil] NOME" onde NOME comeca
        # com letra maiuscula e nao eh "infantil" (token fixo do prefixo).
        re.compile(
            r"\bcentro\s+(?:municipal\s+)?(?:de\s+)?educa[cç][aã]o\s+(?:infantil\s+)?(?P<nome>[A-ZÀ-Ý][\wÀ-ÿ\s]{2,80}?)"
            + _END_LOOKAHEAD,
            re.IGNORECASE,
        ),
    ),
    (
        "creche",
        re.compile(
            r"\bcreche\s+(?:municipal\s+)?(?P<nome>[A-ZÀ-Ý][\wÀ-ÿ\s]{2,80}?)"
            + _END_LOOKAHEAD,
            re.IGNORECASE,
        ),
    ),
]


_LIXO_INICIO = re.compile(
    r"^(?:infantil|prof|profa|professora?|sr|sra|dra?|me|sao|santa?)\s*$",
    re.IGNORECASE,
)
_LIXO_PALAVRAS_FUNCIONAIS = {
    "infantil", "prof", "profa", "professor", "professora",
    "rede", "ensino", "municipal", "estadual",
    "publica", "publico", "campo", "rural", "urbana",
}


def extrair(descricao: str) -> tuple[str, str] | None:
    """Devolve (padrao, nome_normalizado) ou None."""
    for padrao_id, regex in PADROES:
        m = regex.search(descricao)
        if not m:
            continue
        nome = m.group("nome").strip()
        nome = re.sub(r"\s+", " ", nome).strip(" -.,:;e")
        # Remove sufixos comuns que escapam do lookahead
        nome = re.sub(
            r"\s+(?:munic[ií]pio|estado|prefeitura|desta\s+municipalidade)\b.*$",
            "",
            nome,
            flags=re.IGNORECASE,
        )
        # Filtra "infantil" puro e variantes capturadas erroneamente
        if _LIXO_INICIO.match(nome):
            continue
        if len(nome) < 4 or len(nome) > 80:
            continue
        # Se primeiro token e palavra funcional sozinha, descarta
        primeiro = nome.split()[0].lower()
        if primeiro in _LIXO_PALAVRAS_FUNCIONAIS and len(nome.split()) < 2:
            continue
        # Se ultima palavra e conjuncao "e" sozinha, remove
        nome = re.sub(r"\s+e$", "", nome)
        if len(nome) < 4:
            continue
        return padrao_id, nome
    return None


def slugify(nome: str) -> str:
    s = nome.lower()
    # remove acentos basicos
    for a, b in [
        ("á", "a"), ("à", "a"), ("â", "a"), ("ã", "a"),
        ("é", "e"), ("ê", "e"),
        ("í", "i"),
        ("ó", "o"), ("ô", "o"), ("õ", "o"),
        ("ú", "u"), ("ü", "u"),
        ("ç", "c"),
    ]:
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80]


def main() -> None:
    sql = """
        SELECT rc.id, rc.descricao, ic.cluster_id, mp.nome AS municipio
        FROM raw.compras rc
        JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
        LEFT JOIN analytics.municipio_pr mp ON mp.cd_tce = rc.raw_payload->>'cd_tce'
        WHERE rc.source = 'tce_pr/contrato'
          AND ic.cluster_id IN (
              'obras_edificacao', 'transporte_escolar',
              'merenda_escolar', 'materiais_escolares'
          )
    """
    total = 0
    extraidos = 0
    padrao_counter: Counter[str] = Counter()
    slug_counter: Counter[str] = Counter()
    samples: list[tuple[str, str, str, str, str]] = []

    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            for row in cur:
                total += 1
                ext = extrair(row["descricao"])
                if ext is None:
                    continue
                padrao, nome = ext
                slug = slugify(nome)
                extraidos += 1
                padrao_counter[padrao] += 1
                slug_counter[slug] += 1
                if len(samples) < 30 and row["cluster_id"] == "obras_edificacao":
                    samples.append((row["cluster_id"], row["municipio"] or "?", padrao, nome, slug))

    print(f"Total candidatos (clusters relacionados a escola): {total}")
    print(f"Com escola extraida: {extraidos} ({100*extraidos/total:.1f}%)")
    print(f"\nPor padrao: {padrao_counter.most_common()}")
    print(f"\nNomes unicos (slugs): {len(slug_counter)}")
    print(f"\nTop 15 slugs (mais frequentes):")
    for slug, n in slug_counter.most_common(15):
        print(f"  {n:>3}x  {slug}")
    print(f"\n--- Samples obras_edificacao (30): ---")
    for cl, mun, pad, nome, slug in samples:
        print(f"  [{mun:<22}] [{pad:<18}] {nome!r}  ->  {slug}")


if __name__ == "__main__":
    main()
