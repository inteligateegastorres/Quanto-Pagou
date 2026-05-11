# Plano de Desenvolvimento — Quanto Pagou

> Plataforma cívica para monitorar gastos públicos brasileiros e identificar possíveis desvios.

**Versão:** v5.5 (2026-05-11)
**Status:** v5 + manchetes algorítmicas + Wave A (higiene) completa +
Wave B (estrutura) parcial + Wave LGPD documentada (§18) com L.1, L.2
(heurística v1), L.9 (doc) e L.10 implementados. **Não pronto para
go-live público** — restam L.3-L.8, L.11-L.15 + ajustes em L.2.b
(MV/frontend) e L.9.b/c (CLI/cron). Ver §18.3.

---

## v5.1 (2026-05-09) — status de implementação

**Frente narrativa — todas implementadas:**

| Proposta | Status | Onde |
|---|---|---|
| 1.a Modal "Como interpretar" | ✅ implementado | `/metodologia` (`<details>` em §IQR) |
| 1.b "Por que confiar / Por que duvidar" | ✅ implementado | `/metodologia` (2 colunas no topo) |
| 1.c Reescrita da home | ⚠️ Zona A apenas | Manchete acima do fold puxa rank=1 da API |
| 1.d `/correcoes` como vitrine | ⚠️ texto + form, sem schema | `analytics.correcoes` adiado até 1º relato |

**Frente roadmap — 3 de 4 implementadas:**

| Proposta | Status | Onde |
|---|---|---|
| 2.a 5 templates de insight | ⚠️ substituído por sistema /manchetes | §15 |
| 2.b Família de 6 badges | ✅ implementado | `lib/Badge.tsx` em 4 páginas |
| 2.c Próxima manchete (medicamentos) | ⚠️ exploração feita; publicação pendente | §13.7 atualizada com achados |
| 2.d Comparação por escola Abordagem 1 | ✅ implementado | `/escolas/[slug]` ordenado por valor |

**Sistema novo (não estava na v5 original):**
**Manchetes algorítmicas** — vide §15 (3 camadas SQL + YAML + estabilidade
temporal + vela apagada + busca reversa). Substitui parcialmente 2.a; o
algoritmo seleciona discrepâncias sem curadoria humana.

**Próximos passos pós-v5:** §16 (3 sessões A/B/C — todas implementadas
em 2026-05-09; resta operacional + Fase 1+).

---

## Changelog desde v4 (2026-05-02 → 2026-05-09)

Mudanças relevantes ao plano original (não invalidam decisões, complementam):

- **Drill-down universal** em `/contratos`: toda agregação no site
  abre lá filtrada (cluster, fornecedor, município, modalidade, q,
  datas, ordenação). Implementa o §4 "navegabilidade" do plano de
  forma sistemática.
- **Busca tripla decomposta** — três páginas para três perguntas
  diferentes: `/buscar` (combinada município+fornecedor),
  `/fornecedores` (empresa que recebeu pagamento), `/instituicoes`
  (destinatário no objeto: UPA/escola/hospital). Antes estava tudo
  amarrado em `/buscar`; separação tornou cada pergunta nítida.
- **Filtro de data obrigatório** em `/comparar` (PLANO §6.2): agora
  formulário bloqueia comparação sem `since`/`until`.
- **`/curitiba` virou redirect** para `/municipio/410690` — página
  genérica de município PR cobre o caso.
- **Endpoint `/instituicoes/search`** ganhou agregado{" "}
  `fornecedores_no_objeto` que responde diretamente "qual empresa
  recebeu por entregar a esta instituição".
- **QA versionado**: `tests/qa/CHECKLIST.md` (3 partes: backend,
  frontend, integração) + `tests/qa/FINDINGS.md` (template para
  registrar bugs). Aplicável local e em produção.
- **Cron weekly** ativo (GitHub Actions) atualizando `last_snapshot_at`
  exposto em `/stats/pr`.
- **Docs sincronizadas**: README (tabelas atualizadas), `/metodologia`
  (v0.2 com TCE-PR, Tier 1.5, IQR honesto, guardrail §6.5,
  limites por design), DEPLOY (smoke test expandido).

> **Tese:** este projeto não é "infra de dados" — é **produto de comunicação pública** apoiado em infra de dados. O sucesso mora em **clareza + confiança + compartilhabilidade**. Toda feature é avaliada por: *"isso vira algo que alguém manda no WhatsApp da família?"*

---

## 1. Visão

Plataforma aberta para a população brasileira monitorar gastos públicos em todos os níveis (federal, estadual, municipal) e identificar possíveis desvios de verba pública através de comparação de preços, sinais de atenção e narrativa cívica.

**Princípios:**
- **Comunicação > infra.** Sem distribuição e clareza, vira mais um Brasil.IO de nicho.
- **Progressive correctness.** Maturidade técnica é destino, não ponto de partida. Tier 1 + golden set pequeno + drift manual no início; sofisticar quando houver tráfego e feedback. **Publicar imperfeito + visível > adiar para perfeito + invisível.**
- **Estatística honesta + linguagem honesta.** Estatística robusta, linguagem factual, agregação numérica escondida por padrão.
- **Integridade de comparações.** Cluster versionado, unidade normalizada, golden set — sem essas três, comparação não vai ao ar.
- **Quarentena visível.** Itens não-comparáveis aparecem com label, nunca somem.
- **Qualidade medida e publicada.** Precisão/recall por categoria visíveis no site.
- **Contribuir > reinventar.** Maximizar uso e contribuição em OSS existente.
- **Atualização semanal**, não tempo real.

---

## 2. Público-alvo

| Persona | Necessidade | Entrega principal |
|---|---|---|
| Cidadão leigo | "Meu prefeito está gastando muito?" | Card narrativo com pares relevantes (mesma UF + porte), histórico, badge de confiabilidade — agregado escondido |
| Jornalista | Investigação em pauta | Filtros, exportação CSV/Parquet, score decomposto, página de fornecedor, fonte primária |
| Pesquisador | Análise quantitativa | API pública, dump versionado, snapshots reprodutíveis, modelo aberto |
| Servidor de controle (TC, MP, CGU) | Triagem | Painel com componentes do score expostos, intervalos de confiança |

---

## 3. Estado do ecossistema OSS (2026-05)

### 3.1 Projetos para alavancar

| Projeto | Cobertura | Status | Como aproveitar |
|---|---|---|---|
| **Querido Diário** (OKBR) — github.com/okfn-brasil/querido-diario | Diários oficiais municipais (151 cidades, meta 250 em 2026) | Vivo, MIT, API aberta | Base municipal. Contribuir spiders novas; consumir API para extração |
| **Tá de Pé Dados** — github.com/analytics-ufcg/ta-de-pe-dados | TCE-RS, TCE-PE, Receita Federal, Compras Federal | Vivo | Esqueleto inicial; PRs upstream com novos adapters |
| **Brasil.IO** — brasil.io | Gastos diretos federais (SIAFI), CNPJs | Vivo | Consumir como dependência |
| **Serenata de Amor / Rosie** | CEAP parlamentar federal | Manutenção (~1x/mês manual) | Referência arquitetural |
| **Achados e Pedidos** (TB + Abraji) | Pedidos LAI | Vivo | Integração futura — gatilho automático de LAI |

### 3.2 APIs governamentais relevantes

- **Portal da Transparência Federal** — portaldatransparencia.gov.br/api-de-dados
- **Compras.gov.br** — dadosabertos.compras.gov.br (CATMAT/CATSER, licitações, contratos, empenhos)
- **Tesouro Transparente / SICONFI** — receitas/despesas estaduais e municipais
- **dados.gov.br** — catálogo geral

### 3.3 Gap institucional

**Painel de Preços oficial** (paineldeprecos.planejamento.gov.br) parou de receber atualizações em 04/jul/2025. Existe lacuna direta — Fase 1 desta plataforma é o sucessor cívico.

---

## 4. Gaps técnicos + ganchos virais

**Gaps técnicos:**
1. Sucessor cívico do Painel de Preços federal.
2. Comparação cross-ente (federal × estadual × municipal) inexistente consolidada.
3. Granularidade municipal item-a-item depende de extração estruturada de PDFs.
4. UX para leigos é praticamente inexistente.

**Ganchos virais (entregáveis-bandeira para distribuição):**
- 🏆 **"Top 10 cidades que pagam mais caro pela merenda escolar"** (Fase 3)
- 🏛️ **"Ranking dos órgãos federais com maior preço médio por categoria"** (Fase 1)
- 🗺️ **"Mapa: quanto seu município paga vs vizinhos do mesmo porte"** (Fase 2-3)
- 📈 **"Quem subiu/caiu no ranking esta semana"** (boletim semanal automatizado)
- 🔍 **"Top fornecedores recorrentes em dispensas de licitação"** (Fase 1-2)
- 📰 **"Insight da semana"** — story curada, baseada em dados, formato compartilhável

Cada gancho com link curto, OG image dinâmica e formato pronto para X/Bluesky/Instagram/WhatsApp.

---

## 5. Arquitetura proposta

### 5.1 Pipeline

```
┌─────────────────────────────────────────────────────────┐
│  FONTES (semanal)                                       │
│  Compras.gov.br · Portal Transparência · TCEs · QD · BIO│
└────────────────┬────────────────────────────────────────┘
                 │
        ┌────────▼─────────┐
        │  Ingest workers  │  Python (Scrapy + httpx)
        └────────┬─────────┘
                 │
        ┌────────▼──────────────┐
        │  Raw + DURABILITY     │  Postgres + R2 snapshots imutáveis
        │  layer                │  cada coleta hash-versionada
        └────────┬──────────────┘
                 │
        ┌────────▼──────────────┐
        │  ITEM RESOLUTION      │  Tier 1 CATMAT → Tier 2 embeddings →
        │  (versioned clusters) │  Tier 3 dicionários → Tier 4 LLM
        │  + golden set + drift │  cluster_id sempre versionado
        └────────┬──────────────┘
                 │
        ┌────────▼──────────────┐
        │  UNIT NORMALIZATION   │  *** novo em v3 ***
        │  layer                │  unidade_base + valor_normalizado
        │                       │  quarentena se ambíguo
        └────────┬──────────────┘
                 │
        ┌────────▼─────────┐
        │  Normalização    │  dbt → schema canônico
        └────────┬─────────┘
                 │
        ┌────────▼──────────────┐
        │  Marts + RISK MODEL   │  composto, robusto, decomposto no UI
        │  (interno: risk_score)│  externo: "Sinais de atenção"
        │                       │  intervalos de confiança preservados
        └────────┬──────────────┘
                 │
   ┌─────────────┼──────────────────┐
   ▼             ▼                  ▼
┌──────┐   ┌──────────┐     ┌──────────────────┐
│ API  │   │ Frontend │     │ Boletim semanal  │
│ REST │   │ Next.js  │     │ + alertas opt-in │
│      │   │ + SSG    │     │ + correções pub. │
└──────┘   └──────────┘     └──────────────────┘
```

### 5.2 Schema canônico do "item-comprado"

```jsonc
{
  "id": "uuid",
  "fonte": "compras.gov.br | tce-sp | querido-diario | ...",
  "fonte_url": "string (link primário sempre presente)",
  "snapshot_id": "ref ao snapshot da camada de durabilidade",
  "data": "date",
  "ente": {
    "nivel": "federal|estadual|municipal",
    "uf": "string", "municipio": "string?",
    "orgao": "string", "porte": "string"
  },
  "item": {
    "catmat_id": "string?",
    "catser_id": "string?",
    "descricao_original": "string",
    "descricao_normalizada": "string",
    "cluster_id": "string (output da resolução)",
    "cluster_version": "string (ex: arroz_v1)",         // novo v3
    "categoria": "string",
    "confianca_resolucao": "float 0-1"
  },
  "quantidade": "number",
  "unidade": "string",
  "unidade_base": "string (kg|litro|unidade|...)",       // novo v3
  "fator_conversao": "decimal",                          // novo v3
  "valor_unitario": "decimal",
  "valor_unitario_normalizado": "decimal (por unidade_base)", // novo v3
  "valor_total": "decimal",
  "modalidade": "string",
  "fornecedor": { "cnpj": "string", "nome": "string" },
  "contrato_id": "string?",
  "edital_id": "string?",
  "ingerido_em": "timestamp",
  "qualidade": {
    "precisao_extracao": "float?",
    "metodo": "api|scraper|llm-extract",
    "em_quarentena": "bool"                              // novo v3
  }
}
```

### 5.3 Camada de resolução de itens (com versionamento e golden set)

**Problema:** "arroz tipo 1" vs "arroz beneficiado longo fino tipo 1 pacote 5kg" precisam ser comparados como o mesmo produto. CATMAT cobre só federal.

**Pipeline em 4 tiers:**
1. **Tier 1 — CATMAT/CATSER direto** quando disponível.
2. **Tier 2 — Embeddings + clustering:** `bge-m3` ou `e5-multilingual` + HDBSCAN por categoria.
3. **Tier 3 — Dicionário curado por categoria** (revisado por PR; categorias-piloto: merenda, medicamentos, combustível).
4. **Tier 4 — LLM resolver** quando ambíguo (Claude/Llama com prompt estruturado + confiança).

**Versionamento de clusters (governança crítica):**
- Cada cluster recebe versão (`arroz_v1`, `arroz_v2`).
- Histórico **nunca é reescrito** — comparações cross-versão exigem mapeamento explícito documentado.
- Quando o modelo de embeddings muda ou um cluster é split/merge, gera-se nova versão; dados antigos preservam seu `cluster_version` original.
- Tabela `cluster_registry(cluster_id, cluster_version, descricao_canonica, criado_em, ativo, mapeamento_de)`.

**Golden set em dois níveis (não-bloqueante):**
- **Core set** (50-100 itens fixos por categoria-piloto): usado em testes de regressão automatizados; mudança requer PR revisado.
- **Extended set** (rotativo, amostrado): cresce ao longo do tempo via revisão humana e contribuições OSS via microtasks ("help label this item").
- Versionado no repositório como CSV. Núcleo pequeno permite começar; extensão acompanha tráfego.

**Drift monitoring (ativação progressiva):**
- **Fase 0-1:** verificação manual semanal contra core set; alerta no terminal/log.
- **Fase 2+:** job automatizado, alerta se precisão cai > 5pp, página interna de saúde de clusters.

**Saída obrigatória:** `cluster_id`, `cluster_version`, `confianca_resolucao` (0-1).
Comparações públicas só com `confianca_resolucao ≥ 0.75` (threshold versionado em config). Itens abaixo do threshold ou em quarentena aparecem com label "não comparável ainda" — não somem (ver 5.6).

**Ativação por fase:**

| Tier | Fase 0 | Fase 1 | Fase 2 | Fase 3 |
|---|---|---|---|---|
| Tier 1 (CATMAT direto) | ✓ | ✓ | ✓ | ✓ |
| Tier 2 (embeddings) | — | ✓ (top categorias) | ✓ (todas) | ✓ |
| Tier 3 (dicionários curados) | — | — | ✓ | ✓ |
| Tier 4 (LLM resolver) | — | — | — | ✓ |
| Drift monitoring automático | — | — | ✓ | ✓ |
| Cluster split/merge sofisticado | — | — | — | ✓ |

### 5.4 Modelo de risco — técnico vs UI

**Internamente** (`risk_score` ∈ [0, 100]):

| Componente | Peso | Cálculo |
|---|---|---|
| `price_premium` | 0.40 | (preço − mediana_pares) / IQR_pares; clipped [0, 1]; pares = mesma UF + mesmo porte + faixa de quantidade |
| `supplier_concentration` | 0.20 | Herfindahl do fornecedor naquele órgão últimos 24m |
| `competition` | 0.15 | inverso do nº de propostas válidas |
| `modality_risk` | 0.15 | dispensa=1.0, inexigibilidade=0.9, pregão=0.2, concorrência=0.1 |
| `temporal_anomaly` | 0.10 | z-score robusto do mesmo cluster no tempo |

Pesos versionados em `risk_model.yaml`. Calibração contra ~50 casos conhecidos TCU/CGU.

**No UI público (regra de produto):**

| Modo | O que aparece |
|---|---|
| **Cidadão (default)** | Componentes individuais como "sinais", agregado **oculto**. Linguagem: "preço acima de pares", "fornecedor recorrente", "pouca concorrência" |
| **Pesquisador / avançado** | Score agregado visível, tooltip com fórmula, link para `risk_model.yaml` |

**Renomeação no UI:**
- "Risco" → **"Sinais de atenção"** (genérico) ou **"Índice comparativo"** (específico de preço)
- "Score" não aparece para cidadão. Modo avançado mostra como "Índice composto"
- `risk_score` permanece como nome técnico interno apenas

### 5.5 Camada de durabilidade (snapshots versionados)

Para sobreviver a APIs governamentais que somem (caso Painel de Preços jul/2025):
- Cada coleta gera snapshot bruto imutável em Cloudflare R2.
- Tabela `snapshots(id, fonte, periodo, hash_sha256, registros, ingerido_em, schema_version)`.
- Pipeline = função pura sobre snapshots (reprocessamento sempre reproduzível).
- Dump mensal em Parquet em mirror público (Hugging Face datasets ou Internet Archive).

### 5.6 Camada de normalização de unidade (nova em v3)

Antes de qualquer comparação, todo item é convertido para unidade base:

| Categoria | Unidade base |
|---|---|
| Alimentos sólidos | kg |
| Líquidos | litro |
| Materiais discretos | unidade |
| Combustíveis | litro |
| Serviços | hora ou unidade |
| Obras | m² ou m³ |

**Pipeline:**
1. Parser textual extrai unidade da `descricao_original` ("pacote 5kg", "caixa com 12", "galão 20L").
2. Tabela de fatores de conversão (`unit_conversion.yaml`) versionada.
3. Calcula `valor_unitario_normalizado = valor_unitario / fator_conversao` na unidade base da categoria.
4. Se parser falhar ou descrição for ambígua: item entra em `qualidade.em_quarentena = true`.

**Quarentena ≠ invisibilidade (regra v4):**
- Itens em quarentena **continuam visíveis** com label "não comparável ainda" + tooltip explicando o motivo.
- Página individual com URL canônica e fonte primária acessíveis.
- Botão "ajudar a classificar" → microtask de contribuição (alimenta extended golden set).
- **Nunca** entram em rankings, agregações, OG images compartilháveis.

**Métricas publicadas:** % de itens em quarentena por categoria e por fonte.

---

## 6. Camada de produto e comunicação

### 6.1 Componente narrativo padrão (template)

Todo item / órgão / município usa este card:

```
┌─────────────────────────────────────────────────┐
│ 🍞 {Município}, {UF}                           │
│                                                 │
│ Pagou R$ {valor_norm} por {item}                │
│ ({unidade_base})                                │
│ em {data} · {fornecedor}                        │
│                                                 │
│ Comparando com: [pares ▼ UF | porte | nacional] │ ← toggle
│                                                 │
│ ▓▓▓▓▓▓▓▓▓░░  R$ {você}                          │
│ ▓▓▓▓░░░░░░░  R$ {mediana_pares} (cidades        │
│              do mesmo porte na {UF})            │
│ ░ intervalo: R$ {p25} – R$ {p75}                │ ← incerteza visível
│                                                 │
│ → {pct}% acima da mediana de pares              │
│ → Posição: {rank}º entre {n} cidades similares  │
│                                                 │
│ 📈 Histórico (últimos 24m):                     │
│    ▁▁▂▂▃▄▅▆▆▇█  ← sparkline preço x tempo       │ ← novo v3
│                                                 │
│ Sinais de atenção:                              │ ← antes "Risco"
│  • Preço acima de pares (alto)                  │
│  • Fornecedor recorrente neste órgão (médio)    │
│  • Modalidade: dispensa (alto)                  │
│  [ver mais sinais →]                            │
│                                                 │
│ [Confiabilidade: ALTA · CATMAT match] (badge)   │
│                                                 │
│ [📄 Ver fonte primária]  [✉️ Pedir LAI]         │
│ [🚩 Reportar erro]       [🔗 Compartilhar]      │
└─────────────────────────────────────────────────┘
```

**Regras de redação:**
- Comparação **default**: pares (mesmo porte/UF). Toggle expõe nacional/histórico.
- Sempre mostrar intervalo (p25-p75) — incerteza visível.
- Linguagem factual: "pagou R$X por Y". Nunca "suspeito", "irregular", "desviado".
- Sparkline obrigatório quando há ≥ 6 pontos históricos.
- Score agregado **escondido** em modo cidadão.

**Affordances v4 (novas):**
- **Botão "Explicar como se eu fosse leigo"**: alterna o card para versão WhatsApp-friendly — uma frase única ("A sua prefeitura paga 71% mais por arroz que cidades parecidas. Veja por quê."). Mantém link para fonte e botão de compartilhar.
- **Alertas de mudança automáticos** (quando há histórico): badge "📈 +40% nos últimos 6m" ou "📉 -15% no último ano" gerado pelo pipeline.
- **Comparações emocionalmente ancoradas (opcional, contextual)**: em rankings selecionados, adicionar conversões intuitivas — "esse valor extra pagaria X merendas escolares" / "equivale a Y salários mínimos". Apenas onde o cálculo for inequívoco; nunca em itens individuais para evitar manipulação narrativa.

### 6.2 Badges de confiabilidade

| Badge | Critério | Cor |
|---|---|---|
| **Dados completos** | API estruturada + CATMAT/CATSER + sem extração LLM | verde |
| **Dados parciais** | Cluster por embeddings, confiança ≥ 0.75 | amarelo |
| **Baixa confiabilidade** | Extração LLM de PDF, confiança < 0.75 | laranja |
| **Em verificação** | Dado novo, ainda sem amostra de validação | cinza |

Cada badge clicável abre modal: como o dado foi coletado, como o item foi resolvido, limitações.

### 6.3 Página "Metodologia" (obrigatória no MVP)

Explica fontes, periodicidade, fórmula do score, limites de cluster_version, política de correção (SLA: 48h), como reportar erro.

**Versão visual (Fase 1+):** diagramas curtos para "como calculamos comparação", "como normalizamos unidade", "o que é cluster". Objetivo: jornalistas reusarem direto em matérias.

### 6.4 Estratégia de aquisição e loop de crescimento (nova em v3)

**Canais prioritários por fase:**

| Fase | Canal principal | Canal secundário |
|---|---|---|
| 0.5 | Twitter/X + Bluesky (policy nerds, dataviz) | Newsletters Abraji + Escola de Dados |
| 1 | Mesmo + jornalismo investigativo (parcerias diretas) | Reddit r/brasil |
| 2 | Imprensa estadual (G1 regionais, Folha) | Twitter + comunidades técnicas |
| 3 | Imprensa local (foco merenda) | TV regional, podcasts cívicos |

**Loop de crescimento explícito:**

```
1. Usuário vê ranking ("Top 10 cidades que pagam mais caro por X")
2. Curioso, clica em "minha cidade"
3. Vê comparação com pares + histórico
4. Indignado/curioso, compartilha (OG image pronta)
5. Novo usuário entra na home
6. Boletim semanal puxa de volta toda semana
```

**Mecanismos suportando o loop:**
- OG image dinâmica em **toda** página (cidade, fornecedor, ranking).
- Página por município com slug SEO-amigável (ex: `/municipio/sp/sao-paulo`).
- Embeds para sites de jornalismo (iframe + script) já desde Fase 1.

**Conteúdo em duas esteiras (regra v4 — desacopla cadência):**

| Esteira | Cadência | Conteúdo | Produção |
|---|---|---|---|
| **Automática** | semanal, infinita | "Quem subiu/caiu", Top 10 da semana, alertas de delta significativo, rankings recalculados | Pipeline, sem mão humana |
| **Editorial** | irregular, 1-3x/mês | Análise profunda, narrativa investigativa, insight inesperado | Produção curada — vazia se não houver |

Boletim semanal sempre tem a esteira automática + uma seção editorial **opcional** (oculta se vazia). Nunca prometer cadência editorial específica.

**Parcerias estruturadas (a partir da Fase 0.5):**
- Abraji (jornalismo investigativo) — apresentar plataforma como ferramenta para associados.
- Escola de Dados (Open Knowledge) — workshops e conteúdo conjunto.
- Newsletters de jornalismo de dados (Núcleo, Aos Fatos, Lupa) — co-publicação de "Insight da semana" editorial.
- Universidades com laboratórios de jornalismo de dados (UFCG, UFRJ, USP) — projetos finais de curso usando a API.

### 6.5 Página de fornecedor (entidade) — guardrails reforçados em v4

Página por CNPJ (`/fornecedor/{cnpj}/{slug}`):

- **Modal obrigatório no primeiro acesso:** "Como interpretar este perfil — esta página apresenta dados públicos extraídos de portais oficiais. A presença de um fornecedor aqui não implica irregularidade."
- **Threshold mínimo (regra v4):** página só é gerada para fornecedores com **≥ 5 contratos públicos** registrados (filtra fornecedores eventuais e reduz risco de exposição injusta).
- **Delay de publicação (regra v4):** dados de novos contratos só aparecem na página após **30 dias** da assinatura — protege contra erros de ingestão e dá margem para correções.
- **Sem ranking implícito (regra v4):** **não ordenar fornecedores por "pior"**. Listas de fornecedores são neutras (alfabética, ou filtros explícitos do usuário).
- **Conteúdo:**
  - Identificação (CNPJ, razão social, ramo)
  - Total de contratos públicos por ano (timeline)
  - Concentração por órgão (Herfindahl visualizado, com explicação simples)
  - Distribuição por modalidade
  - Top itens fornecidos (com preço médio)
  - Sinais de atenção como na 6.1, **decompostos** (nunca agregado)
  - Fonte primária em **cada linha**
- **Linguagem factual estrita:** "ganhou X contratos em Y", "modalidade mais frequente: Z". Nunca "monopolizou", "suspeito", "predominou".
- **Botão "reportar erro"** + SLA 48h destacado.
- **Excluir do indexamento de buscas** (`noindex, nofollow`) **na Fase 1**; reavaliar com revisão jurídica antes de tornar SEO-amigável.

### 6.6 Página "Correções recentes" (nova em v3 — diferencial)

`/correcoes` — pública, atualizada em tempo real:

- Toda correção feita após `🚩 Reportar erro` aparece aqui.
- Formato: data · item afetado · motivo · antes → depois · revisor.
- RSS feed disponível.
- Vantagem competitiva: quase nenhum projeto público faz isso ativamente.

---

## 7. Stack proposta (confirmada)

| Camada | Tecnologia | Razão |
|---|---|---|
| Ingestão | Python 3.12 + Scrapy + httpx | Padrão OSS BR |
| Banco | Postgres 16 (Supabase) | Volume estimado ano 1: ~50-100 GB |
| Object storage | Cloudflare R2 | Egress barato |
| Resolução de itens | sentence-transformers (bge-m3) + HDBSCAN | OSS, roda em CPU |
| Transformação | dbt-core | Versionamento + testes de dados |
| Risk scoring | Python + Pydantic + YAML config | Auditável |
| Extração de PDF | Tesseract + pdfplumber + LLM fallback | Fase 3+ |
| API | FastAPI | OpenAPI nativo |
| Frontend | Next.js 15 + Tailwind + shadcn/ui | SSG + componentes acessíveis |
| OG images | @vercel/og | Cards de compartilhamento |
| Hospedagem | **Vercel + Supabase + R2** ✓ | Velocidade > otimização de custo |
| Agendamento | GitHub Actions (Fase 0-2) → Airflow (Fase 3+) | Evolução |
| Observabilidade | Sentry + Plausible | Free tiers |
| Email/boletim | Resend ou Buttondown | Free tier |

---

## 8. Roadmap em fases

### Fase 0 — Fundação (1-2 semanas)
- [ ] Criar organização GitHub `quanto-pagou` (ou similar)
- [ ] Criar repositório com README, LICENSE multi-camada, CONTRIBUTING, CODE_OF_CONDUCT
- [ ] Avaliar fork do Tá de Pé Dados vs clone limpo
- [ ] Setup Docker Compose (Postgres + worker + minio simulando R2 local)
- [ ] CI mínimo (lint, type check, testes)
- [ ] Primeira spider Compras.gov.br → tabela raw + snapshot R2
- [ ] Esqueleto da camada de durabilidade funcional já no primeiro PR
- [ ] Esqueleto do `cluster_registry` e `unit_conversion.yaml`

**Entregável:** repositório público com 1 dataset ingerido, snapshot durável, docs.

### Fase 0.5 — Lançamento editorial (2 semanas, paralelo) ⭐ reformulada em v3
**Objetivo:** ter algo compartilhável e cativante **antes** de a infra estar pronta.

- [ ] Domínio definitivo + landing page
- [ ] **Manifesto** explicando o problema (Painel de Preços descontinuado, gap cívico)
- [ ] **1 história concreta real** — análise editorial baseada em ~1 mês de dados federais (ex: "Órgãos federais que pagam mais caro pela mesma caneta — comparação direta")
- [ ] **1 ranking real funcional** — Top 10 órgãos com maior preço médio em 1 categoria
- [ ] **1 insight inesperado** — o tipo de coisa que vira manchete (extraído da análise dos dados)
- [ ] OG images dinâmicas para cada um dos três conteúdos
- [ ] Formulário de inscrição em boletim semanal (Buttondown/Resend)
- [ ] Página "metodologia" v1
- [ ] Página "correções recentes" (vazia mas no ar)
- [ ] Distribuição: Twitter + Bluesky + 3 newsletters (Abraji, Escola de Dados, Núcleo)

**Entregável:** site no ar com narrativa e dados reais. Captura interesse, valida tese, alimenta lista para boletim antes do produto completo.

### Fase 1 — MVP Federal "Painel de Preços vivo" (5-8 semanas)

> **Progressive correctness (v4):** Tier 2 e 3 entram com escopo reduzido; drift automático e cluster sofisticado são deferidos para Fase 2. Foco aqui é cobertura ampla com Tier 1 + governance básica.

- [ ] Ingestão completa: Compras.gov.br + Portal da Transparência
- [ ] Camada de resolução — Tier 1 (CATMAT) operacional; Tier 2 (embeddings) **só nas top 5 categorias** mais frequentes
- [ ] **Cluster versioning ativo + core golden set** (50-100 itens) + drift manual semanal
- [ ] **Camada de normalização de unidade** funcional para top 5 categorias
- [ ] dbt → schema canônico
- [ ] Risk score composto v1 + calibração contra 50 casos TCU/CGU
- [ ] **UI cidadão com agregado escondido + componentes decompostos**
- [ ] **UI pesquisador com score completo**
- [ ] API REST: itens, órgãos, ranking, snapshots, fornecedores
- [ ] Frontend Next.js — card narrativo padrão (6.1) com toggle de pares + sparkline + intervalo
- [ ] **Página de fornecedor** com modal de orientação e `noindex`
- [ ] **Página de correções** ativa
- [ ] ≥ 2 ganchos virais funcionais (Top órgãos + Top fornecedores em dispensas)
- [ ] Badges de confiabilidade
- [ ] Boletim semanal automatizado
- [ ] Deploy + job semanal

**Métricas de sucesso:**
- Cobertura ≥ 80% dos contratos federais com CATMAT
- Precisão da resolução ≥ 90% (Tier 1+2 amostrados via golden set)
- ≤ 5% de itens em quarentena por unidade
- Latência P95 < 1s (SSG)

### Fase 2 — Estados (5-9 semanas)

- [ ] Aproveitar adapters Tá de Pé (TCE-RS, TCE-PE)
- [ ] Adicionar TCE-SP, TCE-MG, TCE-BA, TCE-RJ — cada novo adapter como PR upstream
- [ ] Resolução Tier 3 (dicionários) ativada para categorias-piloto
- [ ] Golden set estadual (≥ 200 itens por estado)
- [ ] Comparação federal × estadual destacada no UI
- [ ] Páginas SSG por estado e órgão estadual
- [ ] Mapa interativo de comparação por UF (gancho viral novo)

**Métrica:** ≥ 6 estados (>60% PIB); precisão ≥ 85%; quarentena ≤ 10%.

### Fase 3 — Municípios via Querido Diário (12-18 semanas) ⚠️ escopo reduzido

> **Realidade ajustada na v2:** estimativa anterior de 8-12 semanas era ~3x otimista.

**Escopo inicial:**
- **3-5 cidades-piloto:** São Paulo, Recife, Porto Alegre, Belo Horizonte, Curitiba
- **1 categoria-piloto:** alimentação escolar (PNAE × CATMAT)
- Métricas explícitas de qualidade publicadas

- [ ] Pipeline Tesseract + pdfplumber + LLM fallback
- [ ] Validação humana por amostragem (≥ 100 itens revisados/cidade)
- [ ] Resolução Tier 4 (LLM) ativada
- [ ] Golden set municipal (100/cidade)
- [ ] Dashboard interno de qualidade (precisão, recall, cobertura, drift)
- [ ] Publicar externamente apenas com precisão ≥ 80% e badge correspondente
- [ ] Contribuir spiders novas para Querido Diário (meta +20 cidades)
- [ ] Gancho viral: "Top cidades-piloto que pagam mais caro pela merenda" — com badges explícitos

**Critérios de expansão (gates):**
- Pipeline atinge precisão ≥ 80% em duas cidades distintas
- Custo de revisão humana mensurável e < X horas/cidade

### Fase 4 — Camada cívica (contínua)

- [ ] Alertas Telegram/WhatsApp opt-in (segmentação por município)
- [ ] Integração Achados e Pedidos: botão "fazer LAI sobre este contrato"
- [ ] Embeds para jornalismo
- [ ] Programa de contribuidores (issues "good first issue", workshops)
- [ ] Expansão controlada de cidades/categorias na Fase 3
- [ ] Reavaliar SEO da página de fornecedor com revisão jurídica

---

## 9. Riscos e mitigações

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| APIs govs descontinuadas | Alta | Alto | Camada de durabilidade (5.5) |
| Resolução semântica baixa | Alta | Alto | 4 tiers + golden set + drift monitoring + threshold 0.75 |
| Drift silencioso de clusters | Alta | Alto | Cluster versioning + alerta 5pp + golden set semanal |
| Comparação inválida por unidade | Alta | Alto | Camada de normalização + quarentena automática |
| Falsos positivos no risco | Alta | Alto | Score decomposto, agregado escondido por padrão, calibração TCU/CGU |
| Subestimação Fase 3 | Alta (já materializado) | Médio | Escopo reduzido, gates objetivos para expansão |
| **Over-engineering atrasa lançamento** | Alta | Alto | Progressive correctness (1.) — Fase 0-1 com Tier 1 + golden set pequeno + drift manual; sofisticar só com tráfego |
| **Quarentena vira buraco negro** | Média | Médio | Itens em quarentena visíveis com label "não comparável ainda"; nunca somem do site (5.6) |
| **Bottleneck editorial semanal** | Alta | Médio | Esteira automática vs editorial separadas (6.4); cadência editorial não-prometida |
| **Acusação de difamação (fornecedor)** | Média | Alto | Linguagem factual + modal "como interpretar" + noindex Fase 1 + revisão jurídica antes de SEO + página de correções |
| Captura político-partidária | Média | Alto | CoC apartidário, mostra todos entes, repo neutro |
| Score interpretado como "corrupção" | Alta | Alto | Renomeado para "Sinais de atenção", agregado escondido cidadão |
| Burnout do mantenedor único | Alta | Alto | Doc obsessiva desde dia 1; recrutar contribuidores na Fase 0.5 |
| LLM resolver caro | Média | Médio | Tier 4 só fallback; cache de embeddings; rate limit |
| Volume explodindo | Média | Médio | Particionamento por ano/UF; dados frios em Parquet+R2 |

---

## 10. Métricas de sucesso (ano 1)

**Cobertura:**
- ≥ 80% de contratos federais com CATMAT
- ≥ 6 estados (>60% PIB nacional)
- 3-5 cidades-piloto com extração validada

**Qualidade (publicada):**
- Precisão da resolução ≥ 90% (Tier 1+2), ≥ 80% (Tier 3+4)
- Quarentena de unidade ≤ 5% federal, ≤ 15% municipal
- Calibração: top-10% do score contém ≥ 70% dos casos conhecidos TCU/CGU

**Uso e distribuição:**
- ≥ 30.000 visitantes únicos/mês até final do ano 1
- ≥ 5.000 inscritos no boletim semanal
- ≥ 5 reportagens citando a plataforma
- ≥ 50 compartilhamentos/semana de OG images de cidade-fornecedor-ranking

**Saúde OSS:**
- ≥ 5 contribuidores externos com PR mergeado
- ≥ 10 PRs upstream em Querido Diário/Tá de Pé

**Confiança:**
- ≥ 95% dos reportes de erro respondidos em ≤ 48h
- 0 ações judiciais procedentes (KPI essencial)

**Sustentabilidade:**
- Custo operacional < US$ 200/mês ou financiamento garantido por 12 meses

---

## 11. Decisões (confirmadas em v3 — 2026-05-02)

| # | Decisão | Confirmado |
|---|---|---|
| 11.1 | **Licença em 3 camadas:** AGPL backend / MIT SDK + frontend / ODbL ou CC-BY datasets normalizados | ✓ |
| 11.2 | **Nome:** **Quanto Pagou** | ✓ |
| 11.3 | **Hospedagem:** Vercel + Supabase + Cloudflare R2 | ✓ |
| 11.4 | **Ordem:** Fase 0 → 0.5 (paralelo) → 1 → 2 → 3 → 4 | ✓ |
| 11.5 | **Repositório:** organização nova no GitHub (sugestão `quanto-pagou`) | ✓ |

**Pendências menores:**
- Domínio: comprar `quantopagou.org` / `.com.br` (verificar disponibilidade)
- E-mail institucional + persona pública
- Revisão jurídica preliminar **antes do lançamento da Fase 0.5** com narrativa pública

---

## 12. Próximos passos imediatos — sprint de 7 dias

> **Princípio v4:** parar de planejar, começar a executar. Algo imperfeito e útil no ar > algo perfeito e invisível.

**Sprint local de 7 dias** (executável sem domínio/Vercel/conta GitHub-org pronta — entregue em `C:\tmp\projetos\gov`, deploy quando o gating estiver feito):

| Dia | Entregável |
|---|---|
| 1 | Estrutura do repo (Python + Docker Compose com Postgres + minio simulando R2). README mínimo. CI lint+test. |
| 2 | Primeira spider Compras.gov.br ingerindo 12 meses de contratos federais. Snapshots brutos persistidos. |
| 2-3 | Tier 1 (CATMAT direto). `unit_conversion.yaml` com top 5 categorias. Core golden set (50 itens). |
| 3-4 | dbt: schema canônico + 1 mart (mediana_pares por CATMAT × UF × porte). |
| 4-5 | API FastAPI mínima (itens, ranking, saúde). Frontend Next.js com 1 ranking real + card narrativo (6.1) + 1 página de item. |
| 5-6 | **Análise editorial real:** rodar a base, encontrar 1 história ("órgãos federais que pagam mais caro pela mesma X"), escrever em ~500 palavras. Gerar OG images. |
| 6-7 | Polimento. Manifesto + página metodologia + página correções (vazia). Empacotamento para deploy. |

**O que requer ação do usuário (em paralelo, não bloqueante para os 7 dias):**
1. Verificar/comprar domínio `quantopagou.org` / `.com.br`
2. Criar organização GitHub `quanto-pagou`
3. Criar conta Vercel + projeto Supabase + bucket Cloudflare R2 (free tier)
4. Conta Buttondown ou Resend para boletim
5. Revisão jurídica preliminar do manifesto + página de fornecedor (antes do go-live público)

**Após dia 7:** se a infra estiver pronta → deploy + lançamento Fase 0.5 + distribuição (3 newsletters). Se não → continua iterando local até gating fechar.

---

## 13. Propostas v5 — detalhamento (2026-05-09)

Detalha as 8 propostas resumidas no topo. Conservar até a implementação
fechar — depois, o que vingou vira parágrafo nas seções §6.X
correspondentes e este §13 pode ser removido.

### 13.1 Modal "Como interpretar" (refina §6.3)

**Onde:** `<details>` em `/metodologia` + CTA "Como ler?" ao lado de
toda barra p25-p75 (cards `/item/[raw_id]`, `/cluster/[id]`, `/comparar`).

**Quatro quadros, ordem fixa:**

1. **O que você está vendo** — preço pago + intervalo onde caem 50% dos
   pares. Comparação por unidade-base normalizada.
2. **Por que faixa, não número único** — preço público varia
   legitimamente; estar fora da faixa não é prova de irregularidade.
3. **As 3 cores que você verá** — verde (dentro p25-p75) / amarelo
   (acima p75, vale entender por quê) / vermelho (≥ 2× mediana, vale
   checar — nunca "irregular").
4. **O que pode estar errado neste número** — fontes de erro (cluster
   errado, unidade mal parseada, escopo atípico) + link `/correcoes`
   + formulário de relato.

### 13.2 "Por que confiar / Por que duvidar" (refina §6.3)

**Onde:** após `<h1>` em `/metodologia`, antes de "Fontes". Duas colunas
simétricas (mesma quantidade de bullets, mesmo peso visual).

**Confiar:** fonte primária pública · snapshot SHA-256 · confiança ≥
0.75 · mediana+IQR não σ · quarentena visível · `/correcoes` datada.

**Duvidar:** cobertura keyword 34% no PR · granularidade só por contrato
(não item-a-item) · modalidade ~65% · federal hoje fixture · cluster
Tier 1.5 (embeddings adiados).

### 13.3 Home reescrita (refina §6.4)

**3 zonas (vs 4 atuais), inversão de ordem:**

- **A · Manchete (above fold):** insight da semana com número de
  impacto (ex: "Maringá pagou 10× mais por kg de merenda que Cascavel").
  CTAs "Ler análise" + "Ver os contratos". Stats descem para footer
  da manchete ("156k contratos · 397 municípios").
- **B · Evidência (a régua):** 4 bullets explicando como sabemos.
  Vacina anti-objeção complementar a 14.2.
- **C · Navegue:** 4 entradas (município/fornecedor/categoria/escola)
  + busca rápida + lista de destaques. Categorias monitoradas SAEM da
  home (vão pra footer ou `/categorias`).
- **D · Boletim + rodapé:** mantém atual.

**Risco:** manchete fica datada. Mitigação: cron weekly de 13.5 alimenta
o slot da manchete com hierarquia (curado vivo > T1 da semana > último
curado).

### 13.4 `/correcoes` como vitrine (refina §6.6)

**3 movimentos:**

- **Reformular página:** texto sobre o processo (4 passos) +
  formulário inline + linha "sem correções = ninguém pegou erro grande
  ainda, não é vazio". Hoje é só "sem correções até agora".
- **Promover em `/metodologia`:** linha na coluna "confiar" de 13.2
  + linha ao final ("metodologia é versionada, mudanças geram entrada
  em `/correcoes`").
- **Badge "corrigido em X"** nas páginas afetadas: banner discreto
  com link pra entrada específica de `/correcoes`. Inverte estigma em
  prova.

**Schema novo:** `analytics.correcoes(id, item_id|cluster_id, data,
delta_antes, delta_depois, descricao, fonte)` — ~10 linhas SQL.

### 13.5 Roadmap viral (refina §6.4 e ganchos §4)

**5 templates ranqueados por viralidade × esforço:**

| # | Template | Onde | Risco |
|---|---|---|---|
| T1 | Spread extremo da semana | `mart_pares` × município porte similar | Baixo |
| T2 | Fornecedor concentrado | `/fornecedor/{cnpj}/por-municipio` ≥10 | Médio |
| T3 | Dispensa repetida | JOIN modalidade+fornecedor+município | Alto |
| T4 | Categoria subindo | série temporal `contract_date` por cluster | Baixo |
| T5 | Contrato mais caro do mês | `MAX(valor_total)` semanal | Muito baixo |

**Cadência:** cron weekly gera 3 candidatos automáticos (T1/T4/T5) →
fila em `analytics.insight_candidato` → publicação em `/destaques/`
(URL nova, badge "gerado automaticamente"). Curados continuam em
`/insight/`.

**Gatilhos de descoberta:** banner "spread mais extremo" em
`/cluster/[id]`; banner "acima/abaixo da mediana em N categorias" em
`/municipio/[cd]`; banner "aparece em N municípios" em
`/fornecedor/[cnpj]`; topo da `/contratos` mostra top 3 por valor.

### 13.6 Família de badges (refina §6.2)

**6 badges com gramática consistente** (ícone + label + tooltip 1 frase):

| Badge | Quando | Cor |
|---|---|---|
| 🟢 Confiança alta | `confianca ≥ 0.85` | verde |
| 🟡 Confiança média | `0.6 ≤ confianca < 0.85` | amarelo |
| 🔴 Sem cluster | `cluster_id IS NULL` ou quarentena | cinza/vermelho claro |
| 🌐 Fonte primária | sempre que tem `source_url` | azul |
| ⏱ Atualizado em X | sempre, em listas/cards | cinza |
| 📐 cluster_version=v1 | toda comparação | neutro |

**Conflito de hierarquia:** se confiança é baixa **E** valor está acima
de p75, confiança vem primeiro (mais à esquerda) — confiança baixa já
é por si só o sinal, não chamar atenção pra valor.

**Implementação:** componente `frontend/components/Badge.tsx` + helper
`lib/badges.ts`. Zero mudança na API (campos já existem em
`item_canonical`).

### 13.7 Próxima manchete: medicamentos por habitante

**Critério vencedor:** alta diferença + categoria reconhecível + dado
robusto + ângulo narrativo claro.

**Plano A — vencedor:** "5 municípios PR que mais gastaram com
medicamentos por habitante em 2025". Cluster maduro, alta cobertura,
denominador IBGE 2022 disponível.

**Exploração realizada (2026-05-09)** confirmou viabilidade com
**2 caveats encontrados na query**:

1. **Trap de consórcios regionais.** FRANCISCO BELTRÃO aparecia em
   primeiro com R$ 12.658/cap — 24× o segundo — porque hospeda o
   CONSUD (Consórcio Intermunicipal de Saúde do Sudoeste). PATO
   BRANCO aparecia em segundo com R$ 518/cap pelo mesmo motivo
   (CONIMS). Filtro `orgao_nome !~* 'cons[óo]rcio|consud|conims'` +
   mesma regex em `descricao` removeu o ruído.
2. **Cobertura de população**: só 35 dos 397 municípios PR têm
   `populacao` em `analytics.municipio_pr` (8.8%). Antes de publicar
   é preciso carregar IBGE 2022 completo para o catálogo.

**Top legítimo após filtros** (preview, sujeito a refino):
ITAIPULÂNDIA (R$ 224/cap, 12k hab) → MAMBORÉ (R$ 152/cap, 14k hab) →
FRANCISCO BELTRÃO (R$ 126/cap, 94k hab — só contratos do município).
Curitiba e Londrina ficam em ~R$ 55/cap (baseline cidades grandes).

**Pivot narrativo descoberto pela query:** "por que cidades pequenas
têm gasto per capita 3-4× maior que grandes em medicamentos?" — ângulo
mais interessante que "ranking absoluto", e tem explicação plausível
(economia de escala em compras grandes vs alta variabilidade em
compras pequenas).

**Plano B — descartado:** "Combustível com âncora ANP" inviável — TCE
não publica volume em litros, só valor por contrato. Sem unidade base,
sem comparação contra preço médio ANP.

**Esqueleto `/insight/medicamentos-por-habitante-pr`:**
1. Manchete + número de impacto
2. Gráfico: dispersão R$/habitante por município (eixo x = porte)
3. Tabela: top 5 acima + top 5 abaixo
4. "Por que isso pode acontecer legitimamente" (vacina)
5. "Por que vale olhar mesmo assim"
6. Como reproduzir: link `/comparar?cluster=medicamentos`
7. Limites do dado (granularidade, modalidade ~65%)
8. Reportar → `/correcoes`

**Teste de robustez (nunca pula):** inverter manchete (somar à mão) ·
sample top-3 e bottom-3 (ler descrição) · validar denominador IBGE ·
2ª opinião via `/ultrareview` · filtro de adjetivo (sem "suspeito",
"irregular", "desviado", "exorbitante").

### 13.8 Comparação por escola — revisitada (refina §6 estado atual)

**Estado:** 506 escolas via regex; cobertura 0,17% geral, 29% em
`obras_edificacao`. Hoje `/escolas` é catálogo de transparência.

**3 abordagens em ordem de honestidade crescente:**

| # | O que faz | Custo | Risco |
|---|---|---|---|
| 1 | Maiores investimentos por escola (descritivo) | ~30 LOC | Muito baixo |
| 2 | Spread interno por escola (min-max-mediana) | ~80 LOC | Baixo |
| 3 | Comparar tipo de intervenção entre escolas | ~200 LOC + cluster v2 | Médio |

**Recomendação:**
- **Implementar Abordagem 1 agora** dentro de `/escolas/[slug]`:
  ordenar contratos por valor desc + stat "investimento total em obras"
  no header. Sem violar framing de catálogo.
- **Manter Abordagem 3 adiada para Fase 1+** com pré-requisitos
  registrados: keyword extraction de tipo de intervenção (~30
  categorias) · validação manual de 100 contratos · threshold mínimo
  de 5 contratos por (tipo × município).
- **Não implementar Abordagem 2** — retorno baixo pra esforço médio
  (aditivos contratuais são ruído normal).

---

## 15. Sistema de manchetes algorítmicas

Sistema novo entregue em 2026-05-09 (não estava na v5 original, surgiu
da discussão crítica do usuário sobre 2.a). **Algorítmico, não
curadoria** — `nenhuma tela tem valores hardcoded; tudo vem do banco`.

### 15.1 Princípios

1. **Algoritmo estúpido de propósito.** Aplica critérios versionados em
   `config/manchete_v1.yaml`. Discordou da seleção? PR no YAML, com
   dados.
2. **Separação rígida de camadas** (3 camadas SQL):
   fatos × seleção × log. Permite re-tunar parâmetros em ~1s sem
   recomputar fatos.
3. **Tudo audit-trail.** Cada manchete carrega hash do YAML que a
   selecionou; cada refresh registra log com snapshot completo.
4. **Vela apagada também é informação.** Manchete que sai com motivo
   diagnóstico aparece na página por 90 dias.
5. **Ninguém escapa por aleatoriedade.** Busca reversa
   (`/manchetes/diagnostico?cd_tce=X`) mostra todas as combinações
   avaliadas com motivo de não-publicação.

### 15.2 Arquitetura — 3 camadas

```
┌─────────────────────────────────────────────────────────────────┐
│ Camada 1: analytics.cluster_discrepancias  (Materialized View)  │
│ FATOS estatísticos por (cluster, município).                    │
│ Refresh: junto com build_marts (semanal cron).                  │
│ Computa: spread, IQR, comparab proxy, spreads por janela        │
│ (90/180/365d) — referência = MAX(contract_date) do snapshot.    │
│ NÃO filtra. Expõe tudo. Custo: alto (re-computa MV).            │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Camada 2: analytics.manchete  (Table)                           │
│ SELEÇÃO após aplicar thresholds do YAML.                        │
│ Refresh: TRUNCATE + INSERT a cada `manchetes refresh`.          │
│ Custo: ~1s. Re-tunável sem recomputar Camada 1.                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Camada 3a: analytics.manchete_publicada  (Append-only log)      │
│ Snapshot de cada manchete publicada com hash do YAML.           │
│ Pergunta: "que manchetes estavam ativas em DD/MM com qual       │
│ config?" Auditoria temporal pública.                            │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Camada 3b: analytics.manchete_saida  (Vela apagada)             │
│ Manchetes que saíram com motivo diagnóstico ("spread caiu para  │
│ 6.6× — limiar 8.0×"). Detectadas no refresh comparando ativos   │
│ antes vs depois.                                                │
└─────────────────────────────────────────────────────────────────┘

Configuração ativa: analytics.manchete_config_aplicada
(snapshot do YAML por hash, usado pelo backend para diagnóstico).
```

### 15.3 Thresholds calibrados (perfil C — v1)

YAML em `config/manchete_v1.yaml`. Calibrados via dry-run em 2026-05-09
contra snapshot 156k contratos PR:

```yaml
cluster_n_min: 1000              # massa mínima do cluster
sujeito_n_min: 30                # contratos do município no cluster
sujeito_valor_total_min: 500000  # R$ no cluster pelo município
spread_min: 5.0                  # mediana_sujeito / mediana_cluster
iqr_sujeito_min: 2.0             # tem dispersão real (p75/p25)
iqr_relativo_max_k: 2.0          # IQR_suj <= 2× IQR_cluster (filtro β)
comparab_min: 0.75               # proxy v1 (HHI mod × HHI forn × spread temp)
estabilidade_min_janelas: 2      # de 3 (90d, 180d, 365d)
estabilidade_min_n_janela: 5     # janela com n < 5 não conta
top_n_publicado: 20
```

Rendimento atual: **5 manchetes ativas** (era 8 antes da estabilidade
temporal). Top 2 com 3/3 janelas (robustas), 3 com 2/3.

### 15.4 Comparabilidade proxy v1 (limites conhecidos)

Média geométrica de 3 sub-scores:
- HHI da modalidade no cluster (alto = homogêneo)
- 1 − HHI do fornecedor no cluster (baixo HHI = mercado competitivo)
- Spread temporal (meses distintos com contratos / 12)

**Saturada no caso TCE-PR:** HHI fornecedor é ~0 em todos os clusters
(milhares de fornecedores), spread temporal é ~1 (espalhamento natural
no ano). Só HHI modalidade discrimina. Threshold 0.75 derruba clusters
com modalidade muito misturada (transporte, obras pavimentação,
materiais hidráulicos); 0.65 = piso permissivo.

Refinar em v1.5: adicionar COV de valor + similaridade textual entre
descrições do cluster. Embeddings (Tier 2) só em v2+.

### 15.5 Endpoints + páginas entregues

**API:**
- `GET /manchetes` — top N ativas
- `GET /manchetes/saidas?dias=N` — vela apagada (últimos N dias)
- `GET /manchetes/diagnostico?cd_tce=X` — busca reversa

**Frontend:**
- `/manchetes` — lista + form de busca reversa + seção recém-saídas
- Home Zona A — manchete rank=1 (sem hardcode)
- `/cluster/[id]` — box "Manchetes deste cluster" (filtra)
- `/municipio/[cd_tce]` — box "Manchetes onde este município aparece"

### 15.6 Hardening de QA entregue junto

- `tests/qa/banco_check.py` — 13 PASS / 0 FAIL contra `/health` e `/stats/pr`
- `tests/qa/schema_snapshot.py` (update/check) — 30 endpoints versionados
  em `tests/qa/snapshots/`. Resolve drift CHECKLIST↔API preventivamente
  (classe inteira F-001/F-004/F-009/F-015 do FINDINGS).
- IBGE Censo 2022 carregado em `municipio_pr` — 35 → 396 catalogados.
  Desbloqueou 80% das cidades para o sistema de manchetes.

### 15.7 Cron e fluxo operacional

`.github/workflows/ingest-weekly.yml` (quartas 06:00 UTC):
1. Aplica migrations (incluindo `005_manchetes.sql`)
2. Ingere TCE-PR (~55s)
3. Ingere Compras.gov.br (best-effort)
4. `python -m analytics.build_marts` (refresh Camada 1 inclusa)
5. **`python -m analytics.manchetes refresh`** (Camadas 2 e 3)
6. Upload R2 + summary

Manual: `python -m uv run python -m analytics.manchetes refresh`
(idempotente, ~1s para re-aplicar YAML).

---

## 16. Próximos passos (pós-v5.1)

Listados em ordem de prioridade. Nenhum bloqueante para o MVP atual.

### 16.1 Curto prazo (técnico, autônomo)

| # | O quê | Tamanho |
|---|---|---|
| 1 | Adaptar `dev_up.{ps1,sh}` para chamar `manchetes refresh` (já está no cron weekly) | trivial |
| 2 | Página `/manchetes/historico?em=YYYY-MM-DD` lendo `manchete_publicada` | médio |
| 3 | Reescrita completa da home (Zonas B/C, não só A) — promover §13.2 confiar/duvidar como Zona B | médio |
| 4 | Schema `analytics.correcoes` + badge "corrigido em X" — aguarda primeiro relato real | médio |

### 16.2 Médio prazo (decisões de produto)

| # | O quê | Decisão pendente |
|---|---|---|
| 5 | **Comparabilidade proxy v1.5** — adicionar COV de valor + similaridade textual (regex categórica) entre objetos do cluster | Investir antes de embeddings ou direto v2? |
| 6 | **Publicar manchete medicamentos por habitante** (§13.7) | Aguarda revisão final do texto editorial |
| 7 | **2.a destaques separados de manchetes** — cron de candidatos T1/T4/T5 em `/destaques/` curado vs algorítmico | Vale a separação ou /manchetes basta? |
| 8 | **Manchetes sobre fornecedor** | Risco jurídico — fora de v1, v1.5, v2. Reabrir só com revisão jurídica |

### 16.3 Longo prazo (Fase 1+)

| # | O quê | Bloqueado por |
|---|---|---|
| 9 | **Embeddings (Tier 2)** — derrota proxy v1 da comparabilidade, melhora cluster | Fase 1+ por design (PLANO §5.3) |
| 10 | **Spider Compras.gov.br real** (federal item-a-item) | API federal estabilizar |
| 11 | **Domínio + Vercel + Supabase + R2 + revisão jurídica** | Usuário humano (PLANO §11) |
| 12 | **Spiders estaduais** (Tá de Pé) | Fase 2 |

### 16.4 Hardening contínuo

| # | O quê | Valor |
|---|---|---|
| 13 | Adicionar `schema_snapshot.py check` ao CI do GitHub Actions | Drift detectado em PR antes do merge |
| 14 | Automatizar §B.5 do CHECKLIST — kill API + headless test de degradação | UI degradação validada |
| 15 | Cobertura de testes unitários para `analytics.manchetes._diagnosticar_motivo` (lógica espelhada API/Python) | Evita drift entre _diag_motivo_falha e _diagnosticar_motivo |

---

## 17. Plano de resposta à análise externa (2026-05-09)

Análise externa do repositório feita por terceiro contra um snapshot
**anterior à v5.1** (1 commit antigo do `main`). Várias críticas já
foram endereçadas pelas sessões A/B/C de hoje (vide §15, §16, §14).

Este §17 documenta o plano de resposta às críticas **ainda válidas**.
Estruturado em 3 waves (higiene → estrutura → qualidade) com itens
auditáveis, estimativas, critérios de aceite e riscos.

### 17.0 Triagem da análise externa

**Já endereçado (reviewer não viu — pre-v5.1):**

| Crítica | Resposta |
|---|---|
| Seed dividido SQL+Python (35 cidades hardcoded) | `scripts/load_ibge_populacao.py` unificou: 35 → 396 (99.7% match) |
| "Top-N dsObjeto fora de cluster" | Sistema `/manchetes` toca o problema por outro ângulo (PLANO §15); pipeline específico de candidatos a YAML novo está em §17.B |
| Audit-trail de comparações | `analytics.manchete_publicada` (Camada 3, §15.2) |
| Drift CHECKLIST↔API | `tests/qa/schema_snapshot.py` (30 endpoints baselined) |
| Hardcode de números no UI | Zona A da home migrada (rank=1 da API); badges família reusada |

**Pontos discordados (com justificativa):**

| Crítica | Discordância |
|---|---|
| "Cobertura de testes é teatro" | Os 28 casos parametrizados de `test_resolution.py` travam bugs reais (S10→10L, gramatura→peso). Frame correto: parser tests sólidos, **faltam integration tests HTTP** — endereço em Wave C. |
| Adotar `openapi-typescript` | Adiciona dep + build step + risco drift no v1 (~30 endpoints, 1 dev). Custo total > benefício. `schema_snapshot.py check` no CI já protege contra drift. Reabrir em v2. |
| "Threshold ≥5 contratos sozinho não é salvaguarda LGPD" | Concordo no isolado, **mas é defesa em camadas**: ≥5 + `noindex,nofollow` + modal "como interpretar" + linguagem factual + `cnpj_mascarado` + `/correcoes`. O que falta mesmo é documentar a postura — Wave A item 6. |

### 17.A Wave A — higiene (3h, 10 itens) — ✅ IMPLEMENTADA 2026-05-09

Corrige 6 dos 10 pontos críticos do reviewer e destrava colaboração
externa. **5 commits** entregues, todos com validação local antes do
push.

| # | O quê | Status | Commit | Notas |
|---|---|---|---|---|
| A.1 | `LICENSE` (AGPL-3.0) no root | ✅ | `4d3298b` | Texto oficial GNU baixado direto |
| A.2 | `frontend/LICENSE` (MIT) | ✅ | `4d3298b` | Espelha multi-licença declarada no PLANO §11.1 |
| A.3 | `CONTRIBUTING.md` | ✅ | `4d3298b` | Setup local + padrão PR + RFC para mudanças sensíveis (manchete YAML, threshold confiança, copy pública) |
| A.4 | `SECURITY.md` | ✅ | `4d3298b` | Escopo, canal `contato@quantopagou.org`, SLA 5d/10d/30d, sem bug bounty financeiro (só crédito) |
| A.5 | `CODE_OF_CONDUCT.md` | ✅ | `4d3298b` | Contributor Covenant 2.1 com canal de enforcement preenchido |
| A.6 | `data/PRIVACY.md` + parágrafo no `/manifesto` | ✅ | `4d3298b` | 6 categorias de dado, 3 bases legais (art.7 II/V/IX), 6 salvaguardas, retenção, art.18, canal takedown. **Marcado como v1 — pendente revisão jurídica antes do go-live público** |
| A.7 | `assert _pool` → `raise RuntimeError` | ✅ | `4b6e11f` | grep limpo: zero `assert` em runtime |
| A.8 | `REFRESH MATERIALIZED VIEW CONCURRENTLY` | ✅ | `4b6e11f` | Validado em build real: 47.85s vs ~50s antes (overhead aceitável). Migrations agora usam `CREATE IF NOT EXISTS`; mudanças de schema futuras exigem migration nova com DROP explícito |
| A.9 | Frontend `cache: "no-store"` → `revalidate: 1800` | ✅ | `fe116be` | `jget` com TTL 30min; novo `jgetLive` para buscas (`/instituicoes/search`, `/contratos/search`, `/manchetes/diagnostico`). TTL < cron weekly = zero risco inconsistência |
| A.10 | `.github/workflows/ci.yml` (PR-time) | ✅ | `d18f2df` | 2 jobs (backend + frontend). Lints continue-on-error temporário (cleanup gradual em §17.B). pytest e tsc estritos. Validado local antes do push: ruff "All checks passed", pytest 28/28 |

**Cleanup adicional aplicado** durante A.10 (parte do refactor):
- `pyproject.toml`: ruff config com `ignore = ["B008"]` (FastAPI Query/Depends idiomático) + `per-file-ignores` em legacy (api/main.py, build_marts, manchetes, tce_pr.py, scripts/, tests/qa/) com cleanup tracked em §17.B
- 15 autofixes mecânicas (imports não usados, formatação) em scripts probe_*, build_marts, banco_check, load_ibge
- `resolution.py`: comentário inline 103 chars → 100 chars sem ignorar regra global

**Wave A fechou** (vs predição original):
- ✅ crítica 1 (LICENSE) — `LICENSE` + `frontend/LICENSE` no repo
- ✅ crítica 2 (CI) — `ci.yml` rodando ruff + pytest + tsc em PR
- ✅ crítica 3 (`assert _pool`) — `raise RuntimeError`
- ✅ crítica 4 (mart REFRESH) — CONCURRENTLY + IF NOT EXISTS
- ✅ crítica 5 (frontend cache) — revalidate 30min + jgetLive
- ✅ crítica 6 (LGPD documentada) — `data/PRIVACY.md` v1 + manifesto
- ✅ crítica 7 (`CONTRIBUTING/SECURITY/CoC`) — 3 docs criadas

**Não fechadas em Wave A** (vão pra B/C):
- crítica "src/api/main.py monolítico" → §17.B.1
- crítica "scripts/probe_* misturados" → §17.B.4
- crítica "rate-limit/CORS" → §17.C.4 (Cloudflare)
- crítica "cobertura keyword 34% sem loop de feedback" → §17.B.2
- crítica "sem testes HTTP/E2E" → §17.C.1, C.2

### 17.B Wave B — estrutura (1 dia, 4 itens) — ⚠️ PARCIALMENTE IMPLEMENTADA 2026-05-09

3 de 4 itens completos. **B.1 dividido em 2 fases** (split bigbang
em refactor seguro com schema_snapshot validando entre passos).

| # | O quê | Status | Commit | Notas |
|---|---|---|---|---|
| B.1 | Quebrar `src/api/main.py` em routers + schemas | ⚠️ **fase 1** | `f6ff003` | **Fase 1**: lifespan + pool + ConnDep + threshold extraídos pra `src/api/deps.py` (-34 linhas). main.py 2177→2143. **Fase 2 pendente**: mover 30 endpoints pra `routers/{meta,catalogo,dados,contrato,fornecedor,municipio,escola,instituicao,tce_pr}.py` + 34 modelos pra `schemas/`. main.py alvo: <200 linhas. Cada router com `schema_snapshot check` entre passos pra evitar regressão. Caught 1 bug real (psycopg removido) — sistema funcionando como projetado |
| B.2 | Pipeline `unmatched_top_dsobjeto.csv` | ✅ | `44f9dfb` | `scripts/unmatched_dsobjeto_top.py` com normalização de 21 prefixos boilerplate iterativa + strip acentos + truncate em 8 palavras. 104k contratos em quarentena → 43k grupos → top 200 vai pra `data/unmatched/top_dsobjeto.csv` (gitignored, gerado). Artifact `unmatched-dsobjeto-{ano}` no `ingest-weekly.yml` com retention 30d. Top resultados misturam candidatos úteis (servicos artistico-culturais) com placeholders genéricos — refinamento iterativo da regex em PRs futuros |
| B.3 | Composite indexes em `raw.compras` | ✅ | `61dc42f` | `sql/006_perf_indexes.sql` com 4 partial indexes (source só tem 2 valores → cardinalidade péssima como primeira coluna B-tree; partial é melhor). EXPLAIN ANALYZE de drill-down típico: **73ms → 6.7ms (~10× speedup)**. Índices: `idx_compras_tce_data`, `idx_compras_tce_cd_tce`, `idx_compras_tce_modalidade`, `idx_item_canon_cluster_all`. Adicionado a dev_up + ingest-weekly |
| B.4 | Mover `scripts/probe_*.py` para `_exploration/` | ✅ | `2c94d64` | 16 probes movidos via `git mv` (preserva histórico). `scripts/` raiz limpo: 14 arquivos de produção. `_exploration/README.md` documenta cada probe + por que existe + quando reabrir |

**Cleanup adicional descoberto durante Wave B:**
- B.4 expôs que `scripts/` agora tem só código de produção — ajuda
  qualquer novo dev a entender o que vale rodar
- B.3 mostrou que o real bottleneck era `raw_payload->>'cd_tce'` sem
  índice (composite com source à frente seria pior, partial é
  cirúrgico)
- B.1 fase 1 capturou 1 bug em runtime (`import psycopg` removido) que
  só apareceu via `schema_snapshot check` — validação salvou commit

**Wave B fechou** (vs predição original):
- ✅ crítica 11 (probe scripts misturados) — `_exploration/` separa
- ✅ crítica "cobertura keyword 34% sem loop de feedback" — pipeline
  unmatched alimenta backlog do YAML
- ✅ crítica de performance — partial indexes 10× speedup
- ⚠️ crítica 2 (catedral main.py) — **parcialmente**, fase 1 feita;
  fase 2 (movimentação completa) pendente em §17.B.1.f2

### 17.B.1.f2 — refactor de routers/schemas (fase 2 de B.1)

Pendente. Plano:

| Router | Endpoints | Modelos a mover |
|---|---|---|
| `routers/meta.py` | /health, /quarentena/resumo, /stats/pr, /manchetes, /manchetes/diagnostico, /manchetes/saidas | HealthOut, QuarentenaResumoOut, StatsPrOut, ManchteOut, ManchteDiagnosticoOut, ManchteSaidaOut, ManchteCandidatoDiagOut, StatsPrModalidadeOut, StatsPrTopClusterOut |
| `routers/catalogo.py` | /clusters | ClusterOut |
| `routers/dados.py` | /pares, /ranking/orgaos, /item/{raw_id} | ParesOut, RankingOrgaoOut, ItemOut, ParesAggOut |
| `routers/contrato.py` | /contrato/{raw_id}, /contratos/search | ContratoOut, ContratoSearchPageOut, ContratoSearchItemOut |
| `routers/instituicao.py` | /instituicoes/search | InstituicoesSearchOut + sub-modelos |
| `routers/escola.py` | /escolas, /escolas/{slug}/contratos | EscolaListItemOut, EscolaContratoOut |
| `routers/municipio.py` | /municipios, /municipio/{key}/info | MunicipioListItemOut, MunicipioInfoOut |
| `routers/fornecedor.py` | /fornecedor/{cnpj}, /fornecedor/{cnpj}/* (5), /fornecedores | FornecedorPerfilOut, FornecedorAgregadoOut, FornecedorContratoOut, FornecedorListItemOut |
| `routers/tce_pr.py` | /tce-pr/dispensas/top-fornecedores, /tce-pr/municipio/* (3), /tce-pr/cluster/* (2) | DispensaTopFornecedorOut, TcePrSummaryOut, ContratoMunicipioOut, RankingMunicipioOut, FornecedorMunicipioOut |

**Critério de aceite:** main.py < 200 linhas; `schema_snapshot check`
verde a cada router migrado; todos os 30 endpoints respondem com
mesmo shape. Próxima sessão.

### 17.C Wave C — qualidade (1 dia, opcional, depende de tempo)

Cobertura de teste real (não só parser) + segurança operacional.

| # | O quê | Onde | Aceite | Tempo |
|---|---|---|---|---|
| C.1 | Testes de contrato HTTP via `fastapi.testclient` | `tests/test_api_contratos.py` (novo) | 5-10 testes cobrindo `/health`, `/manchetes`, `/manchetes/diagnostico`, `/contratos/search`, `/fornecedor/{cnpj}`. Cada teste valida status + shape (keys do response). | 3h |
| C.2 | Smoke E2E frontend via Playwright | `frontend/tests/e2e/` (novo) | 3 specs: `/`, `/manchetes`, `/contratos`. Cada um: status 200, h1 visível, sem `console.error`. Roda em CI. | 3h |
| C.3 | Documentação de teto do free tier | `DEPLOY.md` | Adiciona seção "Quando sai do free": Vercel function-secs (limite mensal), Supabase row reads, R2 egress. Estimativa de quantos hits/mês cada um aguenta. | 1h |
| C.4 | Cloudflare na frente do domínio (rate-limit + CORS allowlist) | `DEPLOY.md` + Cloudflare config (humano) | Documentar setup no `DEPLOY.md`; bloqueia `/manchetes/diagnostico?cd_tce=...` em loop. | 1h |

**Wave C fecha:** crítica 1 (cobertura de testes — frame "integration"), 13 (custos free tier) e parte de "rate-limit/CORS antes do go-live".

### 17.D Itens fora de escopo (deferidos)

| # | O quê | Por quê deferir |
|---|---|---|
| D.1 | `openapi-typescript` para gerar tipos TS | Custo tooling > benefício no v1; reabrir em v2 |
| D.2 | Embeddings (Tier 2) para cluster | Já em PLANO §16.3 / §5.3 — Fase 1+ por design |
| D.3 | pgbouncer transaction-mode + `prepare_threshold=None` | Só relevante se rodarmos atrás de Supabase pooler em Vercel Functions; hoje stack é local. Documentar antes do deploy real. |

### 17.E Riscos do plano

| Risco | Mitigação |
|---|---|
| **Wave B.1 quebra contrato API** ao quebrar main.py em routers | `schema_snapshot.py check` antes/depois. CI obrigatório. Refactor em commits pequenos. |
| **Wave A.9 (revalidate) faz `/manchetes` mostrar dados defasados** | TTL 1800s (30min) é menor que a cadência de refresh (semanal). Manchete só muda no cron weekly. Sem risco de inconsistência. |
| **CI A.10 falha em casos legacy (lint warnings)** | Configurar `ruff` com regras existentes (não bumpar); aceitar mypy strict só em código novo |
| **LGPD A.6 sem revisão jurídica humana** | Documentar o policy é melhor que não documentar. Marcar como "v1 — pendente revisão jurídica antes do go-live público". |
| **Wave C.1 testes HTTP exigem Postgres no CI** | Usar `services: postgres` em GH Actions; aplicar migrations no setup |

### 17.F Sequência recomendada

**Próxima sessão:**
1. Wave A inteira (3h) — alta alavancagem, fecha 6 críticas + destrava colaboração
2. Confirma com você antes de seguir

**Sessão seguinte (se Wave A ok):**
3. Wave B.1 (refactor main.py) — maior risco, fazer com calma
4. Wave B.2 (pipeline dsobjeto) — alimenta backlog de YAML
5. Wave B.3-4 (perf + cleanup)

**Sessão 3 (opcional):**
6. Wave C completa — quality gates pré-go-live

---

## 18. Wave LGPD — pacote jurídico-administrativo (pré-go-live)

Bloco **bloqueante para domínio público**, derivado de análise jurídica
externa de 2026-05-09. Cobre lacunas LGPD que Wave A endereçou apenas
parcialmente (`data/PRIVACY.md` v1 cobre conceitualmente; falta
arquitetura de eliminação, distinção PJ vs MEI, LIA/RIPD formais,
canal de direitos, encarregado).

**Estimativa total:** 2-4 semanas (técnica + jurídica + UI).

### 18.0 Por que vai entre Wave B e Wave C

Reviewer jurídico marcou como **CRÍTICO** os itens 1.1, 1.2, 1.3, 1.6
(arquitetura de eliminação) — bloqueantes para go-live público. Wave C
(qualidade) é hardening operacional importante mas não bloqueante. A
sequência correta:

1. ~~Wave A — higiene~~ ✅ (commits `4b6e11f`-`d18f2df`)
2. ~~Wave B — estrutura~~ ⚠️ parcial (B.1 fase 2 pendente)
3. **Wave LGPD aqui** ← bloqueante para go-live
4. Wave C — qualidade
5. Go-live público

### 18.A Wave LGPD — 15 itens

Cada item com prioridade, aceite e estimativa. Itens marcados
**CRÍTICA** são bloqueantes; **ALTA** ficam ok pra ser entregues em
paralelo com revisão jurídica humana.

| # | Item | Prioridade | Aceite | Tempo |
|---|---|---|---|---|
| **L.1** ✅ | `analytics.eliminacao` + tombstones + filtro MVs + CLI `eliminar.py` + endpoint `/contrato` 410 Gone | **CRÍTICA** | Solicitação de eliminação atendida em ≤15d via art. 18 IV LGPD; raw permanece em `raw.snapshots` com hash; conteúdo desaparece da vitrine; `/eliminacoes/publicas` lista IDs eliminados sem reproduzir conteúdo | 1d — implementado em `af20e47` (`sql/007_eliminacao.sql` + `scripts/eliminar.py`) |
| **L.2** ✅⚠️ | `analytics.fornecedor(cnpj, tipo_juridico, fonte)` + classificador `fn_classificar_tipo_juridico` (heurística por sufixo: LTDA, S.A., EIRELI, COOPERATIVA, etc) + default deny em `/fornecedor/{cnpj}` | **CRÍTICA** | Endpoint retorna 404 quando `tipo_juridico != 'PJ'` (inclui NULL = não classificado). Primeira carga: 22.4k PJ confirmado / 16.3k mascarado (42%). Dump RFB sobrescreverá heurística no futuro (fonte versionada). **L.2.b deferido:** MV `mart_fornecedores_municipio` filtrar PJ + frontend `/fornecedor/[cnpj]` 404 elegante + mascarar `/fornecedores` listagem. | 2d — implementado parcial em `sql/009_fornecedor.sql` + `src/api/main.py` |
| **L.3** | LIA estruturada (Guia ANPD "Legítimo Interesse") em `docs/legal/LIA.md` | **CRÍTICA** | Cobre: identificação do tratamento, finalidade legítima, necessidade, balanceamento (interesse vs direitos do titular), salvaguardas implementadas | 1d (humano jurídico) |
| **L.4** | RIPD em `docs/legal/RIPD.md` (Resolução CD/ANPD nº 4/2023) | **CRÍTICA** | Cobre: descrição, finalidade, legitimação, ciclo de vida, riscos, medidas mitigadoras | 1d (humano jurídico) |
| **L.5** | Política de Privacidade em rota `/politica-privacidade` + footer global | Alta | Rota pública renderiza política completa (art. 9º LGPD); link no footer de toda página; refletir `data/PRIVACY.md` v2 | 4h |
| **L.6** | Termos de Uso em `/termos` + licença de dados (CC-BY 4.0 ou ODbL) | Alta | Rota pública; cobre: uso pessoal/comercial, atribuição, garantias, limitação de responsabilidade, foro | 4h |
| **L.7** | Encarregado nomeado + canal `/lgpd` + e-mail dedicado (ou autodeclaração de pequeno porte) | Alta | Rodapé global cita encarregado; rota `/lgpd` documenta direitos do art. 18 + canal; ticket ID + SLA 15d | 4h |
| **L.8** | Catálogo de subprocessadores em `docs/legal/SUBPROCESSADORES.md` | Alta | Lista: Vercel, Supabase, Cloudflare R2, Fly.io, Resend (futuro). Cada um com: razão social, finalidade, jurisdição, base legal de transferência internacional (Resolução CD/ANPD 19/2024) | 2h |
| **L.9** ✅⚠️ | Política de retenção em `docs/legal/RETENCAO.md` + job de expurgo do `raw_payload` redundante | Média | Documento define prazos por tipo (raw, canonical, mart, log); job mensal reduz `raw_payload` mantendo só campos não derivados nas colunas dedicadas. **L.9.b deferido:** `scripts/expurgar_raw_payload.py` com dry-run. **L.9.c deferido:** cron mensal após ≥1 ciclo validado. | 1d — documento implementado em `docs/legal/RETENCAO.md` |
| **L.10** ✅ | `analytics.audit_log` (registro de operações art. 37 LGPD) via triggers | Média | Tabela append-only com schema/table/op/pk_text/raw_id_afetado/ator/base_legal/diff. Triggers em `analytics.eliminacao`, `item_canonical` (só quando `eliminada_em` muda) e `fornecedor`. Ator via `current_setting('app.audit_actor')` setado pelo psycopg, com fallback pra linha de `eliminacao`. Escopo cirúrgico: NÃO loga refresh de MV. | 1d — implementado em `sql/008_audit_log.sql` + `scripts/eliminar.py` |
| **L.11** | Disclaimer de origem em `/comparar`, `/manchetes`, `/fornecedor/*`, `/municipio/*`, `/cluster/*` | Média | Banner discreto: "Dado extraído de TCE-PR/Compras.gov.br em DD/MM. Possíveis erros — [reportar correção]". Componente reusável `<DisclaimerOrigem>` | 2h |
| **L.12** | `/correcoes` formal: ticket ID + fluxo auditável + SLA 15d | Média | Form gera ticket no banco (`analytics.correcao_ticket`); usuário recebe link público pra acompanhar; SLA 15d (LGPD) ou 48h (correção factual) com badge de prazo | 1d |
| **L.13** | Direito à revisão de ranking (art. 20 §1º): botão "contestar este ranking" em `/manchetes`, `/ranking/*` | Baixa | Form `/contestar?manchete_id=X` registra pedido de revisão; resposta humana documentada em `/correcoes` | 4h |
| **L.14** | Buscar instituição-âncora (Open Knowledge BR / Transparência BR / Abraji) | **CRÍTICA não-técnica** | E-mail enviado a ≥2 instituições propondo parceria/co-mantenança; resposta documentada em `docs/PARCERIAS.md` | externo |
| **L.15** | Submeter pacote (L.1-L.13) a revisor jurídico independente especializado em LGPD/cívico | **CRÍTICA não-técnica** | Parecer recebido + ajustes incorporados; documentado em `docs/legal/REVISAO_JURIDICA_v1.md` | externo |

### 18.B Sequência recomendada

| Fase | Itens | Atores | Tempo |
|---|---|---|---|
| Técnica imediata | ~~L.1 (tombstones)~~ ✅ | dev | 1d |
| Técnica próxima | ~~L.2 (PJ vs MEI/EI v1)~~ ✅⚠️, ~~L.10 (audit_log)~~ ✅, ~~L.9.a (doc retenção)~~ ✅ | dev | 3d |
| Técnica próxima — ajustes | L.2.b (MV/frontend), L.9.b (CLI expurgo), L.9.c (cron) | dev | 1d |
| UI | L.5, L.6, L.7, L.11, L.12, L.13 | dev | 3d |
| Jurídica | L.3 (LIA), L.4 (RIPD), L.8 (subprocessadores) | jurídico humano | 5d |
| Externa | L.14 (instituição), L.15 (revisor jurídico) | autor | 1-2 sem |

### 18.C Pontos discordados da análise externa

Discordâncias documentadas com fundamento, sem ignorar a crítica:

| Crítica | Discordância |
|---|---|
| "ALTA — NÃO RECOMENDADO PARA PRODUÇÃO" | Projeto **não está em produção**. Sem domínio público, sem indexação, sem usuário externo. Risco atual = 0. Frase corretamente lida: "não recomendado para virar produção sem cumprir Wave LGPD". |
| "Threshold ≥5 contratos é heurística sem fundamento" | Concordo no isolado, mas é camada de defesa em camadas. Item L.2 fecha a defesa (tipo_juridico). |
| "Imutabilidade conflita com direito de eliminação" | Imutabilidade do **snapshot raw** é defensável (auditoria contra falsificação); imutabilidade do **publicado** não é. L.1 resolve com tombstones. |
| "Cobertura de testes é teatro" | Mantenho discordância parcial: 28 casos de parser travam bugs reais. Faltam testes de integração HTTP — em §17.C.1 (Wave C). |
| "Adotar openapi-typescript" | Reabrir em v2; v1 com `schema_snapshot.py check` no CI já protege contra drift. |

---

## 18. Wave LGPD — bloqueante para go-live público (2026-05-09)

Resposta a parecer técnico-jurídico independente recebido em 2026-05-09
(`ANALISE_JURIDICA_QUANTO_PAGOU.md` + `PARECER_QUANTO_PAGOU.md`). O
parecer triou 25+ achados em CRÍTICA / ALTA / MÉDIA / BAIXA.

**Triagem rápida (8 dos achados já fechados pela Wave A):**

| Achado | Status |
|---|---|
| 2.4 `assert _pool` runtime | ✅ Wave A.7 (`4b6e11f`) |
| 2.2 sem `SECURITY.md` | ✅ Wave A.4 (`4d3298b`) |
| 6.1 sem `LICENSE` | ✅ Wave A.1+A.2 (`4d3298b`) |
| 6.2 sem `CONTRIBUTING`/`CoC` | ✅ Wave A.3+A.5 (`4d3298b`) |
| 4.1 CI sem pytest/ruff | ✅ Wave A.10 (`d18f2df`) |
| 1.5 retenção documentada | ⚠️ parcial — `data/PRIVACY.md` cobre conceitualmente; falta job de expurgo (vira L.9) |
| 3.1 sem documentação LGPD | ⚠️ parcial — arquivo existe; falta rota pública (L.5) |
| 3.4 logs aplicação | ⚠️ parcial — depende de hosting |

**Discordâncias documentadas** (com justificativa em resposta no PR):

- "Não recomendado para produção" — projeto **não está em produção**;
  zero exposição atual. O parecer está certo no diagnóstico do que
  falta antes do go-live, errado na iminência de risco.
- "Threshold ≥5 contratos é heurística sem fundamento" — concordo no
  isolado, mas é defesa em camadas. Concedido: precisa item L.2
  (distinção PJ vs MEI/EI) pra fechar a defesa.
- "Cobertura de testes é teatro" — overstated, conforme já argumentado
  em PLANO §17.0.

### 18.1 Itens da Wave LGPD (15 itens, ~2-4 semanas)

Bloqueante para virar domínio público + indexação Google. Ordem por
gravidade jurídica + dependência técnica.

| # | Item | Categoria | Tamanho |
|---|---|---|---|
| **L.1** ✅ | `analytics.eliminacao` (tombstones) + filtro 5 MVs + ALTER `item_canonical` + script CLI + endpoint `/eliminacoes/publicas` + `/contrato/{id}` retorna 410 Gone se eliminado | Tech crítico | 1d — `af20e47` |
| **L.2** ✅⚠️ | `analytics.fornecedor(cnpj, tipo_juridico, fonte)` + classificador heurístico por sufixo (v1: LTDA, S.A., EIRELI, COOPERATIVA, etc) + default deny em `/fornecedor/{cnpj}`. **Deferido (L.2.b):** MV `mart_fornecedores_municipio` filtrar PJ, frontend lidar 404, mascarar `/fornecedores` listagem. Dump RFB substitui heurística depois (fonte versionada). | Tech crítico | 2d (parcial) — `sql/009_fornecedor.sql` |
| **L.3** | LIA estruturada (Guia ANPD "Legítimo Interesse") em `docs/legal/LIA.md` — finalidade, necessidade, proporcionalidade, salvaguardas | Documental crítico | 1d |
| **L.4** | RIPD/DPIA em `docs/legal/RIPD.md` (Resolução CD/ANPD 4/2023) — contexto, descrição, identificação de riscos, medidas de mitigação | Documental crítico | 1d |
| **L.5** | Política de Privacidade em rota `/politica-privacidade` (espelha `data/PRIVACY.md` mas como página web). Link no footer global | UI documental | 4h |
| **L.6** | Termos de Uso em `/termos` + licença de dados (`LICENSE-DATA` raiz, sugestão CC-BY 4.0). Link no footer | UI documental | 4h |
| **L.7** | Encarregado nomeado (DPO ou autodeclaração de pequeno porte conforme Resolução CD/ANPD 2/2022) + canal `/lgpd` + e-mail dedicado | Documental | 4h |
| **L.8** | Catálogo de subprocessadores em `docs/legal/SUBPROCESSADORES.md` (Supabase + Vercel + R2) com DPA referenciado | Documental | 2h |
| **L.9** ✅⚠️ | Política de retenção em `docs/legal/RETENCAO.md` (entregue) + job de expurgo do `raw_payload` após N dias (verificação de qualidade do parse). **Deferido (L.9.b):** `scripts/expurgar_raw_payload.py` com dry-run. **L.9.c:** cron mensal após ≥1 ciclo validado. | Tech | 1d (doc) — `docs/legal/RETENCAO.md` |
| **L.10** ✅ | `analytics.audit_log` (registro de operações, art. 37) com triggers PostgreSQL — tabela append-only + função genérica + triggers cirúrgicos em `eliminacao`, `item_canonical`, `fornecedor`. Ator via `current_setting('app.audit_actor')`. NÃO loga refresh de MV (volume sem ganho probatório). | Tech | 1d — `sql/008_audit_log.sql` |
| **L.11** | Disclaimer de origem visível em `/comparar`, `/manchetes`, `/fornecedor/*` ("Dados extraídos de [fonte] em [data]. Possíveis erros — reportar em /correcoes") | UI cosmético | 2h |
| **L.12** | `/correcoes` formal: ticket ID, SLA 15d, fluxo auditável (vai além do `mailto:` atual) | Tech | 1d |
| **L.13** | Direito à revisão de ranking (art. 20 §1º): botão "contestar este ranking" em `/manchetes` e `/ranking/orgaos` | UI funcional | 4h |
| **L.14** | Buscar instituição-âncora (Open Knowledge BR / Transparência BR / observatório universitário) | Externo | n/a |
| **L.15** | Submeter pacote a revisor jurídico independente real (advogado especializado em LGPD aplicada a iniciativas cívicas) | Externo | n/a |

### 18.2 Sequência recomendada

**Sessão 2026-05-09:**
- §18 documentado + L.1 (tombstones) implementado em `af20e47`

**Sessão 2026-05-11 (esta sessão):**
- ✅ L.10 (audit_log) — `sql/008_audit_log.sql`, testado end-to-end
- ✅⚠️ L.2 (PJ vs MEI/EI v1 heurístico) — `sql/009_fornecedor.sql`, 22.4k PJ / 16.3k mascarado; L.2.b deferido
- ✅⚠️ L.9.a (doc retenção) — `docs/legal/RETENCAO.md`; L.9.b/c deferidos

**Próxima sessão técnica:**
- L.2.b — refactor MV `mart_fornecedores_municipio` (filtrar PJ), frontend `/fornecedor/[cnpj]` 404 elegante, mascarar `/fornecedores` listagem
- L.9.b — `scripts/expurgar_raw_payload.py` com dry-run
- (eventual) Ingestão dump RFB substituindo heurística sufixo_v1

**Sessão jurídica/documental (paralela, humano não-dev):**
- L.3 LIA, L.4 RIPD, L.5 Política, L.6 Termos, L.7 DPO, L.8 Subprocessadores
- Ideal: contratar revisor jurídico real (L.15) para validar o pacote

**Sessão UI (após L.5/L.6/L.7 prontos):**
- L.11 disclaimers, L.12 `/correcoes` formal, L.13 contestar ranking

**Externos (em paralelo):**
- L.14 contatar Open Knowledge BR / Transparência BR
- L.15 contatar advogado LGPD

**Wave C (qualidade) entra DEPOIS de L.2.b** — testes HTTP
ajudam validar mascaramento PJ/MEI sem regressão.

### 18.3 Criterio de "pronto para go-live público"

Não vamos abrir indexação Google enquanto:

- ✅ L.1 (tombstones) implementado
- ✅⚠️ L.2 implementado (v1 heurístico); falta L.2.b (MV + frontend + listagem)
- ✅ L.10 (audit_log) implementado
- ✅⚠️ L.9 doc implementado; falta L.9.b (CLI expurgo)
- ❌ L.3, L.4, L.5, L.6, L.7 não estiverem prontos
- ❌ L.15 (revisor jurídico) não tiver visto o pacote
- ❌ A Wave C.4 (Cloudflare na frente, rate-limit, CORS) não estiver
  configurada

São condições mínimas, não suficientes. Ideal: também L.8, L.11, L.12
+ L.14 (instituição-âncora confirmada).

---

## 14. Changelog

**v5.5 (2026-05-11)** — Wave LGPD avança: L.10 + L.2 (v1) + L.9 (doc):
- **L.10 ✅** `sql/008_audit_log.sql` — `analytics.audit_log` append-only + função trigger genérica + triggers cirúrgicos em `eliminacao`, `item_canonical` (só `eliminada_em`) e `fornecedor`. Ator via `current_setting('app.audit_actor')` (SET LOCAL no psycopg) com fallback pra coluna `ator` de `eliminacao`. Testado end-to-end: INSERT em eliminacao gera 2 audit_log rows (eliminacao + cascata).
- **L.2 ✅⚠️** `sql/009_fornecedor.sql` — `analytics.fornecedor(cnpj, tipo_juridico, fonte)` + `fn_classificar_tipo_juridico` heurística por sufixo (LTDA, S.A., S/A, EIRELI, SOCIEDADE ANÔNIMA, COOPERATIVA, ASSOCIAÇÃO, FUNDAÇÃO, INSTITUTO, FEDERAÇÃO, SINDICATO, IGREJA, HOSPITAL, UNIVERSIDADE, MUNICÍPIO, PREFEITURA, UNIÃO, ESTADO). ME/EPP isolados NÃO marcam PJ (ambíguos com MEI). Primeira carga: 38.686 fornecedores → 22.409 PJ (58%) + 16.277 NULL (42%, mascarado). Endpoint `/fornecedor/{cnpj}` retorna 404 quando `tipo_juridico != 'PJ'`. Fonte versionada permite dump RFB sobrescrever depois. **L.2.b deferido**: MV `mart_fornecedores_municipio` filtrar PJ + frontend 404 elegante + listagem `/fornecedores` mascarada.
- **L.9.a ✅** `docs/legal/RETENCAO.md` v1 — política completa por camada (raw, canonical, mart, log, MVs, manchetes, logs aplicação) + plano L.9.b/c deferidos (CLI antes de cron).
- **§18.2 sequência atualizada** — sessão 2026-05-11 fechada; L.2.b + L.9.b + ingestão RFB na próxima.

**v5.4 (2026-05-09)** — Wave LGPD documentada (PLANO §18) + L.1 tombstones implementados:
- **§18 novo** — 15 itens da Wave LGPD com prioridade, aceite, tempo. Bloqueante para go-live público. Sequência: A→B→**LGPD**→C
- **§18.A tabela** mapeia: 4 críticas (L.1 L.2 L.14 L.15), 4 altas (L.5-L.8), 5 médias (L.9-L.13), 0 baixas
- **§18.B** sequência por ator (dev, jurídico humano, autor) com janelas de tempo
- **§18.C** documenta 5 discordâncias com fundamento (frase "produção" calibrada, threshold como camada de defesa, imutabilidade nuançada, testes de parser legítimos, openapi-typescript adiado)
- **L.1 implementado** (próximo commit) — `analytics.eliminacao` + ALTER `item_canonical` + DROP+CREATE 5 MVs com filtro + `scripts/eliminar.py` CLI + endpoint `/eliminacoes/publicas` + `/contrato/{raw_id}` retorna 410 Gone

**v5.3 (2026-05-09)** — Wave B (estrutura) parcialmente implementada (PLANO §17.B):
- **B.4 ✅** (`2c94d64`): 16 `scripts/probe_*.py` movidos para `scripts/_exploration/` via `git mv` (preserva histórico). README do `_exploration/` documenta cada probe + audit trail das decisões (PNCP descartado, etc)
- **B.3 ✅** (`61dc42f`): `sql/006_perf_indexes.sql` com 4 partial indexes em `raw.compras` + `item_canonical`. **EXPLAIN ANALYZE: 73ms → 6.7ms (~10× speedup)** em drill-down típico
- **B.2 ✅** (`44f9dfb`): `scripts/unmatched_dsobjeto_top.py` com normalização robusta (21 prefixos boilerplate iterativa + strip acentos + truncate). 104k em quarentena → top 200 alimenta backlog do YAML. Artifact no cron weekly retention 30d
- **B.1 ⚠️ fase 1** (`f6ff003`): `lifespan/pool/ConnDep/threshold` extraídos para `src/api/deps.py`. main.py: 2177 → 2143 linhas. Fase 2 (mover 30 endpoints + 34 modelos) documentada em §17.B.1.f2 com plano por router. Validado por schema_snapshot check (capturou 1 bug real durante refactor — sistema funcionando)

**v5.2 (2026-05-09)** — Wave A do plano de resposta à análise externa (PLANO §17.A):
- **Backend fixes** (`4b6e11f`): `assert _pool` → `raise RuntimeError` (python -O bug); `REFRESH MATERIALIZED VIEW CONCURRENTLY` em todas as 5 MVs (validado: 47.85s); migrations idempotentes com `CREATE IF NOT EXISTS`
- **Frontend cache** (`fe116be`): `jget` agora usa `revalidate: 1800` (30min) por padrão; novo `jgetLive` para buscas interativas. Reduz custo Vercel/Supabase em produção
- **Governance** (`4d3298b`): `LICENSE` (AGPL-3.0) + `frontend/LICENSE` (MIT) + `CONTRIBUTING.md` (setup, padrão PR, RFC para mudanças sensíveis) + `SECURITY.md` (escopo, canal, SLA) + `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1) + `data/PRIVACY.md` (LGPD v1, 6 categorias, 3 bases legais, 6 salvaguardas) + parágrafo no `/manifesto`
- **CI** (`d18f2df`): `.github/workflows/ci.yml` com 2 jobs (backend ruff/mypy/pytest + frontend lint/tsc); ruff config com `ignore = ["B008"]` (FastAPI idiom) e `per-file-ignores` em arquivos legacy
- **PLANO §17** (`810c2c8`): plano de resposta à análise externa documentado com triagem (já feito vs discordado vs pendente) + 3 waves (A higiene 3h / B estrutura 1d / C qualidade 1d) + riscos + sequência

**v5.1 (2026-05-09)** — implementação completa da v5 + sistema de manchetes algorítmicas:
- **Topo do PLANO** — atualizado com tabela de status (✅/⚠️) das 8 propostas v5
- **Nova §15** — sistema de manchetes algorítmicas (3 camadas SQL + YAML versionado + estabilidade temporal + vela apagada + busca reversa). Substitui parcialmente §13.5 (2.a viral)
- **Nova §16** — próximos passos pós-v5.1 organizados em 4 grupos
- **Backend novo:** `sql/005_manchetes.sql` (3 tabelas + MV + manchete_saida + manchete_config_aplicada), `src/analytics/manchetes.py` (refresh + diagnóstico), `config/manchete_v1.yaml` (perfil C calibrado: 5 manchetes ativas)
- **API nova:** `/manchetes`, `/manchetes/saidas`, `/manchetes/diagnostico`
- **Frontend novo:** `/manchetes` (lista + busca reversa + recém-saídas), `lib/ManchteContext.tsx` (manchetes contextuais em `/cluster` e `/municipio`), Zona A da home migrada (sem hardcode), `lib/Badge.tsx` (família de 6 badges)
- **Hardening:** `tests/qa/banco_check.py` (13 PASS), `tests/qa/schema_snapshot.py` (30 endpoints versionados em `tests/qa/snapshots/`), `scripts/load_ibge_populacao.py` (35 → 396 municípios catalogados)
- **Integração:** GitHub Actions `ingest-weekly.yml` ganhou step de manchetes refresh; `dev_up.{ps1,sh}` aplica nova migration
- **Findings de QA resolvidos:** F-001/F-002/F-004/F-009/F-012/F-015 (drift schema — CHECKLIST atualizado), F-010/F-013/F-014/F-016/F-017 (frontend), F-003/F-006/F-007/F-008 (backend tipagem + mensagens), F-011 (copy /comparar)

**v5 (2026-05-09)** — sessão de planejamento focada em narrativa e roadmap editorial:
- **Nova §13** — propostas v5 detalhadas (8 itens divididos entre frente narrativa e frente roadmap)
- **§13.1 Modal "Como interpretar"** — refina §6.3 com 4 quadros pedagógicos
- **§13.2 "Por que confiar / Por que duvidar"** — vacina anti-objeção em colunas simétricas
- **§13.3 Reescrita da home** — manchete acima do fold, evidência como segunda zona, navegue terceira
- **§13.4 `/correcoes` como vitrine** — schema `analytics.correcoes` + reformulação textual + badge "corrigido em X" nas páginas afetadas
- **§13.5 Roadmap viral** — 5 templates (T1-T5) + cron weekly de candidatos automáticos em `/destaques/` + gatilhos de descoberta espalhados
- **§13.6 Família de 6 badges** — confiança alta/média/sem cluster + fonte primária + atualizado + cluster_version
- **§13.7 Próxima manchete** — plano A (medicamentos por habitante) confirmado; plano B (combustível com âncora ANP) descartado por inviabilidade de unidade no TCE
- **§13.8 Comparação por escola revisitada** — Abordagem 1 (transparência por escola) implementar; Abordagem 3 (tipo de intervenção) adiada com pré-requisitos
- **5 decisões pendentes do usuário** listadas no topo

**v4 (2026-05-02)** — terceira revisão crítica + pivô para execução:
- **Princípio "progressive correctness"** adicionado (seção 1) — Tier 2-4, drift automático e cluster sofisticado deferidos para Fase 2+
- **5.3:** golden set agora em dois níveis (core fixo + extended rotativo); drift manual em Fase 0-1
- **5.6:** quarentena visível com label "não comparável ainda" + microtask de contribuição
- **6.1:** botão "Explicar como leigo" + alertas de delta (+40% em 6m) + comparações emocionais opcionais
- **6.3:** versão visual da metodologia (diagramas) prevista
- **6.4:** desacoplamento de cadência — esteira automática (semanal) vs editorial (irregular); parcerias estruturadas listadas
- **6.5:** guardrails reforçados — threshold ≥ 5 contratos, delay 30 dias, sem ranking implícito
- **Fase 1:** Tier 2 só para top 5 categorias; cluster versioning ativo mas drift manual; defere sofisticação
- **Riscos:** over-engineering, quarentena invisível, bottleneck editorial
- **Seção 12 reescrita como sprint executável de 7 dias** — separando o que Claude pode fazer local do que requer ação do usuário

**v3 (2026-05-02)** — segunda revisão crítica:
- **5.3:** cluster versioning (frozen) + golden set + drift monitoring (sem isso, comparação histórica é falsa)
- **Nova 5.6:** camada de normalização de unidade (sem isso, todas as comparações são ruído)
- **5.4:** UI agora separa cidadão (componentes, sem agregado) de pesquisador (com agregado); "Risco" → "Sinais de atenção"
- **6.1:** card com toggle de pares + sparkline histórico + intervalo de confiança visível
- **Nova 6.4:** estratégia de aquisição + loop de crescimento explícito
- **Nova 6.5:** página de fornecedor com guardrails legais (modal, noindex, linguagem factual)
- **Nova 6.6:** página de correções públicas (vantagem competitiva)
- **Fase 0.5 reformulada:** lançamento editorial com 1 história + 1 ranking + 1 insight reais
- **Schema:** `cluster_version`, `unidade_base`, `valor_unitario_normalizado`, `em_quarentena`
- **Decisões da seção 11 confirmadas e travadas**
- **Riscos:** adicionados drift, normalização de unidade, interpretação do score, difamação por fornecedor

**v2 (2026-05-02)** — primeira revisão crítica:
- Tese reformulada (produto de comunicação, não infra)
- Camada de resolução de itens em 4 tiers
- Risk score composto substitui >3σ
- Camada de durabilidade
- Fase 0.5 nova
- Fase 3 escopo reduzido
- Licença em 3 camadas

**v1 (2026-05-02)** — rascunho inicial.
