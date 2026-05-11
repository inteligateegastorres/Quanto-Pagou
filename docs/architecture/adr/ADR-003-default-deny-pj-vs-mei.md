# ADR-003 — Default deny para distinção PJ vs MEI/EI

**Status:** Aceito
**Data:** 2026-05-11
**Relacionado:** ADR-001 (progressive correctness), ADR-002 (defesa em camadas)

## Contexto

CNPJ de Microempreendedor Individual (MEI) e de Empresário Individual
(EI) é tecnicamente dado pessoal: a personalidade jurídica é fictícia,
o titular real é a pessoa física (mesmo CPF, mesmo endereço
residencial). Publicar histórico agregado e perfil público de um
"fornecedor" que é MEI/EI = expor PF disfarçada.

Não há padrão de CNPJ que identifique MEI ou EI deterministicamente —
o tipo jurídico vem dos cadastros da Receita Federal.

Caminhos disponíveis para popular o tipo jurídico:

| Opção | Custo | Cobertura | Janela de UX dark |
|---|---|---|---|
| **A. Dump RFB CNPJ aberto** | ~5 GB compactado, ETL chato, mensal | Autoritativo | 2-3 dias de UX inteiramente dark até primeira carga |
| **B. API rate-limited (ReceitaWS/BrasilAPI)** | Latência alta, quotas | ~100% | Idem |
| **C. Heurística por sufixo do nome** (LTDA, S.A., EIRELI, etc.) | Zero | ~58% (medido) | Imediata |
| **D. Sem distinção, manter status quo** | Zero | 0% | — |

## Decisão

Implementar **default deny + heurística por sufixo conservadora (C)
como fonte v1**, com fonte versionada permitindo dump RFB (A) substituir
depois.

Concretamente:

- Tabela `analytics.fornecedor(cnpj, nome_normalizado, tipo_juridico,
  fonte, classificado_em)`.
- Função `fn_classificar_tipo_juridico` retorna `'PJ'` apenas quando o
  nome contém sufixo **inequívoco** de PJ: `LTDA`, `S.A.`/`S/A`,
  `EIRELI`, `SOCIEDADE ANÔNIMA`, `COOPERATIVA`, `ASSOCIAÇÃO`,
  `FUNDAÇÃO`, `INSTITUTO`, `FEDERAÇÃO`, `SINDICATO`, `IGREJA`,
  `HOSPITAL`, `UNIVERSIDADE`, `MUNICÍPIO`, `PREFEITURA`, `UNIÃO`,
  `ESTADO`. Qualquer outro caso fica `NULL`.
- `ME`/`EPP` isolados **não** marcam PJ — ambíguos com MEI.
- Helper `_require_pj_or_404(conn, cnpj)` em `src/api/main.py`:
  endpoint `/fornecedor/{cnpj}` e os 5 derivados (`/por-orgao`,
  `/por-municipio`, `/por-categoria`, `/por-modalidade`, `/contratos`)
  retornam 404 quando `tipo_juridico != 'PJ'`.
- MV `mart_fornecedores_municipio` filtra `tipo_juridico = 'PJ'` na
  origem (defesa em camadas — se algum endpoint esquecer o helper, a
  MV já não tem MEI/EI).
- Listagem `/fornecedores` faz JOIN com `analytics.fornecedor`
  filtrando PJ.
- Frontend `/fornecedor/[cnpj]` substitui `notFound()` genérico por
  componente `PerfilIndisponivel` que distingue causa ("menos de 5
  contratos" vs "tipo jurídico não confirmado") e dá gancho para
  `/correcoes` com tipo `classificacao_pj` (L.12).
- Coluna `fonte` versionada: `heuristica_sufixo_v1` agora; dump RFB
  futuro grava `rfb_dump_AAAA-MM`. `fn_enriquecer_fornecedor` só
  sobrescreve fonte que começa com `heuristica%` — dump RFB nunca é
  reescrito por heurística.

## Resultado medido (primeira carga, 2026-05-11)

- 38.686 fornecedores únicos em `raw.compras`.
- **22.409 PJ confirmados (58%)** — perfil público disponível.
- **16.277 NULL (42%)** — mascarados por default deny.
- MV `mart_fornecedores_municipio` reduzida de ~120k para 81.3k linhas
  com o filtro PJ + tombstones.

## Alternativas consideradas

Tabela acima. Pontos-chave:

- **Dump RFB agora (A)**: atrasa UX em 2-3 dias só para ingestão,
  enquanto ETL do dump tem armadilhas próprias (frequência mensal,
  schema versionado). Decidimos atrasar pra v2.
- **Heurística pura sem default deny (C sem deny)**: deixa qualquer
  CNPJ sem sufixo legível público — falha em ~42% dos casos.
  Inaceitável.
- **Sem distinção (D)**: parecer jurídico explicitamente apontou
  como gap crítico. Inaceitável.

## Consequências

**Positivas:**

- Defesa em camadas honesta: 58% confirmado, 42% mascarado.
  Reportador pode pedir verificação em `/correcoes` se acredita que é
  PJ legítimo (tipo `classificacao_pj`, SLA 15d).
- Não bloqueia produto durante implementação da v2 (dump RFB).
- Migration path para v2 é zero — basta correr o job RFB e sobrescrever
  rows com `fonte LIKE 'heuristica%'`.

**Negativas / aceitas:**

- Falso negativo (~42%): PJs legítimas sem sufixo no nome ficam
  mascaradas. Mitigado pelo canal `/correcoes` com SLA 15d.
- Falso positivo possível mas residual: sufixo `LTDA` é restrito por
  lei (Lei 10.406/2002 art. 1.052+); MEI não pode usar legalmente.
- Heurística não cobre fornecedor estrangeiro (sem CNPJ típico).
  Aceitável pra fase atual (foco PR/Compras federal).

## Referências

- `sql/009_fornecedor.sql`, `sql/010_l2b_mart_pj.sql`.
- Endpoint helper: `src/api/main.py` (`_require_pj_or_404`).
- Frontend: `frontend/app/fornecedor/[cnpj]/page.tsx`
  (`PerfilIndisponivel`).
- PLANO §18 L.2 e L.2.b, §14 changelog v5.5/v5.6.
