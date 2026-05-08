# Quanto Pagou

Plataforma cívica para monitorar gastos públicos brasileiros e identificar possíveis desvios.

> **Status:** sprint local concluído + Fase 1 PR já no ar (~25 commits desde
> o bootstrap). Pipeline TCE-PR estadual completo (156k contratos reais de
> 397 municípios), 19 clusters keyword (33,6% cobertura), 506 escolas
> extraídas, ~25 endpoints API e 14 páginas frontend. Pendente: domínio,
> contas Vercel/Supabase/R2, revisão jurídica (ver [DEPLOY.md](./DEPLOY.md)).
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
python -m uv run python scripts/inspect_raw.py
python -m uv run python scripts/inspect_marts.py
python -m uv run pytest tests/ -v
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
    └── test_resolution.py            # 28 testes (parametrize cobrindo edge cases reais)
```

---

## API REST (Fase 0.5)

Base: `http://127.0.0.1:8001` · Docs: `/docs` · Sem auth (dados públicos).

| Endpoint                                                | Descrição                                                  |
|---------------------------------------------------------|------------------------------------------------------------|
| `GET /health`                                           | Sanidade + contagens (snapshots, raw, canonical, marts).   |
| `GET /clusters?categoria=...`                           | Lista clusters ativos com `n_itens`.                       |
| `GET /pares?cluster_id=X&cluster_version=v1`            | `mart_pares` filtrada (mediana/p25/p75 por uf+porte+ente). |
| `GET /ranking/orgaos?cluster_id=X&order=mediana_desc`   | Ranking de órgãos para o cluster (gancho viral).           |
| `GET /item/{raw_id}`                                    | Item canonicalizado + comparação com pares (ou flag de quarentena). |
| `GET /quarentena/resumo`                                | Saúde pública do pipeline (% por categoria × motivo).      |

---

## Páginas do frontend

| Rota                       | Conteúdo                                                                                        |
|----------------------------|-------------------------------------------------------------------------------------------------|
| `/`                        | Landing reestruturada em 3 zonas: Paraná real (top municípios + top fornecedores) / Federal fixture (insight diesel + ranking) / Categorias separadas. CTAs Buscar/Comparar/Manifesto. |
| `/buscar`                  | Busca de municípios PR (top 30 ou filtro por nome) e fornecedores (top 30 por volume, filtro nome ou CNPJ). |
| `/comparar`                | Município × município por cluster (lado a lado, até 6 cidades, default Curitiba × Toledo em merenda escolar). |
| `/escolas`                 | Catálogo de obras escolares (506 escolas extraídas via regex no objeto). Auditoria de transparência — não ranking. |
| `/escolas/[slug]`          | Drill-down para uma escola: stats + lista de contratos vinculados. |
| `/municipio/[cd_tce]`      | Página genérica para qualquer município PR: top fornecedores, contratos por categoria, comparação contra cidades-pares (cards clicáveis), atalhos por cluster. |
| `/curitiba`                | Atalho hardcoded para 4106902 + seção secundária de busca em diários oficiais via Querido Diário. |
| `/fornecedor/[cnpj]`       | Perfil do fornecedor com guardrails §6.5 (threshold ≥ 5 contratos, modal "como interpretar", `noindex,nofollow`, sem ranking implícito). Distribuição por órgão/município/categoria/modalidade + top 30 contratos clicáveis. |
| `/contrato/[id]`           | Detalhe completo do contrato + link para fonte primária (ZIP TCE-PR ou PNCP) + raw_payload para auditoria. |
| `/insight/diesel-ministerios` | Análise editorial sobre o spread entre ministérios federais comprando o mesmo diesel S10 (fixture). |
| `/cluster/[cluster_id]`    | Distribuição p25-p75 entre pares + ranking de órgãos (federal CATMAT; vazio para clusters TCE-PR — pendência registrada em `todo.txt`). |
| `/item/[raw_id]`           | Card narrativo §6.1 do plano: barras "você vs mediana", badge de confiabilidade, sinais decompostos. |
| `/manifesto`               | Por que existe a plataforma — gap do Painel de Preços + tese + princípios + licenças.          |
| `/metodologia`             | Fontes, resolução, normalização de unidade, política de correção.                              |
| `/correcoes`               | Página viva — onde aparecem correções pós-relato.                                              |
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
