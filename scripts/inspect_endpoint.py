"""Print parameters and response schema for a Compras.gov.br endpoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SPEC = Path("data/compras_openapi.json")


def schema_summary(schema: dict, depth: int = 0, max_depth: int = 3) -> str:
    if depth > max_depth:
        return "..."
    if "$ref" in schema:
        return schema["$ref"]
    t = schema.get("type")
    if t == "array":
        items = schema.get("items", {})
        return f"array<{schema_summary(items, depth + 1, max_depth)}>"
    if t == "object":
        props = schema.get("properties", {})
        if not props:
            return "object"
        return "object{" + ", ".join(props.keys()) + "}"
    return t or "?"


def resolve_ref(spec: dict, ref: str) -> dict:
    parts = ref.lstrip("#/").split("/")
    obj = spec
    for p in parts:
        obj = obj[p]
    return obj


def main() -> None:
    default_target = "/modulo-pesquisa-preco/2_consultarMaterialDetalhe"
    target = sys.argv[1] if len(sys.argv) > 1 else default_target
    method = sys.argv[2] if len(sys.argv) > 2 else "get"

    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    op = spec["paths"][target][method]

    print(f"=== {method.upper()} {target}")
    print(f"Summary: {op.get('summary', '')}")
    if desc := op.get("description"):
        print(f"Description: {desc[:600]}")

    print("\n--- Parameters ---")
    for p in op.get("parameters", []):
        req = "*" if p.get("required") else " "
        sch = p.get("schema", {})
        t = schema_summary(sch)
        d = (p.get("description") or "")[:120]
        print(f"  {req} {p['name']:35s} {t:25s} {d}")

    print("\n--- Response 200 ---")
    resp = op.get("responses", {}).get("200", {})
    content = resp.get("content", {})
    for mime, info in content.items():
        sch = info.get("schema", {})
        ref = sch.get("$ref")
        if ref:
            resolved = resolve_ref(spec, ref)
            print(f"  {mime} -> {ref}")
            print("  Properties:")
            for k, v in resolved.get("properties", {}).items():
                t = schema_summary(v)
                print(f"    {k:35s} {t}")
                # Drill into resultado/items array of object
                if k in ("resultado", "data", "items") and v.get("type") == "array":
                    inner = v.get("items", {})
                    inner_ref = inner.get("$ref")
                    if inner_ref:
                        inner_resolved = resolve_ref(spec, inner_ref)
                        print(f"      array of {inner_ref}:")
                        for ik, iv in inner_resolved.get("properties", {}).items():
                            it = schema_summary(iv)
                            print(f"        {ik:33s} {it}")
        else:
            print(f"  {mime} -> {schema_summary(sch)}")


if __name__ == "__main__":
    main()
