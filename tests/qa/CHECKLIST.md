# QA Checklist — Quanto Pagou

Checklist executável por outra IA (ou humano com terminal). O objetivo é
**detectar regressões e inconsistências** em todo o stack atual.

> **Regra de ouro:** qualquer falha — mesmo que pareça pequena — vai pra
> [`FINDINGS.md`](./FINDINGS.md) usando o template lá descrito. **Não
> conserte nada**: este passo é só observação. Conserto vem depois,
> priorizado.

---

## 0. Pré-requisitos

Antes de começar, garanta que a stack está no ar.

```powershell
pwsh scripts\dev_up.ps1
```

Deve subir:

- [ ] **Postgres** (Docker) — `docker ps` mostra container `pg-quanto-pagou`
- [ ] **API** — `curl http://127.0.0.1:8001/health` retorna 200 e JSON
- [ ] **Frontend** — `curl http://127.0.0.1:3001/` retorna 200 e HTML

Se algum dos três falhar, **pare e registre em FINDINGS.md** (categoria
`infra`). Sem stack no ar, nada do resto roda.

**Variáveis úteis:**

```powershell
$API = "http://127.0.0.1:8001"
$WEB = "http://127.0.0.1:3001"
```

Para cada teste abaixo, o critério "**OK**" só vale se TODOS os
sub-itens marcarem ✅.

---

## 1. API — smoke por endpoint

Execute cada `curl`. Marque ✅ se status 200 + payload coerente.
Marque ❌ + abrir entrada em `FINDINGS.md` se 4xx/5xx, exceção, ou
campo faltante.

### 1.1. Meta / catálogo

- [ ] `GET /health` → `{"db_ok": true, ...}` com contagens > 0 em
      `raw_compras` e `staging_compras`
- [ ] `GET /clusters` → array com ≥ 19 clusters (Tier 1.5). Cada item
      tem `cluster_id`, `descricao_canonica`, `categoria`
- [ ] `GET /quarentena/resumo` → array (pode ser vazio se nada em
      quarentena, mas endpoint **não pode** retornar 500)
- [ ] `GET /stats/pr` → JSON com `total_contratos ≥ 150000`,
      `total_municipios ≥ 390`, `top_clusters` com ≥ 5 itens,
      `valor_total_pr` não nulo

### 1.2. Item / contrato canônico

- [ ] `GET /item/1` → 200 ou 404 (depende do raw_id existir). Se 200,
      tem `descricao`, `valor_total`, `cluster_id` (pode ser null)
- [ ] `GET /contrato/1` → mesmo tratamento

### 1.3. Comparação (núcleo do produto)

- [ ] `GET /pares?cluster_id=tce_pr_v1__merenda_escolar` → array com
      pelo menos 1 item (cluster mais maduro do PR)
- [ ] `GET /ranking/orgaos?cluster_id=tce_pr_v1__merenda_escolar` →
      array com órgãos ordenados por volume
- [ ] `GET /tce-pr/cluster/tce_pr_v1__merenda_escolar/comparacao-municipios?cluster_version=v1`
      → array (pode ser vazio se nenhum município bater os critérios)

### 1.4. Município

- [ ] `GET /municipios?limit=5` → top 5 municípios PR por volume.
      Curitiba deve aparecer no top
- [ ] `GET /municipio/4106902/info` → resolve Curitiba (cd_ibge → cd_tce)
- [ ] `GET /tce-pr/municipio/4106902/resumo` → resumo de Curitiba
- [ ] `GET /tce-pr/municipio/4106902/contratos-por-cluster?limit=10`
      → array
- [ ] `GET /tce-pr/municipio/4106902/fornecedores?limit=10` → array

### 1.5. Fornecedor

- [ ] `GET /fornecedores?limit=10` → top 10 fornecedores por volume.
      Cada item tem `n_contratos ≥ 5` (guardrail §6.5 padrão)
- [ ] `GET /fornecedores?search=copel&limit=10` → contém pelo menos
      "COPEL" no nome de algum item
- [ ] Pegue um `fornecedor_cnpj` da resposta acima e teste:
  - [ ] `GET /fornecedor/{cnpj}` → perfil com `n_contratos`,
        `valor_total`, `n_municipios_distintos`
  - [ ] `GET /fornecedor/{cnpj}/por-orgao?limit=5` → array
  - [ ] `GET /fornecedor/{cnpj}/por-municipio?limit=5` → array
  - [ ] `GET /fornecedor/{cnpj}/por-categoria` → array (pode ser vazio
        se fornecedor não está em nenhum cluster)
  - [ ] `GET /fornecedor/{cnpj}/por-modalidade` → array
  - [ ] `GET /fornecedor/{cnpj}/contratos?limit=5` → array com
        `descricao`, `valor_total`, `municipio`

### 1.6. Instituições (busca por destinatário no objeto)

- [ ] `GET /instituicoes/search?q=UPA&limit=20` → JSON com:
  - `total_objeto_contratos ≥ 1000`
  - `total_fornecedores_no_objeto ≥ 100`
  - `valor_total_objeto > 0`
  - `fornecedores_no_objeto` é array com `fornecedor_cnpj`,
    `fornecedor_nome`, `n_contratos`, `valor_total`, `n_municipios`
  - `objetos` é array com `municipio`, `orgao_nome`, `cd_tce`
- [ ] `GET /instituicoes/search?q=hospital&limit=10` → idem, com
      contratos. Verificar que `q` < 2 caracteres dá **erro 422 ou
      payload com 0 resultados explícito** (não deve crashear)

### 1.7. Contratos (drill-down filtrado)

- [ ] `GET /contratos/search?limit=10` → primeira página com 10
      contratos, ordenado por valor desc por padrão
- [ ] `GET /contratos/search?q=merenda&limit=5` → contratos cuja
      descrição **OU** fornecedor_nome **OU** orgao_nome contém
      "merenda" (ILIKE)
- [ ] `GET /contratos/search?cd_tce=410690&limit=5` → só contratos de
      Curitiba
- [ ] `GET /contratos/search?since=2024-01-01&until=2024-12-31&limit=5`
      → só 2024
- [ ] `GET /contratos/search?modalidade=dispensa&limit=5` → só
      dispensas
- [ ] `GET /contratos/search?ordenar_por=data_desc&limit=5` →
      ordenação por data desc

### 1.8. Escolas

- [ ] `GET /escolas?limit=10` → array com escolas catalogadas. Total
      deve ser ≥ 500 (catálogo PR atual ~506)
- [ ] `GET /escolas?search=carlos&limit=5` → escolas com "carlos" no
      nome
- [ ] Pegue um `escola_slug` da resposta e teste:
  - [ ] `GET /escolas/{slug}/contratos?limit=10` → array de contratos
        que mencionam essa escola

### 1.9. Dispensas

- [ ] `GET /tce-pr/dispensas/top-fornecedores?limit=10&min_contratos=5`
      → array de top fornecedores em dispensa de licitação
- [ ] Verificar que CPFs (CNPJs com 11 dígitos formatados como CPF)
      vêm com `cnpj_mascarado: true` por padrão

### 1.10. Documentação interativa

- [ ] `GET /docs` → Swagger UI carrega
- [ ] `GET /openapi.json` → JSON válido com todos os paths acima

---

## 2. Frontend — smoke por página

Para cada URL: abra no navegador (ou `curl` + grep) e verifique que
**carrega sem erro** (status 200, sem stack trace HTML, conteúdo
visível).

### 2.1. Páginas estáticas

- [ ] `/` (home) — header com badge PR/Federal, título visível
- [ ] `/manifesto` — texto narrativo
- [ ] `/metodologia` — explica fontes, guardrails, cluster_version
- [ ] `/correcoes` — formulário ou lista de correções
- [ ] `/insight/diesel-ministerios` — insight federal (fixture)
- [ ] `/insight/merenda-escolar-pr` — insight PR

### 2.2. Páginas de busca / listagem

- [ ] `/buscar` — duas seções (municípios + fornecedores), top 30 cada
- [ ] `/buscar?m=curitiba` — resultado de Curitiba aparece em
      "Municípios PR"
- [ ] `/buscar?f=atlantica` — pelo menos 1 fornecedor com "atlantica"
- [ ] `/fornecedores` — top 50 fornecedores. Filtro mínimo 5
      contratos (default)
- [ ] `/fornecedores?q=copel` — fornecedores com "copel" no nome
- [ ] `/fornecedores?q=00844138` — busca por CNPJ parcial → ATLANTICA
- [ ] `/fornecedores?min=2` — alerta atencional aparece (abaixo do
      guardrail §6.5)
- [ ] `/instituicoes` — sem `q`, mostra banner de limites
- [ ] `/instituicoes?q=UPA` — mostra 3 stats (contratos, volume,
      fornecedores únicos), seção "Quem foi pago em contratos com 'UPA'
      no objeto", seção "Por município e órgão contratante"
- [ ] `/instituicoes?q=zz` — termo curto: ou redireciona, ou mostra
      empty state
- [ ] `/contratos` — lista paginada, ordenação default desc por valor
- [ ] `/contratos?q=merenda` — busca textual aplicada
- [ ] `/contratos?cd_tce=410690&modalidade=dispensa&since=2024-01-01`
      — múltiplos filtros combinados
- [ ] `/dispensas` — top fornecedores em dispensa, filtro de modalidade
- [ ] `/escolas` — catálogo, ≥ 500 escolas

### 2.3. Páginas de detalhe (URLs canônicas)

- [ ] `/municipio/410690` — Curitiba: agregados por cluster,
      fornecedores top
- [ ] `/fornecedor/00844138000177` — ATLANTICA: perfil com várias
      seções (por órgão, município, categoria, modalidade, contratos)
- [ ] `/escolas/{algum-slug-da-listagem}` — contratos da escola
- [ ] `/item/1` — item canônico (se raw_id=1 existe; senão tente algum
      ID válido visto em outras telas)

### 2.4. Página de comparação

- [ ] `/comparar` — sem cluster: empty state explicando como usar
- [ ] `/comparar?cluster_id=tce_pr_v1__merenda_escolar&since=2024-01-01&until=2024-12-31`
      → tabela com municípios comparáveis
- [ ] `/comparar?cluster_id=tce_pr_v1__merenda_escolar` (sem datas) →
      **deve obrigar o filtro de data** (formulário aparece, ou
      redireciona, ou exibe aviso)

---

## 3. Drill-down universal

Premissa: clicar em qualquer **valor monetário agregado** abre
`/contratos` filtrado pra exatamente aquele subset.

Em cada caso abaixo: clique no valor e confirme que a tela seguinte
mostra contratos cujo somatório bate (ou está muito próximo) ao valor
exibido na origem.

- [ ] `/comparar?cluster_id=...` → clicar no valor de um município →
      `/contratos?cluster_id=...&cd_tce=...` mostra contratos daquele
      cluster + município
- [ ] `/fornecedor/{cnpj}` → clicar em valor por órgão →
      `/contratos?fornecedor_cnpj=...&orgao_codigo=...`
- [ ] `/fornecedor/{cnpj}` → clicar em valor por município →
      `/contratos?fornecedor_cnpj=...&cd_tce=...`
- [ ] `/instituicoes?q=UPA` → clicar no valor de um fornecedor →
      `/contratos?q=UPA&fornecedor_cnpj=...`
- [ ] `/instituicoes?q=UPA` → clicar no valor de um (município, órgão)
      → `/contratos?q=UPA&orgao_codigo=...&cd_tce=...`
- [ ] `/fornecedores` → clicar no valor → `/contratos?fornecedor_cnpj=...`
- [ ] `/municipio/410690` → clicar em valor por cluster →
      `/contratos?cluster_id=...&cd_tce=410690`

**Validação de soma:** em pelo menos um caso, anote o valor exibido na
origem e some manualmente os primeiros 5 contratos da página de destino
(`valor_total`). Se a página de destino tem ≤ 5 itens, a soma deve bater
exatamente. Se tem mais, registre apenas se a divergência parecer
estrutural (não arredondamento centavos).

---

## 4. Cross-links entre páginas

Cada página deve ter saídas claras pra outras seções relacionadas.

- [ ] Header global (`/_layout`): tem nav com Fornecedores,
      Instituições, Buscar, Comparar, Dispensas, Escolas, Manifesto,
      Metodologia, Correções, API
- [ ] Header: link "API" abre `http://127.0.0.1:8001/docs` em nova aba
- [ ] `/fornecedores` rodapé: links pra `/instituicoes`, `/comparar`,
      `/contratos`
- [ ] `/instituicoes` rodapé: links pra `/fornecedores`, `/contratos`
- [ ] `/buscar`: link pra URL canônica `/fornecedor/{cnpj}` e
      `/municipio/{cd_tce}` em cada linha
- [ ] `/contratos` linha de contrato: clicar abre `/contrato/{raw_id}`
      ou `/item/{raw_id}` (qualquer um dos dois é válido)
- [ ] Footer global: link "Reportar erro" abre `/correcoes`

---

## 5. Guardrails e invariantes

Estes são **convicções do produto**. Quebra deles é bug grave.

### 5.1. Guardrail §6.5 — fornecedor com ≥ 5 contratos

- [ ] `/fornecedores` (sem `min` na URL) — todos os itens listados têm
      `n_contratos ≥ 5`
- [ ] `/fornecedor/{cnpj}` para um fornecedor com **menos** de 5
      contratos: deve retornar 404, ou banner explicando "perfil não
      publicado". (Para encontrar um caso, consulte
      `GET /fornecedores?min_contratos=1&limit=200` e pegue um com
      `n_contratos < 5`)

### 5.2. Quarentena visível, nunca escondida

- [ ] `GET /quarentena/resumo` retorna lista
- [ ] Em `/contratos`, contratos quarentenados aparecem com **label**
      visível (não somem da página)

### 5.3. Cluster_version exposto

- [ ] `/comparar` mostra cluster_version=v1 na URL ou no badge da
      tabela
- [ ] `/metodologia` menciona "cluster_version" e explica o que é

### 5.4. Drill-down preserva filtros

- [ ] Em `/contratos`, o formulário de filtros tem os campos
      preenchidos com o que veio na URL (não deve ser sempre vazio)
- [ ] Mudar um filtro e submeter mantém os outros

### 5.5. Datas obrigatórias em comparações

- [ ] `/comparar?cluster_id=...` sem `since`/`until`: tela deixa
      explícito que data é obrigatória, ou aplica default visível
      (não silencioso)

### 5.6. Linguagem honesta

- [ ] Nenhuma página usa o termo "Risco" sem decompor em sub-scores
- [ ] `/instituicoes` tem banner explicando que "termo no objeto" ≠
      "verba total da unidade"
- [ ] `/metodologia` lista limites de cobertura

---

## 6. Edge cases

Para cada um, **registre comportamento observado** mesmo que não pareça
quebrado — outra IA pode discordar do que é "aceitável".

- [ ] `/instituicoes?q=` (vazio) → não deve crashear
- [ ] `/instituicoes?q=zz9999` (sem match) → empty state amigável
- [ ] `/fornecedor/0000000000000` (CNPJ que não existe) → 404 ou
      mensagem clara
- [ ] `/municipio/9999999` (cd_tce inválido) → 404 ou mensagem
- [ ] `/contratos?since=2099-01-01` (data no futuro) → empty state,
      não erro
- [ ] `/contratos?since=2024-13-99` (data inválida) → 400 ou ignora
      filtro
- [ ] URLs com caracteres especiais: `/fornecedores?q=são%20paulo`
      funciona (não duplica encoding)
- [ ] Página de contrato com `valor_total NULL` (raro mas existe na
      raw): UI mostra "—" ou "n/a", não "null" ou "NaN"

---

## 7. Performance e robustez

Não é benchmark, é farejador de regressão grosseira.

- [ ] `/stats/pr` responde em < 3 segundos
- [ ] `/instituicoes/search?q=hospital` em < 5 segundos
- [ ] `/contratos/search?limit=50` em < 3 segundos
- [ ] Recarregar `/` 5x seguidas: nenhuma falha intermitente

---

## 8. Documentação e DX

- [ ] `README.md` raiz menciona como subir a stack (`scripts/dev_up.ps1`)
- [ ] `DEPLOY.md` existe e está coerente com a arquitetura atual
- [ ] `PLANO.md` reflete features já implementadas (não promete o que
      ainda não tem)
- [ ] `/metodologia` no site espelha o que está em `PLANO.md`

---

## Como reportar

Toda falha encontrada acima → **uma entrada nova** em
[`FINDINGS.md`](./FINDINGS.md), seguindo o template lá descrito.

Não consertar. Apenas observar e descrever.

Quando terminar:

1. Conte quantos itens foram ✅ vs ❌. Anote o total no final do
   FINDINGS.md.
2. Identifique os 3 piores findings (prioridade alta) e marque-os.
3. Registre **tempo total** que levou pra rodar o checklist.
