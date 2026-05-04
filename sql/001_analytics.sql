-- Quanto Pagou - schema analytics (Day 3-4).
-- Camada canonica + marts. Progressive correctness: tabelas simples, sem ndices
-- agressivos. Sofisticar quando houver volume real.

CREATE SCHEMA IF NOT EXISTS analytics;

-- ---------------------------------------------------------------------------
-- Cluster registry (versionado).
-- Historico nunca e reescrito; cluster_version inclui cada split/merge.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.cluster_registry (
    cluster_id          TEXT NOT NULL,
    cluster_version     TEXT NOT NULL,
    descricao_canonica  TEXT NOT NULL,
    categoria           TEXT NOT NULL,
    ativo               BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    mapeamento_de       TEXT,
    PRIMARY KEY (cluster_id, cluster_version)
);

COMMENT ON TABLE analytics.cluster_registry IS
    'Versionamento de clusters. Cada cluster_version captura 1 estado canonico; mudancas de modelo emitem nova versao.';

-- ---------------------------------------------------------------------------
-- Item canonico - 1:1 com raw.compras, mas com cluster_id, unidade_base e
-- valor_unitario_normalizado preenchidos pelo build_marts.
-- Itens nao resolvidos / sem unidade legivel: em_quarentena = TRUE,
-- valor_unitario_normalizado = NULL (nunca somem; ficam visiveis com label).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.item_canonical (
    raw_id                          BIGINT PRIMARY KEY REFERENCES raw.compras(id) ON DELETE CASCADE,
    cluster_id                      TEXT,
    cluster_version                 TEXT,
    metodo_resolucao                TEXT,
    confianca_resolucao             NUMERIC(3, 2),
    unidade_label                   TEXT,
    unidade_base                    TEXT,
    fator_conversao                 NUMERIC,
    valor_unitario_normalizado      NUMERIC,
    ente_nivel                      TEXT,
    uf                              TEXT,
    porte                           TEXT,
    em_quarentena                   BOOLEAN NOT NULL DEFAULT FALSE,
    motivo_quarentena               TEXT,
    resolved_at                     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_item_canon_cluster
    ON analytics.item_canonical (cluster_id, cluster_version)
    WHERE em_quarentena = FALSE;

CREATE INDEX IF NOT EXISTS idx_item_canon_quarentena
    ON analytics.item_canonical (em_quarentena, motivo_quarentena);

COMMENT ON TABLE analytics.item_canonical IS
    'Camada canonica 1:1 com raw.compras. valor_unitario_normalizado e o preco por unidade_base.';

-- ---------------------------------------------------------------------------
-- Mart 1: pares de comparacao por (cluster x uf x porte).
-- Usado pelo card narrativo: "voce pagou X; pares pagam Y; intervalo p25-p75".
-- Filtra em_quarentena, valor_unitario_normalizado nulo, confianca < 0.75.
-- ---------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS analytics.mart_pares CASCADE;
CREATE MATERIALIZED VIEW analytics.mart_pares AS
SELECT
    ic.cluster_id,
    ic.cluster_version,
    COALESCE(ic.ente_nivel, 'desconhecido')           AS ente_nivel,
    COALESCE(ic.uf, 'desconhecido')                   AS uf,
    COALESCE(ic.porte, 'desconhecido')                AS porte,
    COUNT(*)                                          AS n,
    ROUND(MIN(ic.valor_unitario_normalizado), 4)      AS minimo,
    ROUND(percentile_cont(0.25) WITHIN GROUP (
        ORDER BY ic.valor_unitario_normalizado)::numeric, 4) AS p25,
    ROUND(percentile_cont(0.5) WITHIN GROUP (
        ORDER BY ic.valor_unitario_normalizado)::numeric, 4) AS mediana,
    ROUND(percentile_cont(0.75) WITHIN GROUP (
        ORDER BY ic.valor_unitario_normalizado)::numeric, 4) AS p75,
    ROUND(MAX(ic.valor_unitario_normalizado), 4)      AS maximo,
    ROUND((percentile_cont(0.75) WITHIN GROUP (
        ORDER BY ic.valor_unitario_normalizado)
        - percentile_cont(0.25) WITHIN GROUP (
            ORDER BY ic.valor_unitario_normalizado))::numeric, 4) AS iqr,
    NOW()                                             AS atualizado_em
FROM analytics.item_canonical ic
WHERE ic.em_quarentena = FALSE
  AND ic.valor_unitario_normalizado IS NOT NULL
  AND ic.confianca_resolucao >= 0.75
GROUP BY 1, 2, 3, 4, 5;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mart_pares_pk
    ON analytics.mart_pares (cluster_id, cluster_version, ente_nivel, uf, porte);

COMMENT ON MATERIALIZED VIEW analytics.mart_pares IS
    'Mediana, p25, p75 por (cluster x ente x uf x porte). Threshold confianca >= 0.75; quarentena exclusa.';

-- ---------------------------------------------------------------------------
-- Mart 2: ranking de orgaos por cluster (gancho viral "Top orgaos federais
-- que pagam mais por X").
-- ---------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS analytics.mart_orgao_cluster CASCADE;
CREATE MATERIALIZED VIEW analytics.mart_orgao_cluster AS
SELECT
    ic.cluster_id,
    ic.cluster_version,
    rc.orgao_codigo,
    rc.orgao_nome,
    COUNT(*)                                          AS n_compras,
    ROUND(percentile_cont(0.5) WITHIN GROUP (
        ORDER BY ic.valor_unitario_normalizado)::numeric, 4) AS mediana_orgao,
    ROUND(SUM(rc.valor_total)::numeric, 2)            AS valor_total_periodo,
    NOW()                                             AS atualizado_em
FROM analytics.item_canonical ic
JOIN raw.compras rc ON rc.id = ic.raw_id
WHERE ic.em_quarentena = FALSE
  AND ic.valor_unitario_normalizado IS NOT NULL
  AND ic.confianca_resolucao >= 0.75
GROUP BY 1, 2, 3, 4;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mart_orgao_cluster_pk
    ON analytics.mart_orgao_cluster (cluster_id, cluster_version, orgao_codigo);

COMMENT ON MATERIALIZED VIEW analytics.mart_orgao_cluster IS
    'Mediana de preco por orgao x cluster. Base do ranking "Top orgaos que pagam mais por X".';

-- ---------------------------------------------------------------------------
-- View pratica: contagem de quarentena por categoria/motivo (saude do pipeline).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW analytics.v_quarentena_resumo AS
SELECT
    cr.categoria,
    ic.motivo_quarentena,
    COUNT(*) AS n
FROM analytics.item_canonical ic
LEFT JOIN analytics.cluster_registry cr
    ON cr.cluster_id = ic.cluster_id
   AND cr.cluster_version = ic.cluster_version
WHERE ic.em_quarentena = TRUE
GROUP BY 1, 2
ORDER BY 3 DESC;

COMMENT ON VIEW analytics.v_quarentena_resumo IS
    'Visibilidade de itens em quarentena - alimenta metrica publica de qualidade por categoria.';
