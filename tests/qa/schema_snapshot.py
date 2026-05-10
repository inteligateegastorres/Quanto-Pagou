"""Snapshot de schemas de endpoints REST + check de drift.

Resolve a classe inteira de findings F-001/F-004/F-009/F-015 (drift entre
CHECKLIST e API) preventivamente. Roda em CI ou manual.

Uso:
    # Captura snapshot atual e grava em tests/qa/snapshots/
    python -m uv run python tests/qa/schema_snapshot.py update

    # Compara API atual vs snapshot, falha (exit 1) se mudou
    python -m uv run python tests/qa/schema_snapshot.py check

Cada endpoint -> tests/qa/snapshots/{path_normalizado}.json com:
    {
      "endpoint": "...",
      "method": "GET",
      "shape": { "type": "object" | "list[object]", "keys": [...] }
    }

NAO captura conteudo (so o shape) — drift de schema, nao de dados.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx

API_DEFAULT = "http://127.0.0.1:8001"
SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"

# Endpoints estaticos (sem dependencia de parametro descoberto).
STATIC: list[tuple[str, str]] = [
    ("/health", "/health"),
    ("/stats/pr", "/stats/pr"),
    ("/clusters", "/clusters"),
    ("/quarentena/resumo", "/quarentena/resumo"),
    ("/pares?cluster_id=oleo_diesel_s10", "/pares"),
    ("/ranking/orgaos?cluster_id=oleo_diesel_s10", "/ranking_orgaos"),
    ("/municipios?limit=1", "/municipios"),
    ("/fornecedores?limit=1", "/fornecedores"),
    ("/escolas?limit=1", "/escolas"),
    ("/tce-pr/dispensas/top-fornecedores?limit=1", "/tce-pr_dispensas_top-fornecedores"),
    ("/instituicoes/search?q=hospital&limit=1", "/instituicoes_search"),
    ("/contratos/search?limit=1", "/contratos_search"),
    ("/municipio/4106902/info", "/municipio_info"),
    ("/tce-pr/municipio/4106902/resumo", "/tce-pr_municipio_resumo"),
    ("/tce-pr/municipio/4106902/contratos-por-cluster?limit=1", "/tce-pr_municipio_contratos-por-cluster"),
    ("/tce-pr/municipio/4106902/fornecedores?limit=1", "/tce-pr_municipio_fornecedores"),
    ("/tce-pr/cluster/merenda_escolar/comparacao-municipios?limit=1", "/tce-pr_cluster_comparacao-municipios"),
    ("/tce-pr/cluster/merenda_escolar/ranking-municipios?limit=1", "/tce-pr_cluster_ranking-municipios"),
    ("/manchetes", "/manchetes"),
    ("/manchetes/saidas", "/manchetes_saidas"),
    ("/manchetes/diagnostico?cd_tce=410690", "/manchetes_diagnostico"),
    ("/eliminacoes/publicas", "/eliminacoes_publicas"),
]


def shape_of(obj: Any) -> dict[str, Any]:
    """Captura o shape (top-level keys) de um JSON.

    - dict: {"type": "object", "keys": [...]}
    - list de dict: {"type": "list[object]", "keys": [...] do primeiro item}
    - list vazia: {"type": "list[unknown]", "keys": []}
    """
    if isinstance(obj, dict):
        return {"type": "object", "keys": sorted(obj.keys())}
    if isinstance(obj, list):
        if not obj:
            return {"type": "list[unknown]", "keys": []}
        if isinstance(obj[0], dict):
            return {"type": "list[object]", "keys": sorted(obj[0].keys())}
        return {"type": "list[scalar]", "keys": []}
    return {"type": type(obj).__name__, "keys": []}


def fetch_endpoints(api_base: str) -> dict[str, dict[str, Any]]:
    """Busca todos os endpoints, retorna dict { snapshot_filename: { endpoint, shape } }.

    Endpoints com dependencia dinamica (cnpj, raw_id) sao descobertos a
    partir de outros endpoints — isto e best-effort.
    """
    out: dict[str, dict[str, Any]] = {}

    # Estaticos
    for path, snap_name in STATIC:
        try:
            r = httpx.get(f"{api_base}{path}", timeout=15.0)
            r.raise_for_status()
            out[snap_name] = {
                "endpoint": path,
                "method": "GET",
                "shape": shape_of(r.json()),
            }
        except httpx.HTTPError as e:
            out[snap_name] = {"endpoint": path, "method": "GET", "error": str(e)}

    # Dinamicos: descobre CNPJ via /fornecedores
    try:
        r = httpx.get(f"{api_base}/fornecedores?limit=1", timeout=10.0)
        cnpj = r.json()[0]["fornecedor_cnpj"] if r.json() else None
    except (httpx.HTTPError, KeyError, IndexError):
        cnpj = None

    if cnpj:
        for path_tmpl, snap_name in [
            (f"/fornecedor/{cnpj}", "/fornecedor_perfil"),
            (f"/fornecedor/{cnpj}/por-orgao?limit=1", "/fornecedor_por-orgao"),
            (f"/fornecedor/{cnpj}/por-municipio?limit=1", "/fornecedor_por-municipio"),
            (f"/fornecedor/{cnpj}/por-categoria", "/fornecedor_por-categoria"),
            (f"/fornecedor/{cnpj}/por-modalidade", "/fornecedor_por-modalidade"),
            (f"/fornecedor/{cnpj}/contratos?limit=1", "/fornecedor_contratos"),
        ]:
            try:
                r = httpx.get(f"{api_base}{path_tmpl}", timeout=10.0)
                r.raise_for_status()
                out[snap_name] = {
                    "endpoint": path_tmpl.replace(cnpj, "{cnpj}"),
                    "method": "GET",
                    "shape": shape_of(r.json()),
                }
            except httpx.HTTPError as e:
                out[snap_name] = {"endpoint": path_tmpl, "method": "GET", "error": str(e)}

    # Dinamicos: descobre raw_id via /contratos/search
    try:
        r = httpx.get(f"{api_base}/contratos/search?limit=1", timeout=10.0)
        raw_id = r.json()["contratos"][0]["raw_id"] if r.json().get("contratos") else None
    except (httpx.HTTPError, KeyError, IndexError):
        raw_id = None

    if raw_id:
        for path_tmpl, snap_name in [
            (f"/item/{raw_id}", "/item"),
            (f"/contrato/{raw_id}", "/contrato"),
        ]:
            try:
                r = httpx.get(f"{api_base}{path_tmpl}", timeout=10.0)
                r.raise_for_status()
                out[snap_name] = {
                    "endpoint": path_tmpl.replace(str(raw_id), "{raw_id}"),
                    "method": "GET",
                    "shape": shape_of(r.json()),
                }
            except httpx.HTTPError as e:
                out[snap_name] = {"endpoint": path_tmpl, "method": "GET", "error": str(e)}

    # Dinamico: escola slug
    try:
        r = httpx.get(f"{api_base}/escolas?limit=1", timeout=10.0)
        slug = r.json()[0]["escola_slug"] if r.json() else None
    except (httpx.HTTPError, KeyError, IndexError):
        slug = None
    if slug:
        try:
            r = httpx.get(f"{api_base}/escolas/{slug}/contratos?limit=1", timeout=10.0)
            r.raise_for_status()
            out["/escolas_contratos"] = {
                "endpoint": "/escolas/{slug}/contratos",
                "method": "GET",
                "shape": shape_of(r.json()),
            }
        except httpx.HTTPError as e:
            out["/escolas_contratos"] = {"endpoint": "/escolas/{slug}/contratos", "method": "GET", "error": str(e)}

    return out


def normalize_filename(snap_name: str) -> str:
    return snap_name.lstrip("/").replace("/", "_") + ".json"


def cmd_update(api_base: str) -> int:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    out = fetch_endpoints(api_base)
    for snap_name, payload in out.items():
        path = SNAPSHOTS_DIR / normalize_filename(snap_name)
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")
    print(f"Wrote {len(out)} snapshots to {SNAPSHOTS_DIR}")
    return 0


def cmd_check(api_base: str) -> int:
    if not SNAPSHOTS_DIR.exists():
        print(f"No snapshots in {SNAPSHOTS_DIR} — run 'update' first")
        return 1
    current = fetch_endpoints(api_base)
    drift_count = 0
    for snap_name, current_payload in current.items():
        path = SNAPSHOTS_DIR / normalize_filename(snap_name)
        if not path.exists():
            print(f"NEW endpoint (no baseline): {snap_name} -> {current_payload['endpoint']}")
            drift_count += 1
            continue
        with path.open(encoding="utf-8") as f:
            baseline = json.load(f)
        if baseline.get("shape") != current_payload.get("shape"):
            print(f"DRIFT in {snap_name} ({current_payload['endpoint']})")
            print(f"  baseline: {baseline.get('shape')}")
            print(f"  current : {current_payload.get('shape')}")
            drift_count += 1
    if drift_count == 0:
        print(f"OK — {len(current)} endpoints sem drift")
        return 0
    print(f"\n{drift_count} drift(s) detectado(s). Atualize o CHECKLIST e rode 'update' apos revisar.")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tests/qa/schema_snapshot.py")
    parser.add_argument("cmd", choices=["update", "check"])
    parser.add_argument("--api", default=API_DEFAULT)
    args = parser.parse_args(argv)
    if args.cmd == "update":
        return cmd_update(args.api)
    return cmd_check(args.api)


if __name__ == "__main__":
    sys.exit(main())
