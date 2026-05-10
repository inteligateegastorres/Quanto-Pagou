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
-- Idempotente. Para evoluir schema, criar migration nova que faz DROP antes.
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.cluster_discrepancias AS
WITH ref AS (
    -- Data de referencia para janelas temporais = MAX(contract_date) do
    -- snapshot atual. NAO usa NOW() porque o snapshot pode estar atrasado
    -- (ex: ultima ingestao foi ha 10 dias; janela de 90d com NOW() teria
    -- buraco). Vide PLANO §13.5 ponto #3 (estabilidade temporal).
    SELECT MAX(contract_date) AS max_date
    FROM raw.compras
    WHERE source = 'tce_pr/contrato' AND contract_date IS NOT NULL
),
base AS (
    SELECT
        ic.cluster_id,
        ic.cluster_version,
        rc.raw_payload->>'cd_tce'                AS cd_tce,
        rc.valor_total::numeric                  AS valor,
        rc.contract_date,
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
        -- Medianas por janela temporal (estabilidade)
        percentile_cont(0.5) WITHIN GROUP (ORDER BY valor)
            FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '90 days')
            ::numeric AS med_cluster_90d,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY valor)
            FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '180 days')
            ::numeric AS med_cluster_180d,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY valor)
            FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '365 days')
            ::numeric AS med_cluster_365d,
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
        MAX(valor)                                                        AS max_sujeito,
        -- Medianas por janela temporal (NULL se janela nao tem contratos)
        percentile_cont(0.5) WITHIN GROUP (ORDER BY valor)
            FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '90 days')
            ::numeric AS med_sujeito_90d,
        COUNT(*) FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '90 days') AS n_sujeito_90d,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY valor)
            FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '180 days')
            ::numeric AS med_sujeito_180d,
        COUNT(*) FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '180 days') AS n_sujeito_180d,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY valor)
            FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '365 days')
            ::numeric AS med_sujeito_365d,
        COUNT(*) FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '365 days') AS n_sujeito_365d
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
    -- Medianas por janela temporal (para teste de estabilidade)
    s.med_sujeito_90d,
    s.med_sujeito_180d,
    s.med_sujeito_365d,
    s.n_sujeito_90d,
    s.n_sujeito_180d,
    s.n_sujeito_365d,
    c.med_cluster_90d,
    c.med_cluster_180d,
    c.med_cluster_365d,
    -- Spreads por janela (NULL se janela nao tem dados suficientes).
    -- Filtro de estabilidade (>=N janelas com spread acima do limiar) acontece
    -- em manchetes.py; aqui e so disponibilizar os 3 valores.
    (s.med_sujeito_90d  / NULLIF(c.med_cluster_90d, 0))      AS spread_90d,
    (s.med_sujeito_180d / NULLIF(c.med_cluster_180d, 0))     AS spread_180d,
    (s.med_sujeito_365d / NULLIF(c.med_cluster_365d, 0))     AS spread_365d,
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

    -- Estabilidade temporal (spreads em 3 janelas; NULL se janela vazia)
    spread_90d           NUMERIC,
    spread_180d          NUMERIC,
    spread_365d          NUMERIC,
    janelas_passadas     INT NOT NULL DEFAULT 0,    -- quantas das 3 janelas passaram spread_min

    -- Score do ranker (ln(volume) * ln(spread) * comparab)
    rank_score           NUMERIC NOT NULL,
    rank_no_dia          INT NOT NULL,

    -- Metadados
    parametros_hash      TEXT NOT NULL,
    refresh_em           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Adicionar colunas se tabela ja existia (migration idempotente).
ALTER TABLE analytics.manchete ADD COLUMN IF NOT EXISTS spread_90d        NUMERIC;
ALTER TABLE analytics.manchete ADD COLUMN IF NOT EXISTS spread_180d       NUMERIC;
ALTER TABLE analytics.manchete ADD COLUMN IF NOT EXISTS spread_365d       NUMERIC;
ALTER TABLE analytics.manchete ADD COLUMN IF NOT EXISTS janelas_passadas  INT NOT NULL DEFAULT 0;

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


-- ---------------------------------------------------------------------------
-- Camada 3b: manchete_saida (vela apagada)
-- Registra manchetes que ESTAVAM ativas mas sairam, com motivo diagnostico.
-- "Vela apagada e tambem informacao" — credibilidade publica.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.manchete_saida (
    saiu_em             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    manchete_id         TEXT NOT NULL,
    motivo              TEXT NOT NULL,            -- ex: "spread caiu para 3.2 (limiar 5)"
    payload_anterior    JSONB NOT NULL,           -- ultima versao ativa
    parametros_hash     TEXT NOT NULL,
    PRIMARY KEY (saiu_em, manchete_id)
);

CREATE INDEX IF NOT EXISTS idx_manchete_saida_recent
    ON analytics.manchete_saida (saiu_em DESC);

COMMENT ON TABLE analytics.manchete_saida IS
    'Manchetes que sairam com motivo diagnostico. Detectadas no refresh comparando IDs ativos antes vs depois. Mostradas em /manchetes na secao "Recem-saidas".';


-- ---------------------------------------------------------------------------
-- analytics.manchete_config_aplicada
-- Snapshot do YAML aplicado em cada refresh. Permite ao backend
-- diagnosticar "por que esse municipio NAO esta em manchete?" sem ler
-- o YAML do disco (busca reversa em /manchetes).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.manchete_config_aplicada (
    parametros_hash    TEXT PRIMARY KEY,
    config_json        JSONB NOT NULL,
    primeira_aplicacao TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ultima_aplicacao   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE analytics.manchete_config_aplicada IS
    'Snapshot do YAML aplicado em cada refresh. Backend usa pra diagnosticar busca reversa ("por que esse municipio nao esta em manchete?").';
