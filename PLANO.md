# Plano de Desenvolvimento — Quanto Pagou

> Plataforma cívica para monitorar gastos públicos brasileiros e identificar possíveis desvios.

**Versão:** v5.1 (2026-05-09)
**Status:** v5 implementado. Sistema de manchetes algorítmicas no ar.
Próximas frentes em §16.

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

## 14. Changelog

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
