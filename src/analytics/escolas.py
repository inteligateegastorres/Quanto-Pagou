"""Extrator de menções de escola/CMEI/creche em descrição livre de contrato.

Para o caminho 1 do plano de obras escolares (catálogo de transparência —
não ranking). Cobertura medida em 2026-05-07: ~270 contratos no PR
todo (0.17% do total) onde nome próprio de instituição educacional é
extraível por regex. Concentrado em obras_edificacao (29% do cluster).

Filosofia: aceitar ruído visível em troca de auditoria. Se o slug não
parece nome próprio (começa com 'e-', começa com 'centro-municipal-',
é palavra funcional pura), pula. Outros lixos saem na UI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

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
    r"\s+e\s+(?:cmei|cme|emef|emei|escola|col[eé]gio|centro\s+municipal|creche)",
    r"\s+e\s+da\s+escola",
    r"\s+da\s+rede\s+p[uú]blica",
)
_END_LOOKAHEAD = r"(?=" + "|".join(_END_TOKENS) + r"|[,\.;:\(\)]|$)"

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

# Palavras que sozinhas não viram nome de escola (sao tokens funcionais).
_LIXO_PALAVRAS = {
    "infantil", "prof", "profa", "professor", "professora",
    "rede", "ensino", "municipal", "estadual",
    "publica", "publico", "campo", "rural", "urbana",
    "desta", "municipalidade",
}

# Slugs que claramente nao representam escola individual.
_SLUG_LIXO_PREFIXES = (
    "e-",                              # "e Centro Municipal..." consumido
    "centro-municipal-de-",            # entidade ampla nao individual
    "centro-de-",
    "da-rede-",
    "do-",
    "desta-",
)


@dataclass(slots=True, frozen=True)
class EscolaMencao:
    nome: str
    slug: str
    padrao: str  # qual regex casou (auditoria)


def _slugify(nome: str) -> str:
    s = nome.lower()
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


def extrair_escola(descricao: str) -> EscolaMencao | None:
    """Devolve a primeira menção de escola identificada na descrição,
    ou None se nenhum padrão casa ou se o resultado é claramente lixo."""
    if not descricao:
        return None
    for padrao_id, regex in PADROES:
        m = regex.search(descricao)
        if not m:
            continue
        nome = m.group("nome").strip()
        nome = re.sub(r"\s+", " ", nome).strip(" -.,:;e")
        nome = re.sub(
            r"\s+(?:munic[ií]pio|estado|prefeitura|desta\s+municipalidade)\b.*$",
            "",
            nome,
            flags=re.IGNORECASE,
        )
        nome = re.sub(r"\s+e$", "", nome)  # conjuncao orfa
        if not nome or len(nome) < 4 or len(nome) > 80:
            continue
        # Tokens funcionais sozinhos
        tokens = nome.lower().split()
        if len(tokens) == 1 and tokens[0] in _LIXO_PALAVRAS:
            continue
        # Slug heuristics
        slug = _slugify(nome)
        if not slug or len(slug) < 4:
            continue
        if any(slug.startswith(p) for p in _SLUG_LIXO_PREFIXES):
            continue
        return EscolaMencao(nome=nome, slug=slug, padrao=padrao_id)
    return None
