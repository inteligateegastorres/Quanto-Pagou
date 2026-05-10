# Contribuir com o Quanto Pagou

Bem-vindo. Este projeto é cívico, open-source e precisa de mais
gente — programadores, jornalistas de dados, advogados, servidores de
controle e cidadãos curiosos. Tem espaço pra todos.

Antes de começar, leia o [PLANO.md](./PLANO.md) — ele explica os
princípios e o estado atual. Resumo: estatística honesta, linguagem
factual, dados em quarentena visíveis, comparações só com confiança
≥ 0.75, sistema algorítmico de manchetes (não curadoria).

Este projeto adota o [Contributor Covenant 2.1](./CODE_OF_CONDUCT.md).
Para reportar problemas de segurança, leia [SECURITY.md](./SECURITY.md).

---

## O que pode contribuir (e como)

| Tipo de contribuição | Onde | Skills |
|---|---|---|
| Bug em parser de unidade ("S10" virando 10 L, etc) | Issue + PR em `src/analytics/resolution.py` + caso novo em `tests/test_resolution.py` | Python |
| Cluster mal-classificado em algum contrato | Relato em `/correcoes` (UI) ou issue com URL | Nenhuma |
| Novo cluster keyword | PR em `config/cluster_keywords.yaml` com 5+ exemplos casados | YAML |
| Novo município catalogado | Não precisa — `scripts/load_ibge_populacao.py` cobre 396 |
| Bug em endpoint API | Issue + PR em `src/api/main.py` (futuro: `src/api/routers/`) + teste em `tests/test_api_*.py` | Python + FastAPI |
| Bug visual no frontend | Issue com screenshot + PR em `frontend/app/<rota>` | TypeScript + Next.js |
| Refinar comparabilidade proxy v1 (PLANO §15.4) | PR em `sql/005_manchetes.sql` + `src/analytics/manchetes.py` | SQL + Python |
| Nova métrica de manchete (estabilidade, novidade) | RFC em issue antes do PR (impacta YAML versionado) | SQL + estatística |
| Documentação | PR em `README.md`, `PLANO.md`, ou `frontend/app/metodologia/` | Português |
| Análise jornalística | Issue com pauta + dados; ajudamos no SQL | Curiosidade |

**Bom primeiro PR:** procure issues marcadas `good-first-issue`. Se
não houver nenhuma aberta, abra issue perguntando o que tem espaço.

---

## Setup local (5 min)

Pré-requisitos: Docker, Python 3.12+, [uv](https://docs.astral.sh/uv/),
Node 20+.

```bash
# Windows
pwsh scripts\dev_up.ps1

# Linux / Mac / WSL
bash scripts/dev_up.sh
```

Sobe Postgres + ingere fixture + roda build_marts + manchetes refresh +
sobe API + sobe frontend. Estado em `.dev/` (gitignored).

URLs: API em `http://127.0.0.1:8001` (docs em `/docs`); frontend em
`http://127.0.0.1:3001`.

Para parar: `pwsh scripts\dev_down.ps1` (ou `bash scripts/dev_down.sh`).

---

## Padrão de PR

1. **Branch a partir de `main`**, nome curto descritivo (`fix-cluster-merenda`,
   `feat-mapa-uf`).
2. **Commit messages** no padrão [Conventional Commits](https://www.conventionalcommits.org/):
   `feat(escopo): ...`, `fix(escopo): ...`, `docs: ...`, `chore(escopo): ...`,
   `refactor(escopo): ...`.
3. **Antes de pushar**, rode local:
   - `python -m uv run ruff check src/`
   - `python -m uv run mypy src/` (warnings ok; novos erros não)
   - `python -m uv run pytest`
   - `cd frontend && npx tsc --noEmit && npx next lint`
4. **PR aberto** dispara `.github/workflows/ci.yml` (mesmo do passo 3) +
   `tests/qa/schema_snapshot.py check` (se tocou API). Status checks
   devem passar antes de merge.
5. **Descreva o "por quê"** no body do PR. O "o quê" o diff já mostra.
   Se for mudança de comportamento público (manchete, copy, score),
   marque `breaking-change` e documente migração.

### Mudanças que merecem RFC antes do código

- Novo critério de seleção de manchete (impacta `config/manchete_v*.yaml`)
- Mudança em threshold de confiança ou cluster_version
- Nova esteira editorial pública (`/insight/...` ou `/destaques/`)
- Mudança em texto público sensível (manifesto, política de correção,
  guardrails de fornecedor)

Abra issue marcada `rfc` com a proposta + alternativas consideradas.
Discussão pública antes do código evita retrabalho.

---

## Estrutura do repositório

Vide `README.md` seção "Layout do repositório". TL;DR:

```
src/             # Python: ingest, analytics, api
sql/             # migrations idempotentes
config/          # YAML versionado (golden set, clusters keyword, manchetes)
scripts/         # CLIs operacionais (dev_up, ingest, loaders)
tests/           # pytest + tests/qa/ (CHECKLIST + banco_check + schema_snapshot)
frontend/        # Next.js 16 + Tailwind
data/            # fixtures sintéticas, golden set CSV, política de privacidade
.github/         # workflows CI
```

---

## Princípios não-negociáveis

Aprenda com erros já cometidos:

- **σ ingênuo é proibido.** Use mediana + IQR + percentis. Distribuições
  reais de preço público têm caudas longas.
- **Cluster_id é versionado.** Mudanças em modelo de cluster geram nova
  versão; histórico nunca é reescrito.
- **Quarentena fica visível** com label, nunca some do site.
- **Linguagem factual.** Não usamos "suspeito", "irregular", "desviado".
  Mostramos números + fonte primária + intervalo. Cabe ao leitor
  interpretar.
- **Manchetes algorítmicas** seguem `config/manchete_v1.yaml` versionado.
  Discordou? PR no YAML, com dados.
- **Hardcode no UI** é bug. Tudo vem do banco.
- **Snapshot é a verdade.** Reprocessar é função pura sobre snapshots.

Vide [PLANO.md §1, §15](./PLANO.md) e a [metodologia](http://127.0.0.1:3001/metodologia)
no site.

---

## Onde achar ajuda

- Issues abertas: <https://github.com/inteligateegastorres/Quanto-Pagou/issues>
- Discussões de design: marcar issue como `discussion`
- E-mail (até organização ser criada): contato@quantopagou.org

Obrigado por contribuir. Plataforma cívica vive de gente que aparece.
