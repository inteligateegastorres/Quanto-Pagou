-- L.19.7 — Métrica per capita first-class (PLANO §19.7).
--
-- Cruza contratos TCE-PR já canonicalizados com populacao IBGE Censo 2022
-- (analytics.municipio_pr.populacao) e expõe gasto_per_capita por
-- (municipio × cluster). Substitui o cálculo ad-hoc que hoje vive como
-- badge — agora a métrica é primária, indexada e exposta em endpoint
-- + UI dedicados.
--
-- Filtros de qualidade idênticos a mart_contratos_municipio:
--   - em_quarentena = FALSE  (item canonicalizado)
--   - eliminada_em IS NULL   (L.1 tombstone respeitado)
--   - confianca_resolucao >= 0.5
--   - populacao IS NOT NULL  (3 dos 399 municípios PR ainda sem censo)
--
-- Limite conhecido: populacao = Censo IBGE 2022. Quando vier nova edição
-- (Censo 2030 ou estimativas anuais TCU), versionar em coluna separada
-- na municipio_pr e atualizar este MV — não criar tabela "populacao_ano".
-- A simplicidade aqui é proposital (memória feedback_progressive_correctness:
-- publicar imperfeito > adiar para perfeito).
--
-- UNIQUE INDEX habilita REFRESH MATERIALIZED VIEW CONCURRENTLY (sem
-- bloquear leituras), seguindo padrão das demais MVs.

DROP MATERIALIZED VIEW IF EXISTS analytics.mart_gasto_per_capita CASCADE;
CREATE MATERIALIZED VIEW analytics.mart_gasto_per_capita AS
SELECT
    ic.cluster_id,
    ic.cluster_version,
    mp.cd_ibge,
    mp.cd_tce,
    mp.nome                                                 AS municipio,
    mp.porte,
    mp.populacao,
    COUNT(*)                                                AS n_contratos,
    ROUND(SUM(rc.valor_total)::numeric, 2)                  AS gasto_total,
    ROUND(
        (SUM(rc.valor_total) / NULLIF(mp.populacao, 0))::numeric,
        2
    )                                                       AS gasto_per_capita,
    ROUND(percentile_cont(0.5) WITHIN GROUP (
        ORDER BY rc.valor_total)::numeric, 2)               AS mediana_valor_contrato,
    NOW()                                                   AS atualizado_em
FROM analytics.item_canonical ic
JOIN raw.compras rc ON rc.id = ic.raw_id
JOIN analytics.municipio_pr mp
    ON mp.cd_tce = rc.raw_payload->>'cd_tce'
WHERE rc.source = 'tce_pr/contrato'
  AND ic.em_quarentena = FALSE
  AND ic.eliminada_em IS NULL
  AND ic.confianca_resolucao >= 0.5
  AND mp.populacao IS NOT NULL
GROUP BY ic.cluster_id, ic.cluster_version,
         mp.cd_ibge, mp.cd_tce, mp.nome, mp.porte, mp.populacao;

CREATE UNIQUE INDEX idx_mart_gasto_per_capita_pk
    ON analytics.mart_gasto_per_capita (
        cluster_id, cluster_version, cd_ibge
    );

CREATE INDEX idx_mart_gasto_per_capita_porte
    ON analytics.mart_gasto_per_capita (porte);

CREATE INDEX idx_mart_gasto_per_capita_per_capita
    ON analytics.mart_gasto_per_capita (gasto_per_capita DESC);

COMMENT ON MATERIALIZED VIEW analytics.mart_gasto_per_capita IS
    'PLANO §19.7 — gasto_per_capita por (municipio × cluster). populacao = IBGE Censo 2022. Filtra eliminacao L.1 + quarentena + baixa confianca.';
COMMENT ON COLUMN analytics.mart_gasto_per_capita.gasto_per_capita IS
    'SUM(valor_total) / populacao em R$/habitante. NULL impossível (populacao IS NOT NULL no WHERE).';
COMMENT ON COLUMN analytics.mart_gasto_per_capita.populacao IS
    'Populacao IBGE Censo 2022. Fixa — comunicada no UI como tal.';

REFRESH MATERIALIZED VIEW analytics.mart_gasto_per_capita;
