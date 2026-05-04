"""Print full DTO schema by name."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SPEC = Path("data/compras_openapi.json")


def main() -> None:
    name = sys.argv[1]
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    schemas = spec["components"]["schemas"]
    if name not in schemas:
        # fuzzy match
        matches = [k for k in schemas if name.lower() in k.lower()]
        print("Exact not found. Fuzzy matches:\n  " + "\n  ".join(matches))
        if len(matches) == 1:
            name = matches[0]
        else:
            return
    print(f"=== {name}")
    obj = schemas[name]
    for k, v in (obj.get("properties") or {}).items():
        t = v.get("type") or v.get("$ref", "?")
        if t == "array":
            inner = v.get("items", {})
            t = f"array<{inner.get('type') or inner.get('$ref', '?')}>"
        d = (v.get("description") or "")[:80]
        print(f"  {k:40s} {t:35s} {d}")


if __name__ == "__main__":
    main()
