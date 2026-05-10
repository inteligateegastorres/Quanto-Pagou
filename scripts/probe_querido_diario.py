"""Probe Querido Diario — descobrir cobertura de Curitiba e estrutura.

Querido Diario (OKBR) extrai diarios oficiais municipais e expoe via API.
Documentacao: https://queridodiario.ok.org.br/api/docs

Objetivo:
1. Confirmar que API responde
2. Verificar se Curitiba (territory IBGE = 4106902) esta coberta
3. Capturar amostra do payload (PDF? JSON? text?)
4. Avaliar se da pra extrair item-a-item de contratos ou se e so texto livre
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

BASE = "https://queridodiario.ok.org.br/api"
CURITIBA_IBGE = "4106902"  # codigo IBGE de Curitiba/PR


def get(client: httpx.Client, path: str, **params: object) -> dict | None:
    t0 = time.monotonic()
    try:
        r = client.get(BASE + path, params=params, timeout=httpx.Timeout(60.0))
    except Exception as e:
        print(f"  FAIL {type(e).__name__}: {e}")
        return None
    elapsed = time.monotonic() - t0
    print(f"  HTTP {r.status_code}  ({elapsed:.1f}s)  bytes={len(r.content)}")
    if r.status_code != 200:
        print(f"    body: {r.text[:300]!r}")
        return None
    try:
        return r.json()
    except Exception:
        print(f"    nao-json: {r.text[:200]!r}")
        return None


def main() -> None:
    out_dir = Path("data/fixtures")
    out_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client(headers={"Accept": "application/json"}) as c:
        print(f"=== {BASE}")

        print("\n[1] /cities — Curitiba listada?")
        cities = get(c, "/cities", territory_id=CURITIBA_IBGE)
        if cities:
            print(f"  {json.dumps(cities, ensure_ascii=False)[:400]}")

        print("\n[2] /cities — busca por nome 'Curitiba'")
        cities2 = get(c, "/cities", city_name="Curitiba", level=1)
        if cities2:
            print(f"  cidades retornadas: {len(cities2.get('cities', []))}")
            for cidade in (cities2.get("cities") or [])[:5]:
                print(f"  {cidade.get('territory_id')} {cidade.get('territory_name')} {cidade.get('state_code')}")

        print("\n[3] /gazettes — busca diarios de Curitiba (ultimos 30d)")
        gazettes = get(
            c,
            "/gazettes",
            territory_ids=CURITIBA_IBGE,
            since="2026-04-01",
            until="2026-05-01",
            size=5,
        )
        if gazettes:
            total = gazettes.get("total_gazettes")
            items = gazettes.get("gazettes") or []
            print(f"  total_gazettes: {total}, items aqui: {len(items)}")
            for g in items[:3]:
                print("\n  GAZETTE")
                print(f"    territory_id : {g.get('territory_id')}")
                print(f"    territory_name: {g.get('territory_name')}")
                print(f"    date         : {g.get('date')}")
                print(f"    edition      : {g.get('edition')}")
                print(f"    is_extra     : {g.get('is_extra_edition')}")
                print(f"    pdf_url      : {g.get('url')}")
                print(f"    file_raw_txt : {g.get('file_raw_txt_url') or '—'}")
                # textual preview se houver
                content = g.get("excerpts") or g.get("text_content") or ""
                if content:
                    print(f"    excerpt      : {str(content)[:200]!r}")

        print("\n[4] /gazettes/full_text — busca textual em Curitiba por 'merenda'")
        # Endpoint full text com query semantica
        ft = get(
            c,
            "/gazettes",
            territory_ids=CURITIBA_IBGE,
            since="2026-01-01",
            until="2026-05-01",
            querystring="merenda escolar",
            size=3,
        )
        if ft:
            items = ft.get("gazettes") or []
            print(f"  hits para 'merenda escolar' em Curitiba: {len(items)}")
            for g in items[:2]:
                excerpts = g.get("excerpts") or []
                if excerpts:
                    print(f"  excerpt[0]: {str(excerpts[0])[:300]!r}")

        # Salva amostra
        if cities or gazettes:
            sample = {
                "cities_by_id": cities,
                "cities_by_name": cities2,
                "gazettes_curitiba_30d": gazettes,
                "gazettes_merenda": ft,
            }
            out = out_dir / "querido_diario_curitiba_sample.json"
            out.write_text(
                json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"\nSalvou amostra em {out}  ({out.stat().st_size} bytes)")

        print("\n[5] /cities/{id}/themed-excerpts — endpoint experimental?")
        themed = get(
            c, f"/cities/{CURITIBA_IBGE}/themed-excerpts",
            since="2026-04-01", until="2026-05-01"
        )
        if themed:
            print(f"  resp: {json.dumps(themed, ensure_ascii=False)[:300]}")


if __name__ == "__main__":
    main()
