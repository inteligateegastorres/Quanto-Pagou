-- Manchetes (PLANO §13.5 / 14.X) - sistema algoritmico de selecao de
-- discrepancias entre municipios em clusters TCE-PR.
--
-- 3 camadas explicitamente separadas:
--   1. analytics.cluster_discrepancias   - fatos estatisticos (MV)
--   2. analytics.manchete                - selecao apos thresholds (table)
--   3. analytics.manchete_publicada      - log de auditoria (table append)
--
-- Os FATOS (1) sao caros de recomputar e refrescam junto com os outros marts.
-- A SELECAO (2) le YAML versionado e e barata de re-rodar com novos thresholds.
-- O LOG (3) registra cada refresh, permitindo "que manchete estava no ar em X?"

CREATE SCHEMA IF NOT EXISTS analytics;

-- ---------------------------------------------------------------------------
-- Camada 1: cluster_discrepancias
-- Fatos estatisticos por (cluster, municipio). Nao filtra; expoe tudo.
-- O calculo e identico ao dry-run final (perfil C calibrado em 2026-05-09).
-- ---------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS analytics.cluster_discrepancias CASCADE;

CREATE MATERIALIZED VIEW analytics.cluster_discrepancias AS
WITH base AS (
    SELECT
        ic.cluster_id,
        ic.cluster_version,
        rc.raw_payload->>'cd_tce'                AS cd_tce,
        rc.valor_total::numeric                  AS valor,
        rc.modalidade,
        rc.fornecedor_cnpj,
        EXTRACT(MONTH FROM rc.contract_date)     AS mes
    FROM raw.compras rc
    JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
    WHERE rc.source = 'tce_pr/contrato'
      AND ic.cluster_id IS NOT NULL
      AND ic.em_quarentena = FALSE
      AND ic.confianca_resolucao >= 0.6
      AND rc.valor_total > 0
      -- Trap de consorcios regionais (descoberto na exploracao 2.c
      -- medicamentos: FB e PB hospedam CONSUD/CONIMS, distorcem per capita).
      AND COALESCE(rc.orgao_nome, '') !~* 'cons[óo]rcio|consud|conims'
      AND rc.descricao !~* 'cons[óo]rcio|consud|conims'
),
cluster_stats AS (
    -- Agregados por cluster + 3 sub-scores de comparabilidade proxy.
    -- Comparabilidade v1: media geometrica de
    --   hhi_modalidade        (alto = cluster com modalidade dominante)
    --   1 - hhi_fornecedor    (baixo HHI = mercado competitivo)
    --   spread_temporal       (contratos em mais meses)
    -- Threshold de uso fica no YAML; aqui e so transparencia.
    SELECT
        cluster_id,
        cluster_version,
        COUNT(*)                                                          AS n_cluster,
        percentile_cont(0.5)  WITHIN GROUP (ORDER BY valor)::numeric      AS med_cluster,
        percentile_cont(0.25) WITHIN GROUP (ORDER BY valor)::numeric      AS p25_cluster,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY valor)::numeric      AS p75_cluster,
        (
            SELECT SUM(s*s) FROM (
                SELECT COUNT(*)::numeric / NULLIF(SUM(COUNT(*)) OVER (), 0) AS s
                FROM base b2 WHERE b2.cluster_id = b.cluster_id
                GROUP BY COALESCE(b2.modalidade, 'sem')
            ) sub
        ) AS hhi_modalidade,
        (
            SELECT SUM(s*s) FROM (
                SELECT COUNT(*)::numeric / NULLIF(SUM(COUNT(*)) OVER (), 0) AS s
                FROM base b2 WHERE b2.cluster_id = b.cluster_id
                  AND b2.fornecedor_cnpj IS NOT NULL
                GROUP BY b2.fornecedor_cnpj
            ) sub
        ) AS hhi_fornecedor,
        (COUNT(DISTINCT mes)::numeric / 12.0) AS spread_temporal
    FROM base b
    GROUP BY cluster_id, cluster_version
),
sujeito_stats AS (
    SELECT
        cluster_id,
        cluster_version,
        cd_tce,
        COUNT(*)                                                          AS n_sujeito,
        SUM(valor)                                                        AS valor_total_sujeito,
        percentile_cont(0.5)  WITHIN GROUP (ORDER BY valor)::numeric      AS med_sujeito,
        percentile_cont(0.25) WITHIN GROUP (ORDER BY valor)::numeric      AS p25_sujeito,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY valor)::numeric      AS p75_sujeito,
        MAX(valor)                                                        AS max_sujeito
    FROM base
    GROUP BY cluster_id, cluster_version, cd_tce
)
SELECT
    s.cluster_id,
    s.cluster_version,
    s.cd_tce,
    s.n_sujeito,
    s.valor_total_sujeito,
    s.med_sujeito,
    s.p25_sujeito,
    s.p75_sujeito,
    s.max_sujeito,
    -- Spread = mediana_sujeito / mediana_cluster
    (s.med_sujeito / NULLIF(c.med_cluster, 0))               AS spread,
    -- IQR ratio do sujeito (p75/p25 internos)
    (s.p75_sujeito / NULLIF(s.p25_sujeito, 0))               AS iqr_sujeito,
    -- Stats do cluster (denormalizados pra evitar JOIN no consumer)
    c.n_cluster,
    c.med_cluster,
    c.p25_cluster,
    c.p75_cluster,
    (c.p75_cluster / NULLIF(c.p25_cluster, 0))               AS iqr_cluster,
    c.hhi_modalidade,
    c.hhi_fornecedor,
    c.spread_temporal,
    -- Comparabilidade proxy v1 (media geometrica)
    POWER(
        c.hhi_modalidade
        * (1 - c.hhi_fornecedor)
        * c.spread_temporal,
        1.0/3.0
    )                                                        AS comparab_proxy,
    NOW()                                                    AS calculado_em
FROM sujeito_stats s
JOIN cluster_stats c
  ON c.cluster_id = s.cluster_id AND c.cluster_version = s.cluster_version;

CREATE UNIQUE INDEX IF NOT EXISTS idx_cluster_discrep_pk
    ON analytics.cluster_discrepancias (cluster_id, cluster_version, cd_tce);

CREATE INDEX IF NOT EXISTS idx_cluster_discrep_spread
    ON analytics.cluster_discrepancias (spread DESC);

COMMENT ON MATERIALIZED VIEW analytics.cluster_discrepancias IS
    'Camada 1: fatos estatisticos por (cluster, municipio). Nao filtra. Refresh junto com build_marts. Comparabilidade proxy v1 = media geometrica de HHI_modalidade, 1-HHI_fornecedor, spread_temporal.';


-- ---------------------------------------------------------------------------
-- Camada 2: manchete
-- Selecao apos aplicar thresholds do YAML. Repopulada por
-- python -m analytics.manchetes refresh.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.manchete (
    manchete_id          TEXT PRIMARY KEY,         -- {cluster_id}__{cd_tce}
    cluster_id           TEXT NOT NULL,
    cluster_version      TEXT NOT NULL,
    cd_tce               TEXT NOT NULL,
    cd_ibge              TEXT,
    municipio_nome       TEXT,
    porte                TEXT,
    populacao            INT,

    -- Metricas que justificam a manchete (snapshot de cluster_discrepancias)
    n_sujeito            INT NOT NULL,
    valor_total_sujeito  NUMERIC NOT NULL,
    med_sujeito          NUMERIC NOT NULL,
    med_cluster          NUMERIC NOT NULL,
    spread               NUMERIC NOT NULL,
    iqr_sujeito          NUMERIC NOT NULL,
    iqr_cluster          NUMERIC NOT NULL,
    comparab_proxy       NUMERIC NOT NULL,

    -- Score do ranker (ln(volume) * ln(spread) * comparab)
    rank_score           NUMERIC NOT NULL,
    rank_no_dia          INT NOT NULL,

    -- Metadados
    parametros_hash      TEXT NOT NULL,
    refresh_em           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_manchete_rank
    ON analytics.manchete (rank_no_dia);

COMMENT ON TABLE analytics.manchete IS
    'Camada 2: manchetes ativas selecionadas pelo YAML. Recalculada a cada refresh. Editar config/manchete_v*.yaml e rodar python -m analytics.manchetes refresh para re-tunar sem recomputar Camada 1.';


-- ---------------------------------------------------------------------------
-- Camada 3: manchete_publicada (log append-only)
-- Cada refresh gera uma linha por manchete ativa. Permite reconstruir
-- "o que estava no ar em DD/MM/YYYY?".
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.manchete_publicada (
    publicada_em         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    manchete_id          TEXT NOT NULL,
    parametros_hash      TEXT NOT NULL,
    payload_json         JSONB NOT NULL,           -- snapshot completo da manchete
    PRIMARY KEY (publicada_em, manchete_id)
);

CREATE INDEX IF NOT EXISTS idx_manchete_pub_manchete
    ON analytics.manchete_publicada (manchete_id, publicada_em DESC);

COMMENT ON TABLE analytics.manchete_publicada IS
    'Camada 3: log append-only de manchetes ja publicadas. Consulta "que manchetes estavam ativas em data X?": SELECT WHERE publicada_em = (SELECT MAX(publicada_em) WHERE publicada_em <= X). Permite auditoria temporal.';
