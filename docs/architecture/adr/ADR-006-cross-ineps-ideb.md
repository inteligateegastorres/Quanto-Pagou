# ADR-006 — Cross com INEP/IDEB (gasto educacional vs desempenho)

**Status:** Proposto (esboço — não implementado)
**Data:** 2026-05-11
**Relacionado:** ADR-001 (progressive correctness), PLANO §13.8 (comparação por escola revisitada)

## Contexto

Análise externa de 2026-05-11 apontou que cruzar **gasto educacional
municipal × resultado educacional (IDEB)** é uma das ferramentas
cívicas de maior impacto. Exemplo: "Curitiba gasta X por aluno em
merenda; cidade vizinha gasta metade e tem IDEB maior".

Esse tipo de comparação só é honesta quando:

- Denominador correto (matrículas, não população).
- Categorização correta do gasto (cluster `merenda_escolar` ≠ `material_escolar` ≠ `transporte_escolar`).
- Mesmo período (ano letivo do IDEB vs ano de gasto).
- Mesmo porte de município (comparação de pares).

## Fonte INEP

INEP publica anualmente:

- **IDEB por escola** (CSV/XLSX em `inep.gov.br/web/guest/educacao-basica/ideb`):
  - `co_municipio` (cd_ibge 7 dígitos)
  - `co_entidade` (cod_escola INEP)
  - `nu_etapa` (1=anos iniciais, 2=anos finais, 3=ensino médio)
  - `ideb` (nota; 0-10)
  - `meta_ideb` (meta projetada para o município/escola)
- **Censo Escolar** (matrículas):
  - `co_entidade`, `co_municipio`, `qt_mat_*` (matrículas por etapa)
- **Publicação bienal** (anos pares: 2017, 2019, 2021, 2023…).

Sem API REST oficial; download é CSV mensal-anual via portal. Aceita
script `scripts/load_ideb.py` análogo a `load_ibge_populacao.py`.

## Proposta de schema

```sql
CREATE TABLE analytics.ideb_municipio (
    cd_ibge        TEXT,
    ano            INTEGER,
    etapa          TEXT CHECK (etapa IN ('anos_iniciais', 'anos_finais', 'medio')),
    ideb           NUMERIC(3,1),
    meta           NUMERIC(3,1),
    n_escolas      INTEGER,
    fonte          TEXT NOT NULL DEFAULT 'inep_municipal_AAAA',
    PRIMARY KEY (cd_ibge, ano, etapa)
);

CREATE TABLE analytics.matriculas_municipio (
    cd_ibge        TEXT,
    ano            INTEGER,
    etapa          TEXT,
    n_matriculas   INTEGER,
    fonte          TEXT NOT NULL DEFAULT 'inep_censo_AAAA',
    PRIMARY KEY (cd_ibge, ano, etapa)
);
```

## Proposta de MV

```sql
CREATE MATERIALIZED VIEW analytics.gasto_educacional_municipio AS
SELECT
    mp.cd_ibge,
    mp.nome AS municipio,
    mp.porte,
    EXTRACT(YEAR FROM rc.contract_date)::int AS ano,
    ic.cluster_id,
    COUNT(*) AS n_contratos,
    SUM(rc.valor_total) AS total_gasto,
    matr.n_matriculas,
    (SUM(rc.valor_total) / NULLIF(matr.n_matriculas, 0))::numeric(20,2) AS gasto_por_aluno,
    ideb.ideb
FROM raw.compras rc
JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
JOIN analytics.municipio_pr mp ON mp.cd_tce = rc.raw_payload->>'cd_tce'
LEFT JOIN analytics.matriculas_municipio matr
    ON matr.cd_ibge = mp.cd_ibge
   AND matr.ano = EXTRACT(YEAR FROM rc.contract_date)::int
LEFT JOIN analytics.ideb_municipio ideb
    ON ideb.cd_ibge = mp.cd_ibge
   AND ideb.ano = EXTRACT(YEAR FROM rc.contract_date)::int
WHERE rc.source = 'tce_pr/contrato'
  AND ic.eliminada_em IS NULL
  AND ic.cluster_id IN ('merenda_escolar', 'material_escolar',
                        'transporte_escolar', 'obras_edificacao_escolar')
GROUP BY mp.cd_ibge, mp.nome, mp.porte, ano, ic.cluster_id,
         matr.n_matriculas, ideb.ideb;
```

## Limites conhecidos

- **IDEB é bienal e atrasado** (2023 publicado em 2024). Gasto de 2025
  não tem IDEB correspondente ainda.
- **IDEB é por etapa, não por cluster orçamentário**. Cruzamento direto
  "merenda 2023 × IDEB 2023 anos iniciais" mistura efeitos (a merenda
  alimenta todas as etapas; o IDEB mede etapa específica).
- **Causalidade não está garantida**. Gastar mais não causa IDEB mais
  alto. UI deve mostrar correlação com aviso.
- **Catálogo de obras escolares (PLANO §13.8)** já está parcial em
  `analytics.escola_mencao` (regex em descrição). Não substitui
  comparação per-aluno municipal — complementa.

## Caminho de implementação (estimativa)

1. **L.19.5.a** — script `scripts/load_ideb.py` baixa CSV INEP do
   último biênio publicado. 4h.
2. **L.19.5.b** — script `scripts/load_matriculas.py` análogo. 4h.
3. **L.19.5.c** — `sql/0NN_ideb_cross.sql` com schema + MV. 2h.
4. **L.19.5.d** — endpoint `/comparar/educacional?cd_ibge=X&cluster=merenda_escolar`
   + página `/comparar/educacional` no frontend. 4h.

Total: ~2 dias úteis. Não cabe nesta entrega — fica como roadmap
documentado.

## Alternativas consideradas

- **Implementar agora**: rejeitado — escopo maior que justificaria
  bloqueio dos outros 4 itens da §19. Roadmap mais valioso que
  half-implementation.
- **Não fazer nunca**: rejeitado — análise externa identificou
  corretamente como feature de alto impacto cívico; estado atual já
  tem 80% da infra (cobertura cluster `merenda_escolar`, marts
  municipais, comparação entre municípios).
- **Comparação por escola individual**: explicitamente adiada em
  PLANO §13.8 (probe mostrou que dado não está no texto). Manter como
  decisão.

## Consequências esperadas (se/quando implementar)

**Positivas:**

- Pressão pública baseada em evidência ("Curitiba gasta R$ X por
  aluno em merenda × cidade Y gasta metade e tem IDEB maior").
- Ferramenta de monitoria educacional municipal — segmento sub-servido
  no ecossistema brasileiro de transparência.

**Negativas / aceitas:**

- Risco de leitura errada (causalidade ≠ correlação). UI precisa de
  modal "como interpretar" similar ao /metodologia.
- Manutenção: INEP atualiza bienalmente; matrículas anualmente. Cron
  separado.

## Referências

- PLANO §13.8 (comparação por escola — adiada).
- `analytics.escola_mencao` (catálogo via regex, complementar).
- `analytics.municipio_pr` (cd_ibge ↔ cd_tce já mapeado).
