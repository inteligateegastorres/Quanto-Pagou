# QA Checklist — Quanto Pagou

Checklist executável por outra IA (ou humano com terminal). Detecta
**regressões e inconsistências** em todo o stack — separado em três
partes paralelas:

- **Parte A — Backend** (API + banco)
- **Parte B — Frontend** (páginas + interações)
- **Parte C — Integração** (back ↔ front coerentes, drill-down, cross-links)

> **Regra de ouro:** qualquer falha — mesmo pequena — vai pra
> [`FINDINGS.md`](./FINDINGS.md) usando o template lá descrito. **Não
> conserte nada.** Esta fase é só observação. Conserto vem depois,
> priorizado.

---

## 0. Pré-requisitos

```powershell
pwsh scripts\dev_up.ps1
```

Deve subir os 3 componentes:

- [ ] **Postgres** — `docker ps` mostra container `pg-quanto-pagou`
- [ ] **API** — `curl http://127.0.0.1:8001/health` → 200, JSON com
      `db_ok: true`
- [ ] **Frontend** — `curl http://127.0.0.1:3001/` → 200, HTML com
      `<title>Quanto Pagou`

Se algum falhar, **pare e registre em FINDINGS.md** (categoria `infra`).

**Variáveis úteis:**

```powershell
$API = "http://127.0.0.1:8001"
$WEB = "http://127.0.0.1:3001"
```

---

# Parte A — Backend (API + banco)

Foco: **payload correto, schema válido, dado coerente, guardrail
respeitado**. Cada item é um `curl` com critério de aceite.

## A.1. Saúde e meta

- [ ] `GET /health` → 200 com `db_ok: true` e contagens > 0 em
      `raw_compras` e `staging_compras`
- [ ] `GET /stats/pr` →
  - `total_contratos ≥ 150_000`
  - `total_municipios ≥ 390`
  - `total_fornecedores ≥ 100_000`
  - `top_clusters` tem ≥ 5 itens
  - `valor_total_pr` não nulo
  - `last_snapshot_at` é timestamp válido
- [ ] `GET /quarentena/resumo` → array (pode ser vazio mas **não 500**)
- [ ] `GET /clusters` → ≥ 19 itens, cada um com `cluster_id`,
      `descricao_canonica`, `categoria`

## A.2. Endpoints de listagem (smoke + schema)

Para cada endpoint, validar **status 200, payload é array, primeiro
item tem todos os campos esperados, tipos corretos**.

- [ ] `GET /municipios?limit=10` → cada item tem `cd_tce`, `cd_ibge`,
      `nome`, `porte`, `n_contratos`, `valor_total`
- [ ] `GET /fornecedores?limit=10` → cada item tem `fornecedor_cnpj`,
      `fornecedor_nome`, `n_contratos`, `valor_total`,
      `n_municipios_distintos`. **Todos com `n_contratos ≥ 5`** (default
      do endpoint = guardrail §6.5)
- [ ] `GET /escolas?limit=10` → cada item tem `escola_slug`,
      `escola_nome`, `n_mencoes`, `n_municipios`, `valor_total`
- [ ] `GET /tce-pr/dispensas/top-fornecedores?limit=10` → cada item
      tem `fornecedor_cnpj`, `fornecedor_nome`, `n_dispensas`,
      `valor_total_dispensas`, `cnpj_mascarado`

## A.3. Endpoints de busca (filtros funcionando)

- [ ] `GET /fornecedores?search=copel&limit=5` → resultado contém ao
      menos um item com "COPEL" no `fornecedor_nome`
- [ ] `GET /fornecedores?search=00844138&limit=5` → busca por CNPJ
      parcial funciona (retorna ATLANTICA)
- [ ] `GET /municipios?search=curitiba&limit=5` → primeiro item é
      Curitiba (`cd_tce=410690` ou `cd_ibge=4106902`)
- [ ] `GET /escolas?search=carlos&limit=5` → algum item tem "Carlos" no
      nome
- [ ] `GET /instituicoes/search?q=UPA&limit=10` →
  - `total_objeto_contratos ≥ 1_000`
  - `total_fornecedores_no_objeto ≥ 100`
  - `valor_total_objeto > 0`
  - `fornecedores_no_objeto[0]` tem todos os campos
  - `objetos[0]` tem `municipio`, `orgao_nome`, `cd_tce`
- [ ] `GET /contratos/search?limit=10` → ordenado por `valor_total
      DESC` por padrão (primeiro item ≥ último)
- [ ] `GET /contratos/search?q=merenda&limit=5` → busca textual cobre
      `descricao` **e** `fornecedor_nome` **e** `orgao_nome` (verifique
      pelo menos um caso onde o termo só aparece em fornecedor/orgao)
- [ ] `GET /contratos/search?cd_tce=410690&limit=5` → todos com
      `cd_tce=410690`
- [ ] `GET /contratos/search?since=2024-01-01&until=2024-12-31&limit=5`
      → todos com `contract_date` em 2024
- [ ] `GET /contratos/search?modalidade=dispensa&limit=5` → todos com
      `modalidade` resolvendo pra dispensa
- [ ] `GET /contratos/search?ordenar_por=data_desc&limit=5` →
      `contract_date` decrescente

## A.4. Endpoints de detalhe (URL canônica)

- [ ] `GET /municipio/4106902/info` → `cd_tce=410690`, `nome=Curitiba`
- [ ] `GET /municipio/410690/info` → mesmo resultado (resolve cd_tce
      também)
- [ ] `GET /tce-pr/municipio/4106902/resumo` → resumo de Curitiba com
      `n_contratos`, `valor_total`, `top_clusters`
- [ ] `GET /tce-pr/municipio/4106902/contratos-por-cluster?limit=10` →
      array
- [ ] `GET /tce-pr/municipio/4106902/fornecedores?limit=10` → array
- [ ] Pegue um CNPJ de `/fornecedores?limit=1` e teste:
  - [ ] `GET /fornecedor/{cnpj}` → perfil com `n_contratos ≥ 5`,
        `valor_total`, `n_municipios_distintos`
  - [ ] `GET /fornecedor/{cnpj}/por-orgao?limit=5` → array
  - [ ] `GET /fornecedor/{cnpj}/por-municipio?limit=5` → array
  - [ ] `GET /fornecedor/{cnpj}/por-categoria` → array (pode ser vazio
        se fornecedor não está em cluster algum, mas não 500)
  - [ ] `GET /fornecedor/{cnpj}/por-modalidade` → array
  - [ ] `GET /fornecedor/{cnpj}/contratos?limit=5` → array
- [ ] Pegue um `escola_slug` de `/escolas?limit=1` e teste:
  - [ ] `GET /escolas/{slug}/contratos?limit=10` → array

## A.5. Endpoints de comparação (núcleo do produto)

- [ ] `GET /pares?cluster_id=tce_pr_v1__merenda_escolar&limit=10` →
      array com `produto_normalizado`, `unit_price_brl`, etc.
- [ ] `GET /ranking/orgaos?cluster_id=tce_pr_v1__merenda_escolar&limit=10`
      → array ordenado por volume
- [ ] `GET /tce-pr/cluster/tce_pr_v1__merenda_escolar/comparacao-municipios?cluster_version=v1&limit=10`
      → array

## A.6. Integridade de dados (banco)

Para cada um, conecte no Postgres e rode SQL. Critério: **resultado
faz sentido E bate com o que a API expõe**.

```powershell
docker exec -i pg-quanto-pagou psql -U postgres -d gov -c "<SQL>"
```

- [ ] `SELECT COUNT(*) FROM raw.compras` → bate com `n_raw_compras`
      em `/health`
- [ ] `SELECT COUNT(DISTINCT raw_payload->>'cd_tce') FROM raw.compras`
      → bate com `total_municipios` em `/stats/pr`
- [ ] `SELECT COUNT(DISTINCT fornecedor_cnpj) FROM raw.compras WHERE
      fornecedor_cnpj IS NOT NULL` → bate com `total_fornecedores` em
      `/stats/pr`
- [ ] `SELECT COUNT(*) FROM raw.compras WHERE cluster_id IS NOT NULL`
      → bate com `n_em_cluster` em `/stats/pr`
- [ ] `SELECT cluster_version FROM raw.compras WHERE cluster_id IS
      NOT NULL GROUP BY cluster_version` → todas em `v1` (sem
      versionamento misturado)
- [ ] `SELECT COUNT(*) FROM raw.compras WHERE motivo_quarentena IS
      NOT NULL` ≥ 0 — quarentenados existem e estão **nas mesmas
      tabelas** (não foram removidos)

## A.7. Guardrails de backend

- [ ] `GET /fornecedor/<CNPJ-com-3-contratos>` → 404 ou
      `ProfileNotPublishedError` (não pode retornar perfil pleno
      abaixo de 5 contratos). Para encontrar candidato:
      `GET /fornecedores?min_contratos=1&limit=200` e pegue o último
- [ ] `GET /fornecedores` (sem `min_contratos`) → todos têm
      `n_contratos ≥ 5`
- [ ] `GET /fornecedores?min_contratos=1` → permite < 5 (override
      explícito)
- [ ] Schema `cluster_version` em todas as respostas que comparam
      preço (`/pares`, `/comparacao-*`) — senão é bug

## A.8. Edge cases de API (erros esperados)

- [ ] `GET /instituicoes/search?q=` (vazio) → 422 ou 200 com payload
      vazio explícito (não 500)
- [ ] `GET /instituicoes/search?q=z` (1 char) → 422 (`min_length=2`)
- [ ] `GET /fornecedor/0000000000000` → 404
- [ ] `GET /municipio/9999999/info` → 404
- [ ] `GET /contratos/search?since=2024-13-99` → 422 (data inválida)
- [ ] `GET /contratos/search?ordenar_por=banana` → 422 (enum
      inválido)
- [ ] `GET /docs` → Swagger carrega
- [ ] `GET /openapi.json` → JSON válido com todos os paths

## A.9. Performance backend (sem benchmark, só sniff)

- [ ] `time curl $API/stats/pr` → < 3 s
- [ ] `time curl "$API/instituicoes/search?q=hospital&limit=20"` → < 5 s
- [ ] `time curl "$API/contratos/search?limit=50"` → < 3 s
- [ ] `time curl $API/fornecedores?limit=100` → < 5 s

---

# Parte B — Frontend (páginas + interações)

Foco: **renderização sem erro, formulários funcionam, dados aparecem,
linguagem honesta, navegação consistente**.

Para cada item: abra no navegador (ou `curl + grep`). Critério "**OK**"
exige status 200 + conteúdo visível + sem stack trace HTML + sem texto
literal `undefined` ou `NaN` na UI.

## B.1. Smoke — páginas estáticas

- [ ] `/` (home) — header visível, badges PR/Federal, CTA
- [ ] `/manifesto` — texto narrativo carrega
- [ ] `/metodologia` — explica fontes, guardrails, cluster_version
- [ ] `/correcoes` — lista ou formulário de correções
- [ ] `/insight/diesel-ministerios` — insight federal renderiza
- [ ] `/insight/merenda-escolar-pr` — insight PR renderiza
- [ ] `/insight/diesel-ministerios/opengraph-image` → retorna PNG
      (`Content-Type: image/png`)

## B.2. Smoke — páginas de listagem/busca

Cada uma deve carregar e mostrar dados (não pode ficar vazia se a
API tem dados).

- [ ] `/buscar` → 2 seções (Municípios PR, Fornecedores), top 30 cada,
      sem busca aplicada
- [ ] `/fornecedores` → top 50, default `min=5`
- [ ] `/instituicoes` → mostra **banner de limites** quando sem `q`
- [ ] `/contratos` → lista paginada, ordenação default visível
- [ ] `/dispensas` → top fornecedores em dispensa, filtros visíveis
- [ ] `/escolas` → catálogo, ≥ 500 escolas

## B.3. Funcional — busca e filtros (formulários)

Para cada formulário: digite valor, submeta, valide que a URL
atualiza com os params **e** o resultado muda.

### `/buscar`

- [ ] Campo "m" (município): digitar `curitiba` → URL `?m=curitiba`,
      Curitiba aparece no topo da seção Municípios
- [ ] Campo "f" (fornecedor): digitar `atlantica` → URL `?f=atlantica`,
      ATLANTICA CONSTRUCOES aparece em Fornecedores
- [ ] Submeter os dois ao mesmo tempo (m e f) → ambos preservados na URL

### `/fornecedores`

- [ ] Campo `q`: digitar `copel` → resultado filtra
- [ ] Campo `min`: trocar pra `2` → alerta atencional aparece
      ("abaixo do guardrail §6.5")
- [ ] Campo `min`: trocar pra `100` → resultado encolhe drasticamente
- [ ] Buscar CNPJ parcial `00844138` → ATLANTICA aparece

### `/instituicoes`

- [ ] Buscar `UPA` → 3 stats no topo (contratos, volume, fornecedores
      únicos), 2 seções abaixo
- [ ] Buscar `CRAS` → resultado muda
- [ ] Buscar `zz9999` (sem match) → empty state amigável (não erro)
- [ ] Buscar termo curto `ab` (< 2 chars) → form bloqueia (HTML5
      `minLength=2`)

### `/contratos`

- [ ] Buscar `q=merenda` → filtra
- [ ] Combinar 3 filtros (`?cd_tce=410690&modalidade=dispensa&since=2024-01-01`)
      → todos preservados; resultado bate
- [ ] Trocar ordenação no select → URL atualiza com `ordenar_por=...`
- [ ] Form de filtros mostra valores atuais preenchidos (não sempre
      vazios)

### `/dispensas`

- [ ] Filtro de modalidade aparece
- [ ] CPFs/PFs vêm com `cnpj_mascarado: true` na UI (label "PF
      mascarado" ou similar)

### `/comparar`

- [ ] Sem `cluster_id` → empty state explicando como usar
- [ ] Com `cluster_id` mas sem datas → **deve obrigar filtro de data**
      (formulário aparece, ou aviso, ou redireciona)
- [ ] Com `cluster_id=tce_pr_v1__merenda_escolar&since=2024-01-01&until=2024-12-31`
      → tabela com municípios comparáveis, badge `cluster_version=v1`

### `/escolas`

- [ ] Buscar `carlos` → escolas com "Carlos" no nome aparecem
- [ ] Lista mostra `n_mencoes`, `valor_total` por escola

## B.4. Smoke — páginas de detalhe (URLs canônicas)

- [ ] `/municipio/410690` → Curitiba: agregados por cluster,
      fornecedores top, drill-down funciona
- [ ] `/fornecedor/00844138000177` → ATLANTICA: várias seções (por
      órgão, município, categoria, modalidade, contratos)
- [ ] `/escolas/<slug-da-listagem>` → contratos da escola
- [ ] `/item/{raw_id}` → contrato canônico (use ID válido visto em
      `/contratos`)
- [ ] `/contrato/{raw_id}` → idem

## B.5. Estados de UI (loading / erro / vazio)

- [ ] `/fornecedores?q=zz9999` → empty state ("Sem resultados...")
- [ ] `/instituicoes?q=zz9999` → empty state com sugestões
- [ ] `/contratos?q=zz9999` → empty state, paginação coerente
- [ ] Derrubar a API e abrir `/fornecedores` → mensagem de erro
      amigável (não tela branca, não stack trace)
  ```powershell
  # Derruba API (lembrar de subir depois!)
  Stop-Process -Id (Get-NetTCPConnection -LocalPort 8001).OwningProcess
  # Testa
  curl $WEB/fornecedores
  # Sobe de novo
  pwsh scripts\dev_up.ps1
  ```

## B.6. Guardrails na UI

- [ ] **Linguagem honesta:** nenhuma página usa "Risco" sem decompor
      em sub-scores (procure literal "Risco" em todas as páginas)
- [ ] `/instituicoes`: banner explícito que "termo no objeto" ≠
      "verba total da unidade"
- [ ] `/fornecedores`: aviso quando `min < 5` ("abaixo do guardrail
      §6.5")
- [ ] `/escolas`: deixa claro que é catálogo de transparência (não
      comparação numérica)
- [ ] `/comparar`: badge `cluster_version=v1` visível
- [ ] `/metodologia`: lista limites de cobertura, explica
      cluster_version, golden set, IQR (sem σ ingênuo)
- [ ] Quarentenados aparecem na UI com label visível (não somem)

## B.7. Cross-links e navegação

- [ ] Header global tem nav: Fornecedores, Instituições, Buscar,
      Comparar, Dispensas, Escolas, Manifesto, Metodologia, Correções,
      API
- [ ] Header → "API" abre `http://127.0.0.1:8001/docs` em nova aba
- [ ] `/fornecedores` rodapé: links pra `/instituicoes`, `/comparar`,
      `/contratos`
- [ ] `/instituicoes` rodapé: links pra `/fornecedores`, `/contratos`
- [ ] `/buscar`: cada linha de fornecedor abre `/fornecedor/{cnpj}`,
      cada município abre `/municipio/{cd_tce}`
- [ ] Footer global: link "Reportar erro" abre `/correcoes`
- [ ] Em qualquer linha de contrato (`/contratos`, `/escolas/[slug]`,
      perfil de fornecedor): clicar abre `/contrato/{raw_id}` ou
      `/item/{raw_id}`

## B.8. Acessibilidade básica

- [ ] `<html lang="pt-BR">` no `view-source` da home
- [ ] Inputs de formulário têm `name` (essencial pra submit
      funcionar) e `placeholder`/`title` informativo
- [ ] Imagens (se houver) têm `alt`
- [ ] Botões e links têm texto visível (não só ícone sem `aria-label`)
- [ ] Heading hierarchy: `<h1>` único por página, `<h2>` para seções

## B.9. Performance frontend (sniff)

- [ ] `/` carrega < 2 s no recarregamento
- [ ] `/instituicoes?q=hospital` carrega < 6 s (chama API, então
      depende dela)
- [ ] `/contratos` (sem filtro) carrega < 3 s
- [ ] Sem `console.error` no DevTools em nenhuma página visitada

---

# Parte C — Integração (back ↔ front coerentes)

Foco: **valor exibido na UI = valor que a API devolve**, links
funcionam end-to-end, drill-down preserva contexto.

## C.1. Coerência back ↔ front (valor exibido bate com API)

Para cada par, abra **as duas URLs em paralelo** e confira que os
números batem (tolerância: arredondamento de centavos).

| Frontend | Backend | Campo a comparar |
|---|---|---|
| `/` (home) — total contratos | `/stats/pr` → `total_contratos` | número |
| `/` — total municípios | `/stats/pr` → `total_municipios` | número |
| `/instituicoes?q=UPA` — stat "Contratos com o termo" | `/instituicoes/search?q=UPA` → `total_objeto_contratos` | número |
| `/instituicoes?q=UPA` — stat "Fornecedores únicos" | `/instituicoes/search?q=UPA` → `total_fornecedores_no_objeto` | número |
| `/fornecedor/00844138000177` — total valor | `/fornecedor/00844138000177` → `valor_total` | R$ formatado |
| `/municipio/410690` — total contratos | `/tce-pr/municipio/4106902/resumo` → `n_contratos` | número |
| `/escolas` — primeira escola, valor | `/escolas?limit=1` → `valor_total` | R$ |

- [ ] Todos os pares acima batem
- [ ] Anote em FINDINGS qualquer divergência além de centavos

## C.2. Drill-down universal (E2E)

Premissa: clicar em **qualquer valor monetário agregado** abre
`/contratos` filtrado pra exatamente aquele subset.

Para cada caso: clique no valor e confirme que (a) a URL de destino
tem os filtros corretos, (b) os contratos exibidos são realmente
daquele subset, (c) somar os primeiros 5 contratos da página de
destino bate (≤ 5 itens) ou é coerente (> 5 itens).

- [ ] `/comparar?cluster_id=...&since=...&until=...` → clicar no valor
      de um município → `/contratos?cluster_id=...&cd_tce=...` mostra
      apenas contratos daquele cluster + município no período
- [ ] `/fornecedor/{cnpj}` → clicar em valor por órgão →
      `/contratos?fornecedor_cnpj=...&orgao_codigo=...`
- [ ] `/fornecedor/{cnpj}` → clicar em valor por município →
      `/contratos?fornecedor_cnpj=...&cd_tce=...`
- [ ] `/instituicoes?q=UPA` → clicar no valor de um fornecedor →
      `/contratos?q=UPA&fornecedor_cnpj=...`
- [ ] `/instituicoes?q=UPA` → clicar no valor de (município, órgão) →
      `/contratos?q=UPA&orgao_codigo=...&cd_tce=...`
- [ ] `/fornecedores` → clicar no valor →
      `/contratos?fornecedor_cnpj=...`
- [ ] `/municipio/410690` → clicar em valor por cluster →
      `/contratos?cluster_id=...&cd_tce=410690`

**Validação de soma:** em pelo menos 1 caso onde a página de destino
tem ≤ 5 itens, a soma deve bater **exatamente** (centavos OK). Em
caso > 5 itens, registre se a divergência for estrutural (não
arredondamento).

## C.3. URLs canônicas funcionam fora de cliques

Cole essas URLs direto no navegador. Devem funcionar sem ter clicado
em link anterior.

- [ ] `/fornecedor/00844138000177`
- [ ] `/municipio/410690`
- [ ] `/escolas/escola-municipal-carlos-gomes` (se slug existir;
      senão use um da listagem)
- [ ] `/item/<raw_id>` (use raw_id válido da listagem `/contratos`)
- [ ] `/contratos?fornecedor_cnpj=00844138000177` — filtro direto

## C.4. Idempotência: mesma URL = mesmo resultado

Recarregar `/` 5x — total de contratos não pode oscilar entre
recargas (cache pode atrasar, mas valor não pode "piscar" entre dois
diferentes).

- [ ] `/` recarregada 5x: número total de contratos é constante
- [ ] `/stats/pr` 5x via curl: payload idêntico (admite
      `last_snapshot_at` igual)

## C.5. Cron + dados frescos (se aplicável)

- [ ] `/stats/pr` → `last_snapshot_at` é data dos últimos 7 dias
      (cron weekly). Se mais antigo: registrar como question (cron
      pode estar pausado intencionalmente).

---

# 9. Edge cases combinados (back + front juntos)

Para cada caso abaixo: testar **rota da API** e **página correspondente**
no front. Comportamento deve ser **consistente** (se API retorna 422,
front mostra erro amigável, não tela branca).

- [ ] CNPJ inválido (`/fornecedor/0000000000000` no API e no front)
- [ ] cd_tce inválido (`/municipio/9999999`)
- [ ] Data no futuro (`/contratos?since=2099-01-01`)
- [ ] Data malformada (`/contratos?since=2024-13-99`)
- [ ] Caracteres especiais (`/fornecedores?q=são%20paulo` —
      encoding correto)
- [ ] Item com `valor_total NULL` na raw — UI mostra "—" não "null"
- [ ] Fornecedor com CPF (11 dígitos com zeros à esquerda no CNPJ
      column) — UI mascara

---

# 10. Documentação coerente

- [ ] `README.md` raiz cita `scripts/dev_up.ps1`
- [ ] `DEPLOY.md` coerente com arquitetura atual
- [ ] `PLANO.md` reflete features já implementadas (não promete o
      que não tem)
- [ ] `/metodologia` no site espelha `PLANO.md`
- [ ] `tests/qa/CHECKLIST.md` (este arquivo) referencia features que
      ainda existem (não cita rota deletada)

---

## Como reportar

Toda falha → **uma entrada nova** em [`FINDINGS.md`](./FINDINGS.md).

**Não consertar.** Apenas observar e descrever.

Quando terminar:

1. Conte ✅ vs ❌ por parte (A, B, C). Anote no resumo final do
   FINDINGS.md.
2. Identifique os 3 piores findings (prioridade alta) e marque-os.
3. Registre **tempo total** que levou pra rodar o checklist.

**Dica de eficiência:** rode A primeiro (rápido, scripted). Se A
estiver muito quebrado, B e C provavelmente estão também — pare e
reporte antes de continuar perdendo tempo.
