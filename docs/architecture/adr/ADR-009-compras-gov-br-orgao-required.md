# ADR-009 — Compras.gov.br /modulo-contratos exige codigoOrgao: adaptação por loop por órgão

**Status:** Aceito + parcialmente implementado (L.19.11.a + L.19.11.b)
**Data:** 2026-05-18
**Relacionado:** ADR-001 (progressive correctness), PLANO §19.11

## Contexto

Em 2026-05-18, tentando rodar `scripts/sync_compras.ps1` para um sync
de rotina, descobrimos que **toda chamada à API retornava 404 "Resource
not found"**. Probes confirmaram que o endpoint
`/modulo-contratos/2_consultarContratosItem` em
`https://dadosabertos.compras.gov.br` passou a exigir o parâmetro
`codigoOrgao` como **obrigatório** — uma mudança de contrato que o
upstream não anunciou.

Evidências:

| Probe | Resultado |
|---|---|
| `GET /modulo-contratos/2_consultarContratosItem?dataVigenciaInicialMin=...&dataVigenciaInicialMax=...` | **404 "Resource not found"** |
| Swagger (`/v3/api-docs`) | `codigoOrgao required=true` |
| Mesma URL + `codigoOrgao=26298` (FNDE) | **200**, 10 itens em abril/2026 |
| `/modulo-uasg/2_consultarOrgao?statusOrgao=true` | 11.162 órgãos em 23 páginas |

Não é instabilidade transitória do backend JPA (que motivou o
window-splitting recursivo já existente). É mudança de contrato
definitiva. Sem ela, o pipeline federal congela e o banco regride ao
fixture sintético + TCE-PR.

## Decisão

Adaptar o spider em duas camadas:

1. **Cadastro de órgãos** (L.19.11.a) — novo spider em
   `src/ingest/compras_orgaos.py` consome
   `/modulo-uasg/2_consultarOrgao?statusOrgao=true` e materializa
   `analytics.orgao_federal` com upsert idempotente por `codigo_orgao`.
   Tabela serve como **tabela-de-loop** para o spider de contratos.

2. **Loop por órgão no spider de contratos** (L.19.11.b) — refatorar
   `_iter_pages`, `ingest()`, `ingest_with_split()` e
   `_ingest_window_recursive()` em `src/ingest/compras.py` para exigir
   `codigo_orgao` como argumento kw-only. Novo `ingest_by_orgaos(...)`
   recebe uma lista de códigos e chama `ingest_with_split` por órgão.
   Window-splitting de data continua aplicando, agora **por órgão** —
   falha transitória em um órgão não afeta os outros.

CLI ganha `--orgaos {all|N,N,N}` (obrigatório em modo live) e
`--orgaos-limit N` para smoke tests. `snapshot_id` recebe sufixo
`_orgao{N}` para evitar colisão.

## Filtro de esfera: descoberta que simplificou o desenho

Quando rodamos o sync completo do cadastro de órgãos, **descobrimos
que o /modulo-uasg devolve órgãos de todas as esferas, não apenas
federais:**

| Esfera × Poder | Total |
|---|---|
| Municipal (Executivo) | 7.065 |
| Estadual (Executivo) | 2.456 |
| **Federal (Executivo)** | **1.117** |
| Federal (Legislativo) | 10 |
| Outros | 514 |
| **Total** | **11.162** |

Como o Compras.gov.br federal só faz sentido para órgãos federais (os
estaduais já vêm via TCE-PR; municipais não pertencem ao escopo), o
filtro natural é `esfera='F' AND status_ativo=TRUE` → **1.134 órgãos
ativos**. Isso é tratável de varrer **por inteiro**, sem heurística
top-N.

Implementado em `load_orgaos_ativos_federais()` (compras.py).

## Alternativas consideradas

| Alternativa | Por que descartada |
|---|---|
| **Top-N heurístico** (200 órgãos com "ministerio/fundo/universidade" no nome) — proposta original em PLANO §19.11.c | Desnecessária. Federais ativos são 1.134, não 11k. Cobertura completa cabe num sync, sem viés de seleção. |
| **Paralelização imediata** (httpx async) | Postergada. Primeiro provar o caminho síncrono funciona; otimizar depois com dados de tempo real. |
| **Abandonar fonte federal** | Inviável. É a única fonte estruturada de contratos federais; perder isso reduz o projeto a estadual+municipal-PR. |
| **Esperar upstream voltar** | Não é regressão temporária; é mudança de contrato. Esperar = projeto congelado indefinidamente. |
| **Manter spider em fallback fixture** | Já é o estado atual e não escala — fixture tem 90 contratos sintéticos. Manchete federal hoje vem desse pool. |

## Consequências

**Positivas:**
- Pipeline federal volta a funcionar contra a API real.
- Cada órgão tem snapshot isolado (`_orgao{N}` no ID) — falha de um
  não corrompe os outros e facilita debug.
- `analytics.orgao_federal` é uma fonte de dados nova útil por si só
  (cruzamento com fornecedor, ranking, etc).
- Atribuição de `FailedWindow` e `IngestResult` por órgão facilita
  observabilidade (qual órgão deu ruim? qual venceu o split? etc.).

**Negativas:**
- **Custo operacional sobe ~10x.** Antes: 1 sync = 1 janela × N páginas
  (~30s típicos). Agora: 1 sync = 1.134 órgãos × ~15s/órgão (incluindo
  órgãos vazios) = ~4-5h. Não bloqueia funcionalidade, mas bloqueia
  cron horário/diário. Mitigação adiada para L.19.11.g (paralelização
  e/ou cache de órgão dormente).
- **Throttle por IP** é risco em varredura de 1.134 órgãos
  consecutivos. Tenacity tem backoff, mas backoff por backoff custa
  tempo. Mitigação: observar em sync real, adicionar rate-limit
  consciente se aparecer.
- **Cadastro de órgãos pode mudar.** Mensal/anual. Refresh é
  idempotente (`python -m ingest orgaos`), mas precisa entrar no cron
  (~30s). Mitigação: adicionar ao mesmo cron do sync_compras.

**Mudança de signature (breaking):**
- `ingest()`, `ingest_with_split()`, `_iter_pages()`, `_persist_pages()`
  agora exigem `codigo_orgao` kw-only no modo live. Fixture mode
  permanece sem `codigo_orgao` (compatível com payloads pré-quebra).
- CLI: `python -m ingest <start> <end>` agora exige `--orgaos`. Sem
  flag, retorna exit 2 com mensagem explicativa.

## Como testar

```bash
# 1. popular o cadastro de orgaos (idempotente)
python -m ingest orgaos

# 2. smoke test: 3 orgaos, 2 paginas/janela
python -m ingest 2026-04-01 2026-04-30 --orgaos "26298,20000,22000" --max-pages 2

# 3. sync completo (vai demorar)
python -m ingest 2026-05-11 2026-05-18 --orgaos all

# 4. smoke do CLI
python -m ingest 2026-05-11 2026-05-18 --orgaos all --orgaos-limit 5
```

## Histórico

- 2026-05-18 14:30 BRT — descoberta do 404, probes confirmando contrato
  novo. Documentado em PLANO §19.11 (commit `46e1ef2`).
- 2026-05-18 ~14:35 BRT — L.19.11.a implementado (commit `b15fb48`):
  spider de órgãos + migration `sql/014_orgao_federal.sql`.
- 2026-05-18 ~14:42 BRT — sync completo do cadastro: 11.162 órgãos em
  31.2s, dos quais 1.134 federais ativos.
- 2026-05-18 ~14:55 BRT — L.19.11.b implementado (commit `e8ee1c2`):
  loop por órgão, CLI `--orgaos`, snapshot `_orgao{N}`, scripts
  atualizados, 51 testes verdes.
- 2026-05-18 ~15:00 BRT — este ADR.

## Próximos passos abertos

- **L.19.11.g (não estimado)** — otimização operacional do varredura
  full (httpx async, ou pool de threads, ou cache de "órgão dormente"
  com `last_seen_with_data`). Adicional, não bloqueia funcionalidade.
- **Refresh de cadastro de órgãos** — adicionar `python -m ingest
  orgaos` ao mesmo cron do sync_compras (ou um cron mensal separado).
- **Observação em sync real** — rodar 1 sync completo e medir tempo
  por órgão p50/p90/p99, taxa de timeout, evidência (se houver) de
  rate-limit.
