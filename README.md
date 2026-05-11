# Quanto Pagou

Plataforma cívica para monitorar gastos públicos brasileiros e identificar possíveis desvios.

> **Status:** sprint local concluído + Fase 1 PR já no ar. Pipeline TCE-PR
> estadual completo (156k contratos reais de 397 municípios — agora todos
> com população IBGE 2022), 19 clusters keyword (~34% cobertura), 506
> escolas extraídas, **sistema de manchetes algorítmicas** (3 camadas SQL
> + YAML versionado + estabilidade temporal + vela apagada + busca
> reversa), ~32 endpoints API e 18 páginas frontend incluindo busca tripla
> (`/buscar`, `/fornecedores`, `/instituicoes`), `/manchetes`, drill-down
> universal em `/contratos` e QA versionado em `tests/qa/` (CHECKLIST +
> banco_check + schema_snapshot). Pendente: domínio, contas
> Vercel/Supabase/R2, revisão jurídica (ver [DEPLOY.md](./DEPLOY.md)).
> Banner global diferencia Paraná real (verde) × Federal fixture (laranja).

---

## Estado atual

Pronto:
- Camada de durabilidade (snapshots brutos versionados por SHA-256).
- Spider Compras.gov.br + ingestão por fixture sintética (a API real está com
  falha intermitente de backend JPA — fixture preserva o pipeline downstream).
- Resolução de cluster Tier 1 (CATMAT direto contra golden set core v1).
- Normalização de unidade via `unit_conversion.yaml` versionado (kg, litro,
  unidade, resma_500).
- Marts materializados: `mart_pares` (mediana/p25/p75 por cluster × ente × uf
  × porte) e `mart_orgao_cluster` (ranking de órgãos por cluster).
- Quarentena visível com motivo legível (itens não-comparáveis nunca somem).
- API FastAPI (OpenAPI nativo).
- Frontend Next.js 16: landing pública (home reformulada com pitch +
  3 CTAs + boletim + status), manifesto, ranking destacado, insight
  editorial, página de cluster, card narrativo do item (template §6.1
  do plano), metodologia, correções, **página `/curitiba`** com dados
  reais TCE-PR (top fornecedores + contratos por categoria-piloto) e
  busca textual em diários oficiais via Querido Diário.
- **Pipeline TCE-PR (Day 8+)** — coexiste com o federal sob
  `source='tce_pr/contrato'`. ZIP anual público em
  `pit.tce.pr.gov.br/Arquivos/{ano}_PIT_TodosArquivos.zip` (2025: 1,29 GB,
  399 municípios PR, atualizado semanal). Adapter `src/ingest/tce_pr.py`
  baixa + extrai sub-zips por município + parseia XML `<Contrato/>`.
  Granularidade **por contrato** (TCE não publica item-a-item). Cluster
  por **keyword em `dsObjeto`** (Tier 1.5, 19 categorias em
  `config/cluster_keywords.yaml`); threshold separado ≥ 0.5. Marts
  dedicados: `mart_contratos_municipio` e `mart_fornecedores_municipio`.
  **Validação estadual:** 156.679 contratos de 397 municípios em 55s
  + build em 50s; 121.526 fornecedores únicos; cobertura keyword
  33,6% (52.669 / 156.679). UI de comparação entre cidades-pares
  ativa via endpoint `/tce-pr/cluster/{id}/ranking-municipios`.
- **Catálogo de obras escolares** — `analytics.escola_mencao` extraída via
  regex em `src/analytics/escolas.py` (4 padrões: escola_municipal,
  sigla_cmei, centro_municipal, creche). 506 escolas únicas em 997 menções,
  cobertura geral 0,17% (concentrada em obras_edificacao 29%). UI em
  `/escolas` e `/escolas/[slug]`. Catálogo de transparência (lista de
  obras pontuais com nome próprio identificável); **não substitui
  comparação por escola** — ver `todo.txt` para fontes alternativas.
- **Modalidade do contrato** (pregão, dispensa, concorrência…) — vem de
  `Licitacao.xml` + `LicitacaoXContrato.xml` via JOIN em memória por
  município. Cobertura 65% no estado completo (82k pregão, 16k dispensa,
  2k concorrência). Aparece em `/fornecedor/[cnpj]` e `/contrato/[id]`.
- **OG images dinâmicas** (`/opengraph-image` na home, `/insight/.../opengraph-image`)
  via `next/og` — dados puxados do mart em tempo de geração.
- **Banner global** diferencia visualmente Paraná real (verde) × Federal
  fixture (laranja); link para `/metodologia`.
- **Window-splitting recursivo** na ingestão Compras.gov.br
  (`ingest_with_split` + `sql/002_resilience.sql`): janelas que falham
  com erro transitório são divididas até `min_window_days`, e o que não
  vingar fica como `failed` em `raw.snapshots` com `error_message`
  legível. `scripts/sync_compras.{ps1,sh}` orquestra.
- **Componente `Stat` compartilhado** (`frontend/lib/Stat.tsx`) com
  overflow-protection nos cards (números grandes não transbordam mais
  para cards adjacentes); helper `fmtBRLCompact` para "R$ 5,12 bi".
- 28 testes unitários travando regressões do parser de unidade.
- **Sistema de manchetes algorítmicas** (`/manchetes`, ver PLANO §15). 3
  camadas SQL: `cluster_discrepancias` (MV de fatos), `manchete` (seleção
  após `config/manchete_v1.yaml`), `manchete_publicada` + `manchete_saida`
  (logs auditáveis). Inclui estabilidade temporal (≥2 de 3 janelas
  90/180/365d), vela apagada (manchete que sai com motivo diagnóstico),
  busca reversa (`/manchetes/diagnostico?cd_tce=X` mostra todos os
  candidatos avaliados). Re-tunável em ~1s editando YAML.
- **IBGE Censo 2022 carregado** em `analytics.municipio_pr`: 35 → 396
  municípios catalogados (99.7% match contra TCE-PR). Pop total
  11.431.051. `scripts/load_ibge_populacao.py`.
- **Hardening de QA:** `tests/qa/banco_check.py` (13 PASS contra
  /health e /stats/pr), `tests/qa/schema_snapshot.py update|check` (30
  endpoints versionados em `tests/qa/snapshots/` — drift CHECKLIST↔API
  detectado em CI).
- **Cron weekly** (`.github/workflows/ingest-weekly.yml`, quartas 06:00
  UTC) ingere TCE-PR + Compras.gov.br + roda build_marts + manchetes
  refresh + `unmatched_dsobjeto_top` (artifact) + sync R2.
- **CI em PR** (`.github/workflows/ci.yml`): ruff + mypy + pytest
  (backend) + next lint + tsc (frontend). Status checks bloqueiam
  merge.
- **Governance** (PLANO §17.A): `LICENSE` (AGPL-3.0) + `frontend/LICENSE`
  (MIT) + `CONTRIBUTING.md` + `SECURITY.md` + `CODE_OF_CONDUCT.md`
  (Contributor Covenant 2.1) + `data/PRIVACY.md` (LGPD v1, 6
  categorias, 3 bases legais, 6 salvaguardas).
- **Performance** (PLANO §17.B.3): `sql/006_perf_indexes.sql` com 4
  partial indexes — drill-down típico de 73ms → 6.7ms (~10× speedup
  validado por EXPLAIN ANALYZE).
- **Backlog do YAML automatizado** (PLANO §17.B.2):
  `scripts/unmatched_dsobjeto_top.py` ranqueia top 200 descrições em
  quarentena (104k contratos sem cluster keyword). PR no
  `cluster_keywords.yaml` consulta o CSV gerado pelo CI.
- **Frontend cache otimizado** (PLANO §17.A.9): `jget` usa
  `revalidate: 1800` (30min); `jgetLive` para buscas interativas.
  Reduz custo Vercel/Supabase em produção.
- **Tombstones LGPD art. 18 IV** (PLANO §18 L.1):
  `analytics.eliminacao` registra solicitações atendidas; trigger
  sincroniza `item_canonical.eliminada_em`; 5 MVs filtram automaticamente;
  endpoint `/contrato/{raw_id}` retorna 410 Gone se eliminado;
  `/eliminacoes/publicas` lista (raw_id + motivo + fundamento) sem
  reproduzir conteúdo. CLI `scripts/eliminar.py`. Snapshot raw
  preservado (auditoria).
- **Audit log LGPD art. 37** (PLANO §18 L.10):
  `analytics.audit_log` append-only com triggers cirúrgicos em
  `analytics.eliminacao`, `item_canonical` (só quando `eliminada_em`
  muda) e `fornecedor`. Captura `ator`/`base_legal` via
  `current_setting('app.audit_actor')` (psycopg seta `SET LOCAL`
  antes do write). NÃO loga refresh de MV (volume sem ganho
  probatório).
- **Distinção PJ vs MEI/EI** (PLANO §18 L.2 + L.2.b):
  `analytics.fornecedor(cnpj, tipo_juridico, fonte)` + classificador
  heurístico por sufixo (LTDA, S.A., EIRELI, COOPERATIVA, etc).
  Helper `_require_pj_or_404` aplicado em **todos** os endpoints
  derivados (`/fornecedor/{cnpj}`, `/por-orgao`, `/por-municipio`,
  `/por-categoria`, `/por-modalidade`, `/contratos`). MV
  `mart_fornecedores_municipio` filtra `tipo_juridico='PJ'` na origem
  (defesa em camadas). Listagem `/fornecedores` filtra PJ. Frontend
  `/fornecedor/[cnpj]` mostra página explicativa de 404 com gancho
  para `/correcoes` em vez de erro genérico. Primeira carga: 22.4k
  PJ confirmado, 16.3k mascarado (42%). Fonte versionada permite
  dump RFB substituir heurística depois.
- **Rotas LGPD públicas** (PLANO §18 L.5, L.6, L.7):
  `/politica-privacidade` (política completa em 10 seções,
  força-static), `/termos` (Termos de Uso + licença CC-BY 4.0 dos
  dados derivados, foro Curitiba/PR, distinção dados primários vs
  derivados), `/lgpd` (tabela dos 9 direitos do art. 18 +
  autodeclaração de pequeno porte CD/ANPD 2/2022 + e-mail
  `lgpd@quantopagou.org` + SLA 15d). Footer global cita encarregado +
  links pras 3 páginas + página de eliminações públicas. Arquivo
  `LICENSE-DATA` na raiz documenta a licença dos dados derivados.
- **Disclaimer de origem** (PLANO §18 L.11):
  Componente `frontend/lib/DisclaimerOrigem.tsx` aceita prop `fonte`
  (tce-pr/compras-gov-br/mista) + `atualizado_em` opcional. Integrado
  em `/comparar`, `/manchetes`, `/fornecedor/[cnpj]`,
  `/municipio/[cd_tce]`, `/cluster/[cluster_id]`. Banner discreto:
  "Dados extraídos de [fonte] em [data]. Possíveis erros — reportar
  correção."
- **`/correcoes` formal com ticket auditável** (PLANO §18 L.12):
  `analytics.correcao_ticket` com `ticket_id` público
  `QP-AAAA-XXXX`. 3 endpoints (`POST /correcoes/ticket`,
  `GET /correcoes/ticket/{id}`, `GET /correcoes/recentes`). Frontend
  com Server Action substitui o `mailto:` antigo; após submit,
  redireciona para `/correcoes/{ticket_id}` (página pública sem
  cadastro, noindex). SLA `factual_48h` (erro de fato) ou
  `lgpd_15d` (art. 19) calculado a partir do tipo. Flag
  `publicar_descricao` deixa o reportador controlar se a descrição
  aparece na vitrine pública dos resolvidos. E-mail do reportador
  nunca sai do banco (auditável internamente via audit_log L.10).
- **Contestar decisão automatizada** (PLANO §18 L.13, LGPD art. 20):
  Tipo `revisao_ranking` adicionado em `correcao_ticket` (SLA 15d).
  Componente `BotaoContestarRanking` gera link pré-preenchido para
  `/correcoes?tipo=revisao_ranking&url=…&descricao=…`. Form de
  `/correcoes` aceita `searchParams` e pré-preenche. Inserido em
  `/manchetes` (cada card), `/cluster/[id]` (header do ranking de
  órgãos), `/fornecedor/[cnpj]` (após distribuição por órgão).
- **Expurgo de `raw_payload` redundante** (PLANO §18 L.9.b + L.9.c):
  `scripts/expurgar_raw_payload.py` com `--dry-run` default seguro
  + `--apply`/`--days N`/`--batch-size`. Critério: idade > N dias
  AND canonicalização validada (`item_canonical` populado) AND
  ainda não expurgado. Workflow `.github/workflows/expurgar-mensal.yml`
  roda dia 1 de cada mês 06:00 UTC sempre em dry-run (Job Summary
  com relatório); apply só via `workflow_dispatch` manual até
  ≥1 ciclo humano validado.
- **Hardening em resposta à análise externa** (v5.9):
  `.github/dependabot.yml` (atualizações weekly para pip, npm,
  github-actions), `.github/workflows/gitleaks.yml` (scan de secrets
  em PR/push), `docs/architecture/adr/` (5 ADRs cobrindo decisões
  críticas) + `docs/architecture/THREAT_MODEL.md` (STRIDE com riscos
  conhecidos), Sentry condicional em `src/api/main.py` (inicializa
  apenas se `SENTRY_DSN_API` setado).
- **Política de retenção** (PLANO §18 L.9.a): `docs/legal/RETENCAO.md`
  v1 com prazos por camada (raw imutável, audit_log 5 anos,
  manchetes 2 anos, MVs sem retenção, raw_payload 90d após
  canonicalização). CLI de expurgo e cron mensal deferidos para
  L.9.b/c.

Em andamento — Wave LGPD (PLANO §18, bloqueante para go-live público):
- **L.1 ✅** tombstones (acima)
- **L.2 ✅** PJ vs MEI v1 + 2.b (acima)
- **L.5 ✅** Política de Privacidade (acima)
- **L.6 ✅** Termos de Uso + LICENSE-DATA CC-BY 4.0 (acima)
- **L.7 ✅** Canal LGPD + encarregado (acima)
- **L.9 ✅** retenção completa (doc + CLI dry-run + workflow mensal)
- **L.10 ✅** audit log (acima)
- **L.11 ✅** disclaimer de origem (acima)
- **L.12 ✅** /correcoes formal com ticket+SLA+audit (acima)
- **L.13 ✅** contestar decisão automatizada (acima)
- **L.3, L.4, L.8** LIA + RIPD + subprocessadores (jurídico humano, pendente)
- **L.14-L.15** instituição-âncora + revisão jurídica externa (pendente)

Não pronto (depende do usuário humano para destravar):
- Domínio `quantopagou.org`, organização GitHub, contas Vercel/Supabase/R2.
- Revisão jurídica preliminar do manifesto + página de fornecedor.
- Adapter PNCP como fallback (explorado, pausado em commit `cc2dd13` —
  swagger e fixture preservados em `data/`. NFe traz só 20% dos itens
  com classificação NCM e não CATMAT; reabrir só se Compras.gov.br
  ficar fora por semanas. Ver memória `project_pncp_adapter`).
- Tier 2 (embeddings) — diferido para Fase 1+ por design (progressive
  correctness).
- Ingestão real do Compras.gov.br quando o backend deles estabilizar
  (resiliência já testada na prática: 3 snapshots `failed` registrados,
  com `error_message` capturando a string `Could not open JPA EntityManager`).
- Spiders estaduais (Tá de Pé) — Fase 2.

---

## Arquitetura

```
Compras.gov.br ──▶ raw.snapshots (SHA-256 + JSONL.gz em ./snapshots)
                ──▶ raw.compras   (linhas + raw_payload JSONB)
                          │
                          ▼
                  src/analytics/resolution.py
                  (Tier 1 CATMAT + parser unit_conversion.yaml)
                          │
                          ▼
                  analytics.cluster_registry (versionado)
                  analytics.item_canonical   (1:1 com raw.compras)
                          │
              ┌───────────┴────────────┐
              ▼                        ▼
   analytics.mart_pares       analytics.mart_orgao_cluster
   (mediana/p25/p75 por        (ranking por cluster)
    cluster × ente × uf
    × porte)
              │                        │
              └───────────┬────────────┘
                          ▼
                   FastAPI (src/api/main.py)
                          │
                          ▼
                   Next.js (frontend/)
```

Princípios chave:
- **Progressive correctness.** Tier 2-4 e drift automático ficam para fases
  posteriores; o que está aqui é Tier 1 + golden set pequeno + drift manual.
- **Quarentena visível.** Item sem CATMAT, sem unidade detectável ou com
  cluster_id ambíguo entra em `analytics.item_canonical.em_quarentena=true`
  com motivo legível e segue acessível por URL.
- **Snapshot é a verdade.** Reprocessar é função pura sobre snapshots —
  `build_marts.py` é idempotente (`UPSERT ... ON CONFLICT`).
- **Cluster é versionado.** `cluster_version` (ex: `v1`) acompanha cada item
  canonicalizado. Mudança de modelo gera nova versão; histórico nunca é
  reescrito.
- **Comparações públicas só com `confianca_resolucao ≥ 0.75`** — threshold
  versionado nos marts (filtro WHERE no SQL da MV).

---

## Como rodar (local)

Pré-requisitos: Docker, Python 3.12+, [`uv`](https://docs.astral.sh/uv/),
Node 20+.

### Caminho rápido (recomendado)

```powershell
# Windows
pwsh scripts/dev_up.ps1            # sobe postgres + API + frontend
pwsh scripts/dev_down.ps1          # para API + frontend (postgres continua)
pwsh scripts/dev_down.ps1 -All     # tambem para postgres (volume preservado)
pwsh scripts/dev_down.ps1 -Wipe    # tudo + apaga volume (perde dados)
pwsh scripts/dev_up.ps1 -Fresh     # reset completo: re-cria volume + reseed
```

```bash
# Linux / Mac / WSL
bash scripts/dev_up.sh
bash scripts/dev_down.sh
ALL=1  bash scripts/dev_down.sh
WIPE=1 bash scripts/dev_down.sh
FRESH=1 bash scripts/dev_up.sh
```

O `dev_up` é idempotente: aplica a migration analytics, ingere a fixture só
se `raw.compras` estiver vazio, roda `build_marts` e sobe API + frontend em
background. PIDs e logs ficam em `.dev/` (gitignored). URLs ao final:

- Postgres: `localhost:5433` (user/db `quantopagou`)
- API: <http://127.0.0.1:8001> (Swagger em `/docs`)
- Frontend: <http://127.0.0.1:3001>

### Caminho manual (se preferir controle)

```bash
# 1. Postgres
docker compose up -d

# 2. Dependências Python
python -m uv sync

# 3. Migration analytics (a 000_init.sql roda automática na 1ª subida do volume)
docker exec -i quantopagou-postgres psql -U quantopagou -d quantopagou < sql/001_analytics.sql

# 4. Ingestão (fixture sintética enquanto API real está caída)
python -m uv run python -m ingest --fixture data/fixtures/compras_sample.jsonl 2026-04-15 2026-04-15

# 5. Pipeline analytics (canonicalização + refresh dos marts)
python -m uv run python -m analytics.build_marts

# 6. API
python -m uv run uvicorn api.main:app --host 127.0.0.1 --port 8001

# 7. Frontend (em outro terminal)
cd frontend && npm install && npm run dev
```

### Inspeções e testes

```bash
# inspecionar banco
python -m uv run python scripts/inspect_raw.py
python -m uv run python scripts/inspect_marts.py

# testes unitarios (parser, etc)
python -m uv run pytest tests/ -v

# QA hardening (validados em CI)
python -m uv run python tests/qa/banco_check.py        # PG vs API
python -m uv run python tests/qa/schema_snapshot.py check  # drift schema
python -m uv run ruff check src/ scripts/ tests/        # lint
python -m uv run mypy src/                              # types

# pipeline de candidatos a YAML novo (top descricoes sem cluster)
python -m uv run python scripts/unmatched_dsobjeto_top.py --top 200
```

---

## Layout do repositório

```
.
├── PLANO.md                          # Plano de produto + roadmap (v4)
├── README.md                         # Este arquivo
├── docker-compose.yml                # Postgres 16 (porta 5433)
├── pyproject.toml                    # uv / hatchling
├── .env.example                      # DATABASE_URL, COMPRAS_API_BASE, ...
│
├── sql/
│   ├── 000_init.sql                  # raw.snapshots + raw.compras
│   └── 001_analytics.sql             # analytics.* (cluster_registry, item_canonical, marts, view)
│
├── config/
│   └── unit_conversion.yaml          # patterns regex + defaults por categoria (versionado)
│
├── data/
│   ├── compras_openapi.json          # OpenAPI da API Compras.gov.br (referência offline)
│   ├── golden_set/
│   │   └── core_v1.csv               # 50 itens, 5 clusters-piloto
│   └── fixtures/
│       └── compras_sample.jsonl      # payload sintético (para quando upstream cai)
│
├── src/
│   ├── ingest/
│   │   ├── compras.py                # spider + persistência (snapshot + raw.compras)
│   │   ├── config.py                 # pydantic-settings (.env)
│   │   └── __main__.py               # CLI: python -m ingest [start] [end] [--fixture ...]
│   ├── analytics/
│   │   ├── resolution.py             # Tier 1 + parser de unidade + derivação de ente
│   │   └── build_marts.py            # CLI: python -m analytics.build_marts
│   └── api/
│       └── main.py                   # FastAPI
│
├── frontend/                         # Next.js 16 + Tailwind
│   ├── app/
│   │   ├── layout.tsx · page.tsx · globals.css
│   │   ├── cluster/[cluster_id]/page.tsx
│   │   ├── item/[raw_id]/page.tsx
│   │   ├── metodologia/page.tsx
│   │   └── correcoes/page.tsx
│   └── lib/api.ts                    # cliente da API + helpers de formato
│
├── scripts/                          # dev_up/dev_down (ps1 + sh) + smokes (probe, inspect, fixture gen)
├── snapshots/                        # JSONL.gz de cada coleta (gitignored)
└── tests/
    ├── test_resolution.py            # 28 testes (parametrize cobrindo edge cases reais)
    └── qa/
        ├── CHECKLIST.md              # QA manual: backend + frontend + integracao
        └── FINDINGS.md               # template para registrar bugs encontrados
```

---

## API REST (Fase 0.5)

Base: `http://127.0.0.1:8001` · Docs: `/docs` · Sem auth (dados públicos).
Lista completa em `/openapi.json`; abaixo, agrupada por área.

**Meta / catálogo**

| Endpoint | Descrição |
|---|---|
| `GET /health` | Sanidade + contagens (snapshots, raw, canonical, marts). |
| `GET /stats/pr` | Agregados ao vivo do pipeline TCE-PR (alimenta a home sem hardcode). |
| `GET /clusters?categoria=...` | Lista clusters ativos com `n_itens`. |
| `GET /quarentena/resumo` | Saúde pública do pipeline (% por categoria × motivo). |
| `GET /manchetes` | Top N manchetes ativas (PLANO §15). Selecionadas pelo YAML versionado, com hash de auditoria e estabilidade temporal (janelas_passadas/3). |
| `GET /manchetes/saidas?dias=N` | Vela apagada — manchetes que saíram nos últimos N dias com motivo diagnóstico. |
| `GET /manchetes/diagnostico?cd_tce=X` | Busca reversa — manchetes ativas do município + diagnóstico de quais (cluster, mun) avaliados não viraram manchete e por quê. |
| `GET /eliminacoes/publicas` | LGPD art. 18 IV — lista IDs eliminados + motivo + fundamento legal. Transparência sem reproduzir conteúdo. |
| `GET /contrato/{raw_id}` | Detalhe; **retorna 410 Gone** se raw_id está em `analytics.eliminacao` (LGPD). |

**Comparação (núcleo do produto)**

| Endpoint | Descrição |
|---|---|
| `GET /pares?cluster_id=X&cluster_version=v1` | `mart_pares` filtrada (mediana/p25/p75 por uf+porte+ente). |
| `GET /ranking/orgaos?cluster_id=X&order=mediana_desc` | Ranking de órgãos para o cluster. |
| `GET /tce-pr/cluster/{id}/ranking-municipios` | Top municípios PR no cluster (volume). |
| `GET /tce-pr/cluster/{id}/comparacao-municipios?cluster_version=v1` | Tabela comparativa entre municípios. |

**Busca / drill-down**

| Endpoint | Descrição |
|---|---|
| `GET /municipios?search=...&limit=N` | Lista de municípios PR (filtro por nome). |
| `GET /fornecedores?search=...&min_contratos=5&limit=N` | Lista de fornecedores (default ≥5 contratos = guardrail §6.5). |
| `GET /instituicoes/search?q=...` | Busca termo em fornecedor + órgão + objeto; agrega quem foi pago em contratos cujo objeto menciona o termo. |
| `GET /contratos/search?q=&cd_tce=&modalidade=&since=&until=&ordenar_por=&limit=` | Drill-down universal: ILIKE em descrição/fornecedor/órgão + filtros combinados. |
| `GET /escolas?search=...&cd_tce=...` | Catálogo de escolas extraídas via regex (506 unidades). |
| `GET /escolas/{slug}/contratos` | Contratos vinculados a uma escola. |
| `GET /tce-pr/dispensas/top-fornecedores?min_contratos=5` | Top fornecedores em dispensa (com mascaramento de PF). |

**Detalhe**

| Endpoint | Descrição |
|---|---|
| `GET /municipio/{key}/info` | Resolve cd_tce↔cd_ibge → info canônica. |
| `GET /tce-pr/municipio/{cd_ibge}/resumo` | Resumo do município: contratos, valor, top clusters. |
| `GET /tce-pr/municipio/{cd_ibge}/contratos-por-cluster` | Contratos agrupados por categoria. |
| `GET /tce-pr/municipio/{cd_ibge}/fornecedores` | Top fornecedores do município. |
| `GET /fornecedor/{cnpj}` | Perfil agregado (≥5 contratos = guardrail §6.5). |
| `GET /fornecedor/{cnpj}/{por-orgao,por-municipio,por-categoria,por-modalidade,contratos}` | Distribuições do perfil. |
| `GET /item/{raw_id}` | Item canonicalizado + comparação com pares (ou flag de quarentena). |
| `GET /contrato/{raw_id}` | Contrato com link à fonte primária + raw_payload. |

---

## Páginas do frontend

| Rota | Conteúdo |
|---|---|
| `/` | Landing com **Zona A puxando manchete rank=1 da API** (sem hardcode) + Paraná real + Federal fixture + Categorias. |
| `/manchetes` | Sistema algorítmico (PLANO §15): top N atual + busca reversa (cd_tce → manchetes ativas + diagnóstico de quais clusters NÃO viraram manchete e por quê) + recém-saídas (vela apagada com motivo). |
| `/buscar` | Busca combinada — municípios PR (top 30 ou filtro por nome) **e** fornecedores (top 30, filtro nome ou CNPJ). |
| `/fornecedores` | Página dedicada à empresa que recebeu pagamento. Filtro mínimo de contratos editável (default 5 = guardrail §6.5). |
| `/instituicoes` | Busca por **destinatário no objeto** (UPA, escola, hospital, posto, CRAS). Agrega "quem foi pago" + "por município/órgão". Banner explicita que termo no objeto ≠ verba total da unidade. |
| `/contratos` | Drill-down universal: lista paginada com filtros editáveis (q, cd_tce, fornecedor, modalidade, datas, ordenação). Toda agregação no site abre aqui filtrada. |
| `/dispensas` | Top fornecedores em dispensa de licitação + insight editorial (merenda escolar PR). Mascara CPFs por padrão. |
| `/comparar` | Município × município por cluster (até 6 cidades). **Filtro de data obrigatório** + badge `cluster_version=v1`. |
| `/escolas` | Catálogo de obras escolares (506 escolas via regex no objeto). Transparência, não ranking — comparação numérica adiada com motivo registrado. |
| `/escolas/[slug]` | Stats + lista de contratos vinculados à escola. |
| `/municipio/[cd_tce]` | Página genérica de qualquer município PR: top fornecedores, contratos por categoria, comparação contra pares (cards clicáveis). |
| `/curitiba` | Redirect → `/municipio/410690` (atalho preservado para SEO/links antigos). |
| `/fornecedor/[cnpj]` | Perfil agregado com guardrails §6.5 (threshold ≥ 5 contratos, modal "como interpretar", `noindex,nofollow`). Distribuição por órgão/município/categoria/modalidade + top contratos. |
| `/contrato/[id]` | Detalhe completo + link à fonte primária (ZIP TCE-PR) + raw_payload para auditoria. |
| `/insight/diesel-ministerios` | Análise editorial sobre spread entre ministérios federais comprando o mesmo diesel S10 (fixture). |
| `/insight/merenda-escolar-pr` | Análise editorial sobre dispensa em merenda escolar no Paraná. |
| `/cluster/[cluster_id]` | Distribuição p25-p75 entre pares + ranking de órgãos (federal CATMAT). |
| `/item/[raw_id]` | Card narrativo §6.1: barras "você vs mediana", badge de confiabilidade, sinais decompostos. |
| `/manifesto` | Por que existe a plataforma — gap do Painel de Preços + tese + princípios. |
| `/metodologia` | Fontes, resolução, normalização, guardrails, cluster_version, política de correção. |
| `/correcoes` | Página viva — correções pós-relato com data, item, delta. |
| `/opengraph-image`, `/insight/.../opengraph-image` | OG images dinâmicas (PNG 1200×630) via `next/og`. |

---

## Schema do banco

```sql
-- camada bruta
raw.snapshots(id pk, source, period_start, period_end, records_count, hash_sha256, ingested_at)
raw.compras  (id pk, snapshot_id fk, source, source_id, source_url,
              contract_date, orgao_codigo, orgao_nome,
              fornecedor_cnpj, fornecedor_nome,
              catmat_id, catser_id, descricao,
              quantidade, unidade, valor_unitario, valor_total, modalidade,
              raw_payload jsonb, ingested_at)

-- camada canônica
analytics.cluster_registry(cluster_id, cluster_version, descricao_canonica,
                           categoria, ativo, criado_em, mapeamento_de
                           PRIMARY KEY (cluster_id, cluster_version))

analytics.item_canonical(raw_id pk fk -> raw.compras,
                         cluster_id, cluster_version,
                         metodo_resolucao, confianca_resolucao,
                         unidade_label, unidade_base, fator_conversao,
                         valor_unitario_normalizado,
                         ente_nivel, uf, porte,
                         em_quarentena, motivo_quarentena, resolved_at)

-- marts (materialized views, refresh manual via build_marts.py)
analytics.mart_pares          -- (cluster, ente, uf, porte) → n, min, p25, mediana, p75, max, iqr
analytics.mart_orgao_cluster  -- (cluster, orgao)           → n_compras, mediana_orgao, valor_total

-- saúde
analytics.v_quarentena_resumo -- (categoria, motivo) → n

-- manchetes algoritmicas (PLANO §15) — 3 camadas separadas
analytics.cluster_discrepancias  -- MV: fatos por (cluster, municipio) +
                                 -- spreads em 3 janelas (90/180/365d) +
                                 -- comparab proxy v1
analytics.manchete               -- selecao apos config/manchete_v1.yaml
analytics.manchete_publicada     -- log append-only (auditoria temporal)
analytics.manchete_saida         -- vela apagada (motivo diagnostico)
analytics.manchete_config_aplicada -- snapshot do YAML por hash

-- LGPD art. 18 IV (PLANO §18 L.1) — direito de eliminacao
analytics.eliminacao             -- (raw_id, motivo, fundamento_legal,
                                 --  eliminada_em, ator, ticket_ref).
                                 -- Trigger sincroniza item_canonical.
                                 -- raw.snapshots/raw.compras NUNCA mudam.
analytics.item_canonical.eliminada_em  -- coluna nova; NULL = ativo;
                                 -- 5 MVs filtram WHERE IS NULL
```

Filtros aplicados nos marts: `em_quarentena=false`, `valor_unitario_normalizado IS NOT NULL`, `confianca_resolucao >= 0.75`.

---

## Resolução & normalização — como funciona

`src/analytics/resolution.py` faz duas coisas e devolve uma linha canônica
por linha bruta:

**1. Cluster (Tier 1 apenas nesta fase):**

| Caso                                    | `cluster_id`         | `metodo_resolucao`         | `confianca` |
|-----------------------------------------|----------------------|----------------------------|-------------|
| `catmat_id` no `core_v1.csv`            | do golden            | `tier1_catmat_golden`      | 1.00        |
| `catmat_id` válido fora do golden       | `catmat_<id>`        | `tier1_catmat_sintetico`   | 0.85        |
| Sem `catmat_id`                         | `null` → quarentena  | `sem_cluster`              | 0.00        |

**2. Unidade:** aplica `config/unit_conversion.yaml` em ordem de patterns;
primeiro match vence. Se nada bate, cai para `defaults_por_categoria` (qtd
assumida = 1) e marca `fator_inferido=true` (penaliza confiança em -0.10).
Se nem o default existe → quarentena.

`valor_unitario_normalizado = valor_unitario / qtd_em_unidade_base`.

**Convenções anti-bug** já no YAML (motivadas por bugs reais pegos no caminho):
- `\b` antes de `\d+` em todo pattern numérico — `S10 LITRO` não vira "10 L".
- Patterns de papel/resma vêm antes de massa — `75G/M²` (gramatura) não vira
  peso.
- Negative lookahead `(?!\s*\/?\s*M[23]?)` no pattern de gramas para descartar
  "G/M2", "G/M3".

Esses dois bugs específicos estão travados em `tests/test_resolution.py`
(`test_canonicalize_diesel_nao_corrompe_S10`,
`test_canonicalize_papel_nao_corrompe_gramatura`).

---

## Decisões técnicas

- **Golden set é CSV, não DB.** Versionado no repo, fácil de revisar via PR.
- **`cluster_version` em todo lugar.** Comparações cross-versão exigem
  mapeamento explícito documentado — histórico nunca é reescrito.
- **MVs em vez de queries ad-hoc.** Refresh é manual no fim do `build_marts`,
  com `CREATE UNIQUE INDEX` para garantir refresh concorrente futuro.
- **`raw_payload JSONB` mantido íntegro.** Se mudar a interpretação amanhã,
  reprocessa do payload sem nova coleta.
- **Ente derivado em `item_canonical`, não em `raw.compras`.** Permite
  reinterpretar o mesmo dado bruto sob novas regras (ex: novas faixas de
  porte municipal) sem alterar a camada raw.
- **Sem auth na API.** Dados públicos por definição. Rate limit virá via
  reverse proxy quando houver tráfego.
- **Frontend faz fetch direto da API a cada requisição** (`cache: 'no-store'`).
  Caching real só quando colocarmos atrás de Vercel/CDN.
- **Linguagem do UI:** "Sinais de atenção" / "Índice comparativo", nunca
  "Risco". Score agregado escondido em modo cidadão.

---

## Princípios

- **Comunicação > infra.** Publicar imperfeito + visível > adiar para perfeito + invisível.
- **Progressive correctness.** Sofisticar quando houver tráfego.
- **Dados em quarentena ficam visíveis** com label, nunca somem.
- **Estatística honesta + linguagem honesta.** Mediana/IQR, não σ ingênuo.
  Linguagem factual, não acusatória.

---

## Deploy

Plano operacional para o go-live público da Fase 0.5 está em
[DEPLOY.md](./DEPLOY.md): stack (Vercel + Supabase + Cloudflare R2 +
Fly.io para o worker FastAPI + GH Actions para cron de ingestão),
ordem de operações, env vars (template em `.env.production.example`),
checklist de smoke test e rollback. Custo total Fase 0.5: US$ 0/mês
(todos free tiers). As ações que ainda dependem do usuário humano
(domínio, contas, revisão jurídica) estão listadas na seção
"Pré-requisitos".

---

## Licença

Backend: AGPL-3.0-or-later. Frontend e SDKs (futuros): MIT. Datasets
normalizados: ODbL ou CC-BY 4.0.
