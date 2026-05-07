"""Resolucao Tier 1 (CATMAT direto + golden set) + parser textual de unidade.

Progressive correctness: nada de embeddings/LLM aqui. Tier 2-4 entram em fases
posteriores. O objetivo deste modulo e ser auditavel e barato - se um item
nao casa, vai para quarentena com motivo legivel; nunca soma do site.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


# ----------------------------- estruturas ------------------------------


@dataclass(slots=True, frozen=True)
class GoldenCluster:
    cluster_id: str
    cluster_version: str
    categoria: str
    descricao_canonica: str
    catmat_ids: tuple[str, ...]


@dataclass(slots=True)
class UnitMatch:
    unidade_base: str
    qtd_em_unidade_base: float  # quantidade da embalagem em unidade-base
    metodo: str                 # 'pattern:<i>' | 'default_categoria' | 'aliases'
    fator_inferido: bool


@dataclass(slots=True)
class Resolution:
    cluster_id: str | None
    cluster_version: str | None
    categoria: str | None
    metodo_resolucao: str            # 'tier1_catmat_golden' | 'tier1_catmat_sintetico' | 'sem_cluster'
    confianca_resolucao: float       # 0.0 - 1.0
    descricao_canonica: str | None


# ----------------------------- loaders ---------------------------------


def load_golden_set(
    path: Path | None = None,
) -> tuple[dict[str, GoldenCluster], list[GoldenCluster]]:
    """Carrega golden set core. Retorna (catmat_id -> cluster, [todos os clusters]).

    Um catmat_id em mais de uma linha do golden e considerado o mesmo cluster
    (varias variacoes de descricao apontam para o mesmo cluster_id).
    """
    p = path or DATA_DIR / "golden_set" / "core_v1.csv"
    by_catmat: dict[str, GoldenCluster] = {}
    by_cluster: dict[tuple[str, str], dict[str, Any]] = {}

    with p.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            key = (row["cluster_id"], row["cluster_version"])
            entry = by_cluster.setdefault(
                key,
                {
                    "cluster_id": row["cluster_id"],
                    "cluster_version": row["cluster_version"],
                    "categoria": row["categoria"],
                    "descricao_canonica": row["descricao_original"],
                    "catmat_ids": set(),
                },
            )
            if row.get("catmat_id"):
                entry["catmat_ids"].add(str(row["catmat_id"]).strip())

    clusters: list[GoldenCluster] = []
    for entry in by_cluster.values():
        gc = GoldenCluster(
            cluster_id=entry["cluster_id"],
            cluster_version=entry["cluster_version"],
            categoria=entry["categoria"],
            descricao_canonica=entry["descricao_canonica"],
            catmat_ids=tuple(sorted(entry["catmat_ids"])),
        )
        clusters.append(gc)
        for cm in gc.catmat_ids:
            by_catmat[cm] = gc

    return by_catmat, clusters


def load_unit_conversion(path: Path | None = None) -> dict[str, Any]:
    p = path or CONFIG_DIR / "unit_conversion.yaml"
    with p.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# Cluster por keyword (Tier 1.5) — usado para fontes municipais/estaduais que
# nao publicam CATMAT, so descricao livre (ex: TCE-PR dsObjeto). Ordem importa
# (primeiro pattern que casa vence).


@dataclass(slots=True, frozen=True)
class KeywordCluster:
    cluster_id: str
    cluster_version: str
    descricao_canonica: str
    categoria: str
    patterns: tuple[re.Pattern[str], ...]


def load_keyword_clusters(path: Path | None = None) -> list[KeywordCluster]:
    """Carrega config/cluster_keywords.yaml. Compila regexes case-insensitive
    com flag re.UNICODE; o caller normaliza a descricao para upper antes."""
    p = path or CONFIG_DIR / "cluster_keywords.yaml"
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    out: list[KeywordCluster] = []
    for entry in data.get("clusters") or []:
        compiled = tuple(
            re.compile(pat, re.IGNORECASE | re.UNICODE)
            for pat in entry.get("patterns") or []
        )
        out.append(
            KeywordCluster(
                cluster_id=entry["cluster_id"],
                cluster_version=entry["cluster_version"],
                descricao_canonica=entry["descricao_canonica"],
                categoria=entry["categoria"],
                patterns=compiled,
            )
        )
    return out


def resolve_cluster_by_keyword(
    descricao: str,
    keyword_clusters: list[KeywordCluster],
) -> Resolution:
    """Tier 1.5: cluster por keyword em descricao livre.

    Confianca fixa em 0.6 (entre CATMAT direto = 1.0 e nada = 0.0). Primeira
    regra que casa vence — ordem do YAML define prioridade.
    """
    if not descricao:
        return Resolution(
            cluster_id=None,
            cluster_version=None,
            categoria=None,
            metodo_resolucao="sem_cluster",
            confianca_resolucao=0.0,
            descricao_canonica=None,
        )
    for kc in keyword_clusters:
        for pat in kc.patterns:
            if pat.search(descricao):
                return Resolution(
                    cluster_id=kc.cluster_id,
                    cluster_version=kc.cluster_version,
                    categoria=kc.categoria,
                    metodo_resolucao="tier1_keyword_dsobjeto",
                    confianca_resolucao=0.60,
                    descricao_canonica=kc.descricao_canonica,
                )
    return Resolution(
        cluster_id=None,
        cluster_version=None,
        categoria=None,
        metodo_resolucao="sem_cluster",
        confianca_resolucao=0.0,
        descricao_canonica=None,
    )


# ----------------------------- resolucao -------------------------------


def resolve_cluster(
    catmat_id: str | None,
    golden_by_catmat: dict[str, GoldenCluster],
) -> Resolution:
    """Tier 1 apenas (CATMAT direto). Tier 2+ entram em fases futuras."""
    if catmat_id:
        cm = str(catmat_id).strip()
        if cm in golden_by_catmat:
            gc = golden_by_catmat[cm]
            return Resolution(
                cluster_id=gc.cluster_id,
                cluster_version=gc.cluster_version,
                categoria=gc.categoria,
                metodo_resolucao="tier1_catmat_golden",
                confianca_resolucao=1.00,
                descricao_canonica=gc.descricao_canonica,
            )
        # CATMAT existe mas fora do golden: cluster sintetico, alta confianca
        # (CATMAT e canonico oficial), mas categoria desconhecida.
        return Resolution(
            cluster_id=f"catmat_{cm}",
            cluster_version="v1",
            categoria="desconhecida",
            metodo_resolucao="tier1_catmat_sintetico",
            confianca_resolucao=0.85,
            descricao_canonica=None,
        )
    # Sem CATMAT: Tier 2-4 ainda nao existem, so resta quarentena.
    return Resolution(
        cluster_id=None,
        cluster_version=None,
        categoria=None,
        metodo_resolucao="sem_cluster",
        confianca_resolucao=0.0,
        descricao_canonica=None,
    )


# ----------------------------- unidade ---------------------------------


def _compile_patterns(conv: dict[str, Any]) -> list[tuple[re.Pattern[str], dict]]:
    out = []
    for entry in conv.get("patterns", []):
        out.append((re.compile(entry["regex"]), entry))
    return out


def parse_unit(
    descricao: str,
    categoria: str | None,
    conv: dict[str, Any],
    _compiled: list[tuple[re.Pattern[str], dict]] | None = None,
) -> UnitMatch | None:
    """Aplica patterns na descricao em UPPER, devolve primeiro match.

    Cai para defaults_por_categoria se nada bater.
    Retorna None se nao houver default para a categoria.
    """
    if not descricao:
        descricao = ""
    upper = descricao.upper()

    patterns = _compiled if _compiled is not None else _compile_patterns(conv)
    for idx, (pat, entry) in enumerate(patterns):
        m = pat.search(upper)
        if not m:
            continue
        multiplicador = float(entry.get("multiplicador", 1.0))
        if "qtd_fixa" in entry:
            qtd = float(entry["qtd_fixa"])
        else:
            try:
                qtd = float(m.group("qtd").replace(",", "."))
            except (IndexError, ValueError):
                continue
        qtd_em_base = qtd * multiplicador
        if qtd_em_base <= 0:
            continue
        return UnitMatch(
            unidade_base=entry["unidade_base"],
            qtd_em_unidade_base=qtd_em_base,
            metodo=f"pattern:{idx}",
            fator_inferido=False,
        )

    # Fallback por categoria.
    defaults = conv.get("defaults_por_categoria") or {}
    if categoria and categoria in defaults:
        d = defaults[categoria]
        return UnitMatch(
            unidade_base=d["unidade_base"],
            qtd_em_unidade_base=float(d["qtd"]),
            metodo="default_categoria",
            fator_inferido=True,
        )
    return None


# ----------------------------- ente / uf / porte -----------------------


def derive_ente(raw_payload: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    """Mapeia raw_payload para (ente_nivel, uf, porte).

    Para Fase 1 federal: esfera 'F' -> ('federal', 'DF', 'federal_central').
    Estaduais/municipais entram em Fase 2-3.
    """
    esfera = (raw_payload.get("esfera") or "").upper()
    if esfera == "F":
        return ("federal", "DF", "federal_central")
    if esfera == "E":
        return ("estadual", None, None)
    if esfera == "M":
        return ("municipal", None, None)
    return (None, None, None)


# ----------------------------- canonicalize ----------------------------


@dataclass(slots=True)
class CanonicalRow:
    raw_id: int
    cluster_id: str | None
    cluster_version: str | None
    metodo_resolucao: str
    confianca_resolucao: float
    unidade_label: str | None
    unidade_base: str | None
    fator_conversao: float | None  # qtd_em_unidade_base capturada
    valor_unitario_normalizado: float | None
    ente_nivel: str | None
    uf: str | None
    porte: str | None
    em_quarentena: bool
    motivo_quarentena: str | None


def canonicalize(
    raw_row: dict[str, Any],
    golden_by_catmat: dict[str, GoldenCluster],
    conv: dict[str, Any],
    _compiled: list[tuple[re.Pattern[str], dict]] | None = None,
) -> CanonicalRow:
    """Resolve cluster + parseia unidade + deriva ente/uf/porte para uma linha."""
    raw_id = int(raw_row["id"])
    catmat = raw_row.get("catmat_id")
    descricao = raw_row.get("descricao") or ""
    valor_unit = raw_row.get("valor_unitario")
    raw_payload = raw_row.get("raw_payload") or {}

    res = resolve_cluster(catmat, golden_by_catmat)

    em_quarentena = False
    motivos: list[str] = []
    if res.cluster_id is None:
        em_quarentena = True
        motivos.append("sem_catmat_e_sem_resolucao")

    unit = parse_unit(descricao, res.categoria, conv, _compiled=_compiled)
    unidade_base = unit.unidade_base if unit else None
    qtd_base = unit.qtd_em_unidade_base if unit else None
    confianca = res.confianca_resolucao

    if unit is None:
        em_quarentena = True
        motivos.append("sem_unidade_detectada")
    elif unit.fator_inferido:
        # Penaliza confianca, mas item ainda comparavel.
        confianca = max(0.0, confianca - 0.10)

    ente_nivel, uf, porte = derive_ente(raw_payload)

    valor_norm: float | None = None
    if valor_unit is not None and qtd_base and qtd_base > 0:
        try:
            valor_norm = float(valor_unit) / qtd_base
        except (TypeError, ValueError):
            em_quarentena = True
            motivos.append("valor_unitario_invalido")

    if valor_norm is None and not em_quarentena:
        em_quarentena = True
        motivos.append("valor_unitario_normalizado_nulo")

    return CanonicalRow(
        raw_id=raw_id,
        cluster_id=res.cluster_id,
        cluster_version=res.cluster_version,
        metodo_resolucao=res.metodo_resolucao,
        confianca_resolucao=round(confianca, 2),
        unidade_label=unit.metodo if unit else None,
        unidade_base=unidade_base,
        fator_conversao=qtd_base,
        valor_unitario_normalizado=(
            round(valor_norm, 6) if valor_norm is not None else None
        ),
        ente_nivel=ente_nivel,
        uf=uf,
        porte=porte,
        em_quarentena=em_quarentena,
        motivo_quarentena=";".join(motivos) if motivos else None,
    )


def canonicalize_tce_pr_row(
    raw_row: dict[str, Any],
    keyword_clusters: list[KeywordCluster],
) -> CanonicalRow:
    """Canonicalizacao para fontes TCE-PR (granularidade contrato).

    Diferenca-chave vs `canonicalize()` federal:
      - Cluster vem de keyword em descricao (Tier 1.5), nao CATMAT.
      - `unidade_base = 'contrato'`, `fator_conversao = 1.0`.
      - `valor_unitario_normalizado = valor_total` (1 contrato = 1 unidade).
      - Itens sem cluster vao para quarentena com motivo legivel.
      - Ente_nivel/uf/porte sao fixos (municipal/PR/None) — porte fica para
        o SQL resolver via JOIN com analytics.municipio_pr.
    """
    raw_id = int(raw_row["id"])
    descricao = raw_row.get("descricao") or ""
    valor_total = raw_row.get("valor_total")

    res = resolve_cluster_by_keyword(descricao, keyword_clusters)

    em_quarentena = res.cluster_id is None
    motivos: list[str] = []
    if em_quarentena:
        motivos.append("sem_cluster_keyword")

    valor_norm: float | None = None
    if valor_total is not None:
        try:
            valor_norm = float(valor_total)
        except (TypeError, ValueError):
            em_quarentena = True
            motivos.append("valor_total_invalido")

    return CanonicalRow(
        raw_id=raw_id,
        cluster_id=res.cluster_id,
        cluster_version=res.cluster_version,
        metodo_resolucao=res.metodo_resolucao,
        confianca_resolucao=res.confianca_resolucao,
        unidade_label="contrato",
        unidade_base="contrato",
        fator_conversao=1.0,
        valor_unitario_normalizado=valor_norm,
        ente_nivel="municipal",
        uf="PR",
        porte=None,  # resolvido no SQL via JOIN com analytics.municipio_pr
        em_quarentena=em_quarentena,
        motivo_quarentena=";".join(motivos) if motivos else None,
    )
