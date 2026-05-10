# scripts/_exploration/

Scripts exploratórios usados durante o desenho do projeto. **Não são
código de produção** e não fazem parte do pipeline rodado pelo
`dev_up` ou pelo cron weekly.

Mantidos versionados como audit trail das decisões: cada um documenta
uma hipótese investigada (e geralmente descartada — ver
`memory/project_pncp_adapter.md`).

| Script | O que investigou |
|---|---|
| `probe_compras.py` | API Compras.gov.br — schema, paginação, frequência de falhas |
| `probe_pncp*.py` | PNCP (5 scripts) — swagger, item structure, NFe coverage. Conclusão: ~20% itens via NFe com NCM ≠ CATMAT, descartado para v1 |
| `probe_tce_pr.py`, `probe_pit_consolidado.py`, `probe_tce_pit_cadastro.py` | TCE-PR PIT — formato do ZIP anual, parsing XML por município |
| `probe_curitiba.py` | Caso de uso específico Curitiba (precursor de `/municipio/[cd_tce]`) |
| `probe_cia_tce.py` | API CI/A do TCE (alternativa ao PIT, descartada) |
| `probe_querido_diario.py`, `probe_qd_themes.py` | Querido Diário — busca textual em diários oficiais (mantido em `/curitiba` e `/municipio/[cd_tce]`) |
| `probe_escolas_extrator.py` | Regex de extração de nome de escola em `dsObjeto` (precursor de `analytics/escolas.py`) |
| `probe_v2.py`, `probe_v3.py` | Iterações da arquitetura inicial (pré-refactor) |

## Como rodar (se precisar)

```bash
python -m uv run python scripts/_exploration/probe_pncp_swagger.py
```

## Por que não foram apagados

1. **Audit trail das decisões**: o que foi tentado e descartado é
   informação útil para quem chega novo.
2. **Reabertura**: alguns (probe_compras, probe_pncp_*) podem voltar
   a ser relevantes quando a API real estabilizar (ver PLANO §16.3).
3. **Material de apoio** para a documentação `data/PRIVACY.md`,
   `PLANO.md` §3 (estado do ecossistema OSS).

Ruff, mypy e pytest **ignoram este diretório** (configurado em
`pyproject.toml` per-file-ignores). Se a complexidade do exploratório
crescer, considere criar `scripts/_exploration/<sub>/` por tema.
