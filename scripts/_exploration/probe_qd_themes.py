"""Probe QD themes — descobrir o que /gazettes/by_theme expoe."""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

BASE = "https://api.queridodiario.ok.org.br"


def get(c: httpx.Client, path: str, **params: object) -> dict | None:
    t0 = time.monotonic()
    try:
        r = c.get(BASE + path, params=params, timeout=httpx.Timeout(60.0))
    except Exception as e:
        print(f"  FAIL {type(e).__name__}: {e}")
        return None
    elapsed = time.monotonic() - t0
    print(f"  HTTP {r.status_code} ({elapsed:.1f}s) bytes={len(r.content)}")
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
        # Lista os temas disponiveis
        print("\n[1] /gazettes/by_theme/themes/")
        themes = get(c, "/gazettes/by_theme/themes/")
        if themes:
            print(f"  {json.dumps(themes, ensure_ascii=False)[:1500]}")

        if not themes or not isinstance(themes, (list, dict)):
            return

        # Se o retorno e um dict com lista
        theme_names = []
        if isinstance(themes, list):
            theme_names = [t if isinstance(t, str) else t.get("name") for t in themes]
        elif isinstance(themes, dict):
            theme_names = list(themes.values()) if themes else []
            if "themes" in themes:
                theme_names = themes["themes"]

        print(f"\n  temas: {theme_names}")

        # Para cada tema, ver subthemes e exemplo de excerto em Curitiba
        for theme in theme_names[:5]:
            theme_str = theme if isinstance(theme, str) else str(theme)
            print(f"\n[2.{theme_str}] /gazettes/by_theme/subthemes/{theme_str}")
            subs = get(c, f"/gazettes/by_theme/subthemes/{theme_str}")
            if subs:
                print(f"  subthemes: {json.dumps(subs, ensure_ascii=False)[:300]}")

            print(f"\n[3.{theme_str}] /gazettes/by_theme/{theme_str} (Curitiba)")
            sample = get(
                c, f"/gazettes/by_theme/{theme_str}",
                territory_ids="4106902",
                size=3,
                since="2026-01-01",
            )
            if sample:
                content = json.dumps(sample, ensure_ascii=False)
                print(f"  total: {sample.get('total_excerpts') or sample.get('total_gazettes')}")
                excerpts = sample.get("excerpts") or sample.get("gazettes") or []
                if excerpts and len(excerpts) > 0:
                    print(f"  sample excerpt: {json.dumps(excerpts[0], ensure_ascii=False)[:600]}")

        # Salva tudo em fixture
        full_sample = {"themes": themes, "subthemes_sample": {}}
        for theme in theme_names[:3]:
            theme_str = theme if isinstance(theme, str) else str(theme)
            full_sample["subthemes_sample"][theme_str] = get(
                c, f"/gazettes/by_theme/{theme_str}",
                territory_ids="4106902",
                size=3,
                since="2025-09-01",
            )
        out = out_dir / "qd_themes_sample.json"
        out.write_text(json.dumps(full_sample, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nSalvou em {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
