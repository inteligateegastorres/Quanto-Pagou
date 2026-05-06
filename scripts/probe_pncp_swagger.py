"""Busca o spec OpenAPI/swagger do PNCP para listar TODOS os endpoints validos.

Salva em data/pncp_openapi.json (gitignore-able) e imprime os paths
relevantes para itens de contratacao.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

CANDIDATES = [
    "https://pncp.gov.br/api/consulta/v3/api-docs",
    "https://pncp.gov.br/api/consulta/v2/api-docs",
    "https://pncp.gov.br/api/consulta/api-docs",
    "https://pncp.gov.br/api/consulta/openapi.json",
    "https://pncp.gov.br/api/consulta/v3/api-docs/swagger-config",
    "https://pncp.gov.br/api/consulta/swagger-ui/swagger-config",
    # variantes sem /consulta
    "https://pncp.gov.br/api/v3/api-docs",
    "https://pncp.gov.br/v3/api-docs",
]


def main() -> None:
    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)

    spec = None
    found_url = None
    with httpx.Client(timeout=httpx.Timeout(60.0, connect=15.0)) as c:
        for url in CANDIDATES:
            t0 = time.monotonic()
            try:
                r = c.get(url, headers={"Accept": "application/json"})
            except Exception as e:
                print(f"  FAIL {type(e).__name__}: {e}  ({url})")
                continue
            print(f"  HTTP {r.status_code}  ({time.monotonic()-t0:.1f}s)  {url}")
            if r.status_code == 200:
                try:
                    data = r.json()
                except Exception:
                    print(f"    nao-json: {r.text[:200]!r}")
                    continue
                if "paths" in data or "openapi" in data or "swagger" in data:
                    spec = data
                    found_url = url
                    break

    if spec is None:
        print("Nao achei spec. Saindo.")
        return

    out_file = out_dir / "pncp_openapi.json"
    out_file.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nSpec salvo em {out_file}  ({out_file.stat().st_size} bytes)")
    print(f"Origem: {found_url}")
    print(f"Versao: {spec.get('info',{}).get('version')!r}")
    print(f"Title : {spec.get('info',{}).get('title')!r}")

    # Lista paths que mencionam 'item' ou 'compra' ou 'contrato'
    paths = spec.get("paths") or {}
    print(f"\nTotal de paths: {len(paths)}")
    print("\nPaths relevantes (contem 'item', 'compra' ou 'contrato'):")
    for path in sorted(paths.keys()):
        low = path.lower()
        if any(k in low for k in ("item", "compra", "contrato")):
            methods = list((paths[path] or {}).keys())
            # Pega primeiro summary
            summary = ""
            for m in methods:
                op = paths[path].get(m) or {}
                if isinstance(op, dict) and op.get("summary"):
                    summary = op["summary"]
                    break
            print(f"  {','.join(methods).upper():<10} {path}  — {summary}")


if __name__ == "__main__":
    main()
