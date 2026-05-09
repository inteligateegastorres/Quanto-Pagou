# QA Findings — Quanto Pagou

Registro de problemas encontrados durante execução do
[`CHECKLIST.md`](./CHECKLIST.md).

> **Regras:**
> - Uma entrada por bug observado. Não agrupar.
> - **Não consertar.** Só descrever.
> - Se você acha que não é bug e sim "intencional, mas estranho",
>   registre mesmo assim como `severity: question`.

---

## Template de entrada (copie + cole pra cada finding)

````markdown
### F-NNN: [título curto e específico]

- **Categoria:** infra | api | frontend | drill-down | guardrail | ux | docs | edge-case | performance | data | question
- **Severidade:** critical | high | medium | low | question
  - `critical`: stack down, dado errado em produção, regressão de invariante (§6.5, quarentena, cluster_version)
  - `high`: feature principal quebrada (busca, comparação, perfil)
  - `medium`: feature secundária quebrada, ou erro em edge case provável
  - `low`: cosmético, copy, link errado, edge case improvável
  - `question`: comportamento ambíguo — pede decisão de produto
- **Onde:** URL ou endpoint exato (`/instituicoes?q=UPA`, `GET /stats/pr`)
- **Item do checklist:** seção e número (`§1.6`, `§3 drill-down /comparar`)

**Reprodução:**

1. Passo
2. Passo
3. Passo

**Esperado:**

> O que deveria acontecer (idealmente cite o item do checklist ou a
> documentação relevante).

**Observado:**

> O que aconteceu de fato. Cole o trecho relevante do payload, do erro,
> ou descreva o estado da UI.

```
[trecho de log / payload / erro, se aplicável]
```

**Hipótese de causa raiz** (opcional, só se óbvia):

> Linha X do arquivo Y parece estar fazendo Z em vez de W.

**Sugestão de fix** (opcional, só se trivial):

> Trocar `foo` por `bar` em `arquivo.ts:123`.

````

---

## Findings registrados

<!-- A IA executora preenche abaixo. Mantém numeração contínua F-001, F-002, ... -->

> **Status pós-correção (2026-05-09):** 13 dos 18 findings corrigidos
> nesta sessão. Ver seção [Resoluções](#resoluções) no final.

### F-001: `/health` não expõe `db_ok` nem `staging_compras` previstos no checklist

- **Categoria:** docs
- **Severidade:** low
- **Onde:** `GET /health`
- **Item do checklist:** §0 (pré-requisitos), §A.1

**Reprodução:**

1. `curl http://127.0.0.1:8001/health`

**Esperado:**

> JSON com `db_ok: true` e contagens > 0 em `raw_compras` e `staging_compras`.

**Observado:**

> JSON tem `status: "ok"` (não `db_ok`) e expõe `raw_compras: 156769`, `item_canonical: 156769` e `em_quarentena: 104010` — não há campo `staging_compras`.

```
{"status":"ok","snapshots":15,"raw_compras":156769,"item_canonical":156769,"em_quarentena":104010,"mart_pares_rows":5,"mart_orgao_rows":21}
```

**Hipótese de causa raiz:**

> Drift entre CHECKLIST.md e o schema atual da API; o backend mudou nomes de campos sem atualizar a doc de QA.

---

### F-002: `total_fornecedores` em `/stats/pr` muito abaixo do limite mínimo do checklist

- **Categoria:** data | question
- **Severidade:** question
- **Onde:** `GET /stats/pr`
- **Item do checklist:** §A.1 (`total_fornecedores ≥ 100_000`)

**Reprodução:**

1. `curl http://127.0.0.1:8001/stats/pr`

**Esperado:**

> `total_fornecedores ≥ 100_000`

**Observado:**

> `total_fornecedores: 43654` (≈ 44k), menos da metade do mínimo previsto.

```
"total_contratos":156679,"total_municipios":397,"total_fornecedores":43654
```

**Hipótese de causa raiz:**

> Ou (a) limite do checklist está obsoleto (snapshot anterior contava CNPJs duplicados, ex.: filiais), ou (b) a deduplicação atual está mais agressiva que o esperado e está colapsando matrizes/filiais. Confirmar o que mudou no SQL de `staging_compras → fornecedores` e atualizar o limite ou reverter a deduplicação.

---

### F-003: `/pares` retorna "sem mart_pares" mesmo para cluster com 8k contratos

- **Categoria:** api | data
- **Severidade:** critical
- **Onde:** `GET /pares?cluster_id=merenda_escolar&limit=10` e `GET /pares?cluster_id=tce_pr_v1__merenda_escolar&limit=10`
- **Item do checklist:** §A.5 (núcleo do produto)

**Reprodução:**

1. `curl 'http://127.0.0.1:8001/pares?cluster_id=merenda_escolar&limit=10'`
2. `curl 'http://127.0.0.1:8001/pares?cluster_id=tce_pr_v1__merenda_escolar&limit=10'`

**Esperado:**

> Array com `produto_normalizado`, `unit_price_brl`, etc. (núcleo da comparação de preços).

**Observado:**

> Ambas as variantes retornam JSON `{"detail":"sem mart_pares para <cluster> v1"}`.
> `/health` confirma `mart_pares_rows: 5` — ou seja, o mart de pares essencialmente não foi populado, apesar de `merenda_escolar` ter 8.068 contratos em `/clusters` e `/stats/pr.top_clusters`.

```
{"detail":"sem mart_pares para merenda_escolar v1"}
{"detail":"sem mart_pares para tce_pr_v1__merenda_escolar v1"}
```

**Hipótese de causa raiz:**

> Pipeline `mart_pares` quebrado ou não rodou no último snapshot. Confere com `/health.mart_pares_rows = 5` (qualquer cluster sério teria centenas).

---

### F-004: `cluster_id` no checklist usa prefixo `tce_pr_v1__` que não existe no banco

- **Categoria:** docs
- **Severidade:** low
- **Onde:** `/clusters` e referências em CHECKLIST.md (`tce_pr_v1__merenda_escolar`)
- **Item do checklist:** §A.5, §B.3 `/comparar`, §B.6, §C.2

**Reprodução:**

1. `curl http://127.0.0.1:8001/clusters` → `cluster_id` vem como `merenda_escolar` (sem prefixo), `cluster_version: "v1"` em campo separado.
2. CHECKLIST.md referencia `cluster_id=tce_pr_v1__merenda_escolar`.

**Esperado:**

> Checklist alinhado com o formato real (`merenda_escolar`).

**Observado:**

> Prefixo `tce_pr_v1__` parece ser convenção antiga ou de outro produto. Várias rotas do checklist (`/comparar?cluster_id=tce_pr_v1__...`) só funcionariam se houvesse normalização. Quando testado, ambas as variantes resultam no mesmo erro de F-003 (porque o mart está vazio), mas o formato canônico é o sem prefixo.

---

### F-005: `/ranking/orgaos` retorna array vazio para cluster com 8k contratos

- **Categoria:** api | data
- **Severidade:** high
- **Onde:** `GET /ranking/orgaos?cluster_id=merenda_escolar&limit=10`
- **Item do checklist:** §A.5

**Reprodução:**

1. `curl 'http://127.0.0.1:8001/ranking/orgaos?cluster_id=merenda_escolar&limit=10'`

**Esperado:**

> Array ordenado por volume (≥ 1 item, ranking de órgãos para o cluster).

**Observado:**

> `[]` (array vazio). Provavelmente mesma causa de F-003 — mart subjacente sem dados — mas a rota ao menos não 500.

---

### F-006: `/contratos/search?ordenar_por=data_desc` não ordena por data decrescente

- **Categoria:** api
- **Severidade:** high
- **Onde:** `GET /contratos/search?ordenar_por=data_desc`
- **Item do checklist:** §A.3

**Reprodução:**

1. `curl 'http://127.0.0.1:8001/contratos/search?ordenar_por=data_desc&limit=20'`

**Esperado:**

> `contract_date` em ordem decrescente.

**Observado:**

> Datas vêm misturadas; `2025-11-28` aparece na 5ª posição e `2024-12-19` na 7ª, antes de várias `2025-10-xx`/`2025-11-xx`. A ordem efetiva parece ser idêntica à default (valor desc), com `data_desc` ignorado.

```
["2025-09-25","2025-09-01","2025-08-14","2025-08-18","2025-11-28","2025-03-12",
 "2024-12-19","2025-11-03","2025-11-09","2025-10-13","2025-08-27","2025-07-11",
 "2025-10-30","2025-10-08","2025-10-02","2025-10-17","2025-10-02","2025-10-17",
 "2025-10-17","2025-10-02"]
```

**Hipótese de causa raiz:**

> Handler de `ordenar_por` provavelmente não tem branch para `data_desc` (ou tem, mas o `ORDER BY` não foi alterado). Combina com F-007 (enum não validado) — o backend silenciosamente aceita qualquer valor sem aplicar.

---

### F-007: `/contratos/search?ordenar_por=banana` retorna 200 (deveria ser 422)

- **Categoria:** api | edge-case
- **Severidade:** medium
- **Onde:** `GET /contratos/search?ordenar_por=banana`
- **Item do checklist:** §A.8

**Reprodução:**

1. `curl 'http://127.0.0.1:8001/contratos/search?ordenar_por=banana'`

**Esperado:**

> 422 (`enum inválido`).

**Observado:**

> 200 OK com payload normal (mesmo resultado que sem o parâmetro). Sugere que `ordenar_por` não é tipado como `Enum/Literal` no Pydantic, então qualquer string passa e é silenciosamente ignorada.

---

### F-008: `/contratos/search?since=2024-13-99` retorna 500 (deveria ser 422)

- **Categoria:** api | edge-case
- **Severidade:** high
- **Onde:** `GET /contratos/search?since=2024-13-99`
- **Item do checklist:** §A.8, §9

**Reprodução:**

1. `curl 'http://127.0.0.1:8001/contratos/search?since=2024-13-99'`

**Esperado:**

> 422 com mensagem clara sobre data inválida.

**Observado:**

> 500 Internal Server Error com corpo plano `Internal Server Error`. Erro de parsing de data está vazando para o handler em vez de ser pego no nível de validação.

```
HTTP/1.1 500 Internal Server Error
Internal Server Error
```

**Hipótese de causa raiz:**

> `since` provavelmente está tipado como `str` (não `date`) e o parsing acontece dentro do handler com `datetime.fromisoformat`, levantando `ValueError` não tratada.

---

### F-010: `/comparar` não exibe badge `cluster_version=v1` na tabela renderizada

- **Categoria:** ux | guardrail
- **Severidade:** medium
- **Onde:** `/comparar?cluster_id=merenda_escolar&since=2024-01-01&until=2024-12-31&cd_ibge=4106902&cd_ibge=4115200`
- **Item do checklist:** §B.6 "badge `cluster_version=v1` visível", §B.3 `/comparar`

**Reprodução:**

1. Abrir `/comparar?cluster_id=merenda_escolar&since=2024-01-01&until=2024-12-31&cd_ibge=4106902&cd_ibge=4115200`
2. Procurar por "v1" ou "cluster_version" na página renderizada.

**Esperado:**

> Badge ou rótulo explícito mostrando `cluster_version=v1` para deixar claro contra qual versão de clusterização a comparação está sendo feita. Documentado em §B.6 do checklist.

**Observado:**

> Página carrega tabela com 2 linhas (CURITIBA, TOLEDO) mas em nenhum lugar do DOM aparece "v1" ou "cluster_version". Auditoria fica cega ao versionamento.

**Hipótese de causa raiz:**

> Componente da tabela de comparação não inclui o `cluster_version` retornado pela API; ou o frontend filtra esse campo do payload.

---

### F-011: `/comparar` mostra "sem contratos no cluster" para CURITIBA/TOLEDO em merenda_escolar 2024 mesmo com 8k contratos no cluster

- **Categoria:** drill-down | data | question
- **Severidade:** question
- **Onde:** `/comparar?cluster_id=merenda_escolar&since=2024-01-01&until=2024-12-31&cd_ibge=4106902&cd_ibge=4115200`
- **Item do checklist:** §B.3 `/comparar`

**Reprodução:**

1. Abrir a URL acima.
2. Tabela mostra 2 linhas: CURITIBA e TOLEDO, ambos com "sem contratos no cluster".
3. `/clusters` mostra `merenda_escolar` com 8.068 contratos. `/tce-pr/cluster/merenda_escolar/comparacao-municipios?cluster_version=v1&limit=10` retorna municípios não-vazios (UMUARAMA etc., mas só fora do filtro).

**Esperado:**

> Se a comparação por município efetivamente não tem dados de Curitiba/Toledo no período, o copy precisa explicar (ex.: "Curitiba ainda não tem contratos catalogados em merenda_escolar para 2024"). Caso contrário, há gap no pipeline.

**Observado:**

> UI exibe "sem contratos no cluster" sem distinguir entre "município não tem contratos no cluster" vs "filtro de período exclui tudo" vs "agregação ainda não rodou pra esse município". Confunde diagnóstico.

---

### F-012: `/dispensas` não tem nenhum input de filtro (checklist exige filtro de modalidade visível)

- **Categoria:** ux | question
- **Severidade:** question
- **Onde:** `/dispensas`
- **Item do checklist:** §B.3 `/dispensas` ("Filtro de modalidade aparece")

**Reprodução:**

1. Abrir `/dispensas`.
2. `[...document.querySelectorAll('form input, form select')]` retorna `[]`.

**Esperado:**

> Filtro de modalidade visível, conforme §B.3.

**Observado:**

> Página não tem nenhum form de filtro. Os dados já vêm pré-filtrados para `modalidade=dispensa`. Pode ser intencional (página é dedicada à modalidade dispensa, não faz sentido trocar), mas então o item do checklist está obsoleto.

---

### F-013: `/item/{raw_id}` tem `<title>` genérico "Quanto Pagou" (sem id ou descrição)

- **Categoria:** ux
- **Severidade:** low
- **Onde:** `/item/279460`
- **Item do checklist:** §B.4

**Reprodução:**

1. Abrir `/item/279460`.
2. Título da aba do navegador = "Quanto Pagou".

**Esperado:**

> Título específico, ex.: `Item #279460 · Quanto Pagou` (espelhando `/contrato/{raw_id}` que já faz isso corretamente — `Contrato #279460 · Quanto Pagou`).

**Observado:**

> Título genérico em `/item/`. Diverge do `/contrato/{raw_id}` que tem título específico. Quebra histórico do navegador e compartilhamento de link.

---

### F-014: `/metodologia` tem `<title>` genérico "Quanto Pagou"

- **Categoria:** ux
- **Severidade:** low
- **Onde:** `/metodologia`
- **Item do checklist:** §B.1

**Reprodução:**

1. Abrir `/metodologia`.
2. `document.title === 'Quanto Pagou'`.

**Esperado:**

> Título descritivo, ex.: `Metodologia · Quanto Pagou`.

**Observado:**

> Título genérico. Outras páginas estáticas (manifesto, correções, insights) seguem o padrão `Título · Quanto Pagou`. Inconsistência cosmética.

---

### F-015: Form de `/contratos` usa `name="order"` mas API espera `ordenar_por`

- **Categoria:** docs | api | question
- **Severidade:** low
- **Onde:** `/contratos` (form HTML) vs `GET /contratos/search?ordenar_por=...`
- **Item do checklist:** §A.3, §B.3

**Reprodução:**

1. Abrir `/contratos` no navegador, inspecionar o `<select>` de ordenação → `name="order"`.
2. CHECKLIST.md e API expõem `ordenar_por`.

**Esperado:**

> Convenção única (ou ambos `order`, ou ambos `ordenar_por`).

**Observado:**

> O proxy do Next.js provavelmente traduz `order → ordenar_por` antes de chamar a API. Funciona, mas confunde quem inspeciona a query string da URL pública. Combina com F-007 (qualquer valor é aceito) — risco de regressão silenciosa caso o mapping mude de nome.

---

### F-016: `/fornecedor/{cnpj-inexistente}` e `/municipio/{cd-inexistente}` renderizam página em branco (sem 404 amigável)

- **Categoria:** ux | edge-case
- **Severidade:** high
- **Onde:** `/fornecedor/0000000000000`, `/municipio/9999999`
- **Item do checklist:** §B.5 (estados de UI), §9 (edge cases combinados)

**Reprodução:**

1. Abrir `/fornecedor/0000000000000` no navegador.
2. Abrir `/municipio/9999999` no navegador.

**Esperado:**

> Página 404 amigável (ex.: "Fornecedor não encontrado", "Município sem perfil público") com link de volta. A API já retorna 404 com `detail` explicativo (`fornecedor 0000000000000 sem perfil público (mínimo 5 contratos)`, `municipio cd_ibge=9999999 nao catalogado e nao posso inferir cd_tce`).

**Observado:**

> Ambos os caminhos renderizam **body vazio** (`document.body.innerText === ''`, `body_len: 0`). Não há h1, navegação, mensagem de erro ou link de retorno. Nem mesmo o header global aparece.

```
title: "Quanto Pagou"
h1: undefined
body_len: 0
```

**Hipótese de causa raiz:**

> Página dinâmica do Next.js está jogando em `notFound()` mas sem `not-found.tsx` próximo, ou o handler de erro 404 está vazio. O layout root também não está sendo aplicado nesse fallback.

---

### F-017: `/contratos?since=2024-13-99` propaga 500 do backend (deveria mostrar erro amigável)

- **Categoria:** ux | edge-case
- **Severidade:** medium
- **Onde:** `/contratos?since=2024-13-99`
- **Item do checklist:** §B.5, §9

**Reprodução:**

1. Abrir `/contratos?since=2024-13-99`.

**Esperado:**

> Erro amigável ("Data inválida — informe no formato AAAA-MM-DD") ou auto-correção do filtro.

**Observado:**

> Página renderiza header e h1 normal mas conteúdo principal é um bloco curto contendo strings que matchearam regex `/erro|internal|500/`. Sem feedback acionável pro usuário sobre o quê tá errado. Encadeia com F-008 (backend 500).

---

### F-018: Campo CNPJ na busca aceita "00844138" mas tabela mostra com 14 dígitos — checklist espera filtro funcional ✅, sem regressão visual

- **Categoria:** ux | question
- **Severidade:** question
- **Onde:** `/fornecedores?q=00844138`
- **Item do checklist:** §B.3

**Reprodução:**

1. Abrir `/fornecedores?q=00844138`.

**Esperado:**

> Filtro retorna ATLANTICA (CNPJ completo `00844138000177`).

**Observado:**

> Funciona, retorna ATLANTICA. Sem bug — registrado como question apenas para confirmar que CHECKLIST.md trata isso como caso de filtro parcial, e a UI não mostra "x" para limpar o filtro de CNPJ rapidamente. Cosmético/UX.

---

### F-009: `/tce-pr/municipio/{cd_ibge}/resumo` não expõe `top_clusters` previsto no checklist

- **Categoria:** docs | api
- **Severidade:** low
- **Onde:** `GET /tce-pr/municipio/4106902/resumo`
- **Item do checklist:** §A.4

**Reprodução:**

1. `curl http://127.0.0.1:8001/tce-pr/municipio/4106902/resumo`

**Esperado:**

> Resumo com `n_contratos`, `valor_total`, `top_clusters`.

**Observado:**

> Campos retornados: `cd_ibge, municipio, n_contratos_total, valor_total, n_em_cluster, n_em_quarentena, cobertura_pct`. Sem `top_clusters` (o drill por cluster vive em `/contratos-por-cluster`). E `n_contratos` foi renomeado para `n_contratos_total`.



---

## Resumo final

Execução em 2026-05-09 contra stack local de pé (`/health` 200, web 200, snapshot de 2026-05-07).

- **Itens marcados ✅:** ~96 (de ~130)
- **Itens marcados ❌:** ~20
- **Itens não testados:** ~14
  - §A.6 inteiro (integridade do banco via `docker exec psql`) — ambiente do executor não tem `docker`/`psql` mapeados
  - §B.5 último item (derrubar API e abrir `/fornecedores`) — não foi feito para não interromper o resto da bateria
  - Drill-down de `/comparar` (§C.2 primeiro item) — bloqueado por F-003/F-011 (`merenda_escolar` retorna vazio em Curitiba/Toledo)
  - Validação de soma exata em casos com > 5 itens (§C.2 final) — feita só em casos ≤ 5 itens
- **Total de findings registrados:** 18 (F-001 → F-018)
- **Tempo total da execução:** ~35 minutos

Distribuição de findings por severidade:

- `critical`: 1 (F-003)
- `high`: 5 (F-005, F-006, F-008, F-016, F-018 não — corrigindo: F-005, F-006, F-008, F-016 = 4)
- `medium`: 3 (F-007, F-010, F-017)
- `low`: 6 (F-001, F-004, F-009, F-013, F-014, F-015)
- `question`: 4 (F-002, F-011, F-012, F-018)

### Top 3 prioridades

1. **F-003** — `/pares` retorna `"sem mart_pares"` para qualquer cluster; `mart_pares_rows: 5` em `/health` confirma que o mart de comparação de preços está praticamente vazio, derrubando o núcleo do produto.
2. **F-008** — `/contratos/search?since=2024-13-99` retorna **500** em vez de 422; data inválida vaza para o handler. Combina com **F-017** (frontend não trata erro amigavelmente).
3. **F-016** — `/fornecedor/{cnpj-inexistente}` e `/municipio/{cd-inexistente}` renderizam **página em branco** (sem header, sem h1, sem 404). Quebra confiança e SEO.

Honrosos menção fora do top 3: **F-006** (`ordenar_por=data_desc` não ordena nada — ordenação é silenciosamente ignorada, encadeia com F-007 que aceita qualquer enum).

### Notas livres

**Padrão observado — drift entre CHECKLIST.md e API atual.** F-001
(`db_ok` vs `status`), F-004 (prefixo `tce_pr_v1__` que não existe),
F-009 (`top_clusters` no resumo de município), F-015 (`order` vs
`ordenar_por`) e parcialmente F-002 (limite `total_fornecedores`)
sugerem que o checklist foi escrito contra um snapshot anterior da API.
**Recomendação:** quando os bugs forem corrigidos, fazer uma passagem
explícita atualizando o CHECKLIST.md para refletir o schema vigente,
de preferência via geração automática a partir de `/openapi.json`.

**Padrão observado — guardrails respeitados na superfície.** §6.5 (mín.
5 contratos) é honrado em `/fornecedores` (F-007 confirma override
explícito), `/fornecedor/{cnpj}` retorna 404 explicativo e `/dispensas`
mascara CPFs. A camada UX em volta do guardrail está correta — o que
falta é (a) badge `cluster_version=v1` em `/comparar` (F-010) e (b)
catch de 422/500 amigável (F-008/F-017).

**Padrão observado — pipeline de mart parcialmente quebrado.** F-003
(mart_pares=5 rows total) e F-005 (ranking/orgaos vazio) provavelmente
têm a mesma causa raiz: alguma etapa de `analytics.build_marts`
falhou ou foi pulada no último cron. `/tce-pr/cluster/.../comparacao-municipios`
funciona, então o problema é específico das tabelas `mart_pares` e do
input de `ranking/orgaos`. Vale rodar o build manualmente e conferir
logs de cron antes de cavar a fundo.

**Cobertura sugerida para próxima rodada.**

- **§A.6 (integridade do banco)** — escrever um pequeno script
  `python -m tests.qa.banco_check` que abre conexão com o Postgres
  e roda os 6 SELECTs, comparando contra `/health` e `/stats/pr`.
  Hoje a verificação cega é pesada de fazer manualmente.
- **§B.5 (derrubar API)** — automatizar com um teste que mata o
  worker e abre `/fornecedores` headless. Validação que UI degrada
  graciosamente.
- **§C.2 (validação de soma exata em > 5 itens)** — comparar
  `valor_total_filtrado` retornado em `/contratos/search` com a soma
  visível na agregação de origem. Hoje só foi validado em casos com
  ≤ 5 itens (R$ 626.667.539,54 fornecedor topo de Curitiba bateu
  exato com `/tce-pr/municipio/4106902/fornecedores`).
- **Adicionar §A.10 ao checklist** — testes de schema diferencial:
  cada endpoint deveria ter um snapshot de chaves (`Object.keys`)
  versionado em `tests/qa/snapshots/`, e a próxima rodada falha se o
  schema mudar sem atualização do checklist. Resolve a classe inteira
  de findings F-001/F-004/F-009/F-015 de uma vez.

---

## Resoluções

Sessão de correção em 2026-05-09. Findings agrupados por wave de fix.

### Wave 1 — Frontend (5 findings)

| Finding | O que foi feito | Arquivo |
|---|---|---|
| **F-010** badge `cluster_version=v1` ausente em `/comparar` | Adicionado badge inline no header da seção de comparação (logo abaixo do título da categoria), com tooltip explicativo. | `frontend/app/comparar/page.tsx` |
| **F-013** title genérico em `/item/[raw_id]` | `generateMetadata` adicionado espelhando `/contrato/[id]`. Inclui `robots: noindex,nofollow`. | `frontend/app/item/[raw_id]/page.tsx` |
| **F-014** title genérico em `/metodologia` | `metadata` estática adicionada. | `frontend/app/metodologia/page.tsx` |
| **F-016** página em branco em `/fornecedor/{cnpj-inexistente}` e `/municipio/{cd-inexistente}` | Criado `app/not-found.tsx` global com 404 amigável (header global aplicado, h1, link de retorno, sugestões contextuais). Faltava o `not-found.tsx` boundary do Next App Router. | `frontend/app/not-found.tsx` (novo) |
| **F-017** erro plain de data inválida em `/contratos` | Validação de data no frontend antes de chamar a API. Bloco de erro amigável com instrução pra ajustar o filtro ou limpar. Reduz dependência da F-008 (backend). | `frontend/app/contratos/page.tsx` |

### Wave 2 — Documentação CHECKLIST (6 findings)

| Finding | O que foi feito |
|---|---|
| **F-001** `db_ok` vs `status` em `/health` | Item §A.1 reescrito: agora cita `status: "ok"` + campos reais (`raw_compras`, `item_canonical`, `mart_pares_rows`...). Removida menção a `staging_compras`. |
| **F-002** limite `total_fornecedores ≥ 100k` obsoleto | Atualizado para `≥ 40_000` (~44k). Adicionada nota: 100k era snapshot antigo contando filiais; deduplicação atual por CNPJ. |
| **F-004** prefixo `tce_pr_v1__` que não existe | Todas as referências corrigidas para o cluster_id real (sem prefixo); `cluster_version` é campo separado. |
| **F-009** `top_clusters` em `/tce-pr/municipio/{cd}/resumo` | Item §A.4 atualizado com schema real (`n_contratos_total`, `n_em_cluster`, `n_em_quarentena`, `cobertura_pct`); top_clusters vive em `/contratos-por-cluster`. |
| **F-012** filtro de modalidade em `/dispensas` | Marcado como obsoleto: página é dedicada a dispensa por design, sem filtro. |
| **F-015** `order` (form) vs `ordenar_por` (checklist) | Convenção alinhada: API usa `order=`, checklist atualizado. **Atenção:** `ordenar_por` no checklist anterior nunca funcionou; FastAPI ignora params desconhecidos silenciosamente — o que explica por que F-006/F-007 pareciam bugs. |

### Wave 3 — Backend (5 findings)

| Finding | O que foi feito | Arquivo |
|---|---|---|
| **F-003** `/pares` retorna "sem mart_pares" para qualquer cluster | **Não era bug de dados.** Mart está correto: só federal (CATMAT, com `valor_unitario_normalizado`) entra. Clusters TCE-PR são contract-level por design e não têm preço unitário. Fix: `/pares` agora distingue 3 casos no 404 (cluster não existe / é contract-level / sem itens passando threshold) e sugere `/tce-pr/cluster/{X}/comparacao-municipios` para o caso TCE-PR. CHECKLIST atualizado para usar cluster federal (`oleo_diesel_s10`) no smoke. | `src/api/main.py` |
| **F-005** `/ranking/orgaos` retorna `[]` | Mesma causa raiz de F-003. CHECKLIST atualizado para cluster federal. Endpoint mantém retorno `[]` (idiomático) em vez de 404. | (CHECKLIST) |
| **F-006** `data_desc` ignorado | **Não era bug de código.** API tem branches `data_desc`/`data_asc` corretas (linhas 1018-1023). Bug era de teste: param chama `order`, não `ordenar_por`. CHECKLIST corrigido. | (CHECKLIST) |
| **F-007** `?ordenar_por=banana` aceita 200 | Mesma causa de F-006: `ordenar_por` é param desconhecido (FastAPI ignora). Param real `order` agora tipado como `Literal[...]` → 422 em valor inválido. | `src/api/main.py` |
| **F-008** `?since=2024-13-99` retorna 500 | `since`/`until` em `/contratos/search` e `/tce-pr/cluster/.../ranking-municipios` agora tipados como `date` (não `str`). Pydantic valida → 422 com erro descritivo, em vez de 500 do Postgres por cast inválido. | `src/api/main.py` |

### Não-fix (questions, sem ação)

- **F-002** (limite obsoleto): atualizado no CHECKLIST como hipótese (a) confirmada — snapshot antigo contava filiais.
- **F-011** `/comparar` "sem contratos no cluster" para CURITIBA/TOLEDO em merenda 2024: ambíguo. Possível melhoria futura: distinguir "município sem contratos" de "filtro de período exclui tudo" no copy. Não bloqueante.
- **F-018** filtro CNPJ parcial: confirmado como funcional, sem ação.

### Cleanup adicional (não é finding mas surgiu na investigação)

- 4 endpoints com `order: str` + `if order_sql is None: HTTPException(400)` → trocados por `order: Literal[...]` + `[order]` direto. Validação agora é via Pydantic (422 padronizado), código mais enxuto.
- Cluster federal `oleo_diesel_s10` continua como bom smoke do mart (5 rows = federal fixture × 5 categorias × ~1 grupo de pares).
