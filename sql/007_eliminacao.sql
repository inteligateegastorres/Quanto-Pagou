-- LGPD art. 18 IV — direito de eliminacao via tombstones (PLANO §18 L.1).
--
-- Resolve achado 1.6 do parecer juridico: imutabilidade absoluta dos
-- snapshots conflita com direito de eliminacao do titular.
--
-- Design:
--   - raw.snapshots e raw.compras NUNCA mudam (integridade da fonte
--     primaria + auditoria)
--   - analytics.eliminacao registra solicitacao atendida (raw_id +
--     motivo + fundamento legal + data + ator)
--   - analytics.item_canonical ganha coluna eliminada_em (NULL = ativa)
--   - Todas as 5 MVs filtram WHERE eliminada_em IS NULL
--   - Endpoint /contrato/{raw_id} retorna 410 Gone se eliminado
--   - Endpoint /eliminacoes/publicas lista IDs eliminados + motivo
--     (transparencia: o que foi eliminado e por que, sem reproduzir
--     o conteudo)

-- ---------------------------------------------------------------------------
-- 1. Tabela de eliminacoes (LGPD art. 37 — registro de operacoes tambem)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.eliminacao (
    raw_id            BIGINT PRIMARY KEY REFERENCES raw.compras(id),
    eliminada_em      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    motivo            TEXT NOT NULL,           -- ex: "Solicitacao do titular via /correcoes#42"
    fundamento_legal  TEXT NOT NULL,           -- ex: "LGPD art. 18, IV (eliminacao)"
    ator              TEXT NOT NULL,           -- ex: "dpo@quantopagou.org" ou "ticket-42"
    ticket_ref        TEXT                     -- referencia ao ticket /correcoes ou processo
);

CREATE INDEX IF NOT EXISTS idx_eliminacao_data
    ON analytics.eliminacao (eliminada_em DESC);

COMMENT ON TABLE analytics.eliminacao IS
    'Registro append-only de eliminacoes atendidas (LGPD art. 18 IV). raw.snapshots e raw.compras permanecem (integridade da fonte primaria); analytics.item_canonical e MVs filtram pelo raw_id presente aqui.';

-- ---------------------------------------------------------------------------
-- 2. Coluna eliminada_em em item_canonical (NULL = ativa)
-- ---------------------------------------------------------------------------
ALTER TABLE analytics.item_canonical
    ADD COLUMN IF NOT EXISTS eliminada_em TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_item_canon_eliminacao
    ON analytics.item_canonical (eliminada_em)
    WHERE eliminada_em IS NULL;

COMMENT ON COLUMN analytics.item_canonical.eliminada_em IS
    'Timestamp de eliminacao (LGPD art. 18 IV). NULL = ativo. Sincronizado com analytics.eliminacao no build_marts e via trigger pos-insert.';

-- ---------------------------------------------------------------------------
-- 3. Trigger: ao inserir em analytics.eliminacao, marca item_canonical
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION analytics.fn_sync_eliminacao()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE analytics.item_canonical
       SET eliminada_em = NEW.eliminada_em
     WHERE raw_id = NEW.raw_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_eliminacao ON analytics.eliminacao;
CREATE TRIGGER trg_sync_eliminacao
    AFTER INSERT ON analytics.eliminacao
    FOR EACH ROW
    EXECUTE FUNCTION analytics.fn_sync_eliminacao();

-- ---------------------------------------------------------------------------
-- 4. Recriar as 5 MVs com filtro AND eliminada_em IS NULL
--
-- Justificativa do DROP+CREATE: estamos MUDANDO a definicao da MV (filtro
-- novo). Migrations anteriores usam CREATE IF NOT EXISTS pra preservar
-- estado entre dev_up runs (PLANO §17.A.8); pra mudancas de schema
-- precisa DROP explicito, conforme documentado.
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
  AND ic.eliminada_em IS NULL
  AND ic.valor_unitario_normalizado IS NOT NULL
  AND ic.confianca_resolucao >= 0.75
GROUP BY 1, 2, 3, 4, 5;

CREATE UNIQUE INDEX idx_mart_pares_pk
    ON analytics.mart_pares (cluster_id, cluster_version, ente_nivel, uf, porte);


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
  AND ic.eliminada_em IS NULL
  AND ic.valor_unitario_normalizado IS NOT NULL
  AND ic.confianca_resolucao >= 0.75
GROUP BY 1, 2, 3, 4;

CREATE UNIQUE INDEX idx_mart_orgao_cluster_pk
    ON analytics.mart_orgao_cluster (cluster_id, cluster_version, orgao_codigo);


DROP MATERIALIZED VIEW IF EXISTS analytics.mart_contratos_municipio CASCADE;
CREATE MATERIALIZED VIEW analytics.mart_contratos_municipio AS
SELECT
    ic.cluster_id,
    ic.cluster_version,
    mp.cd_ibge                                          AS cd_ibge,
    COALESCE(mp.nome, rc.raw_payload->>'municipio')     AS municipio,
    COALESCE(mp.porte, 'municipio_pr_pequeno')          AS porte,
    rc.orgao_codigo,
    rc.orgao_nome,
    COUNT(*)                                            AS n_contratos,
    ROUND(SUM(rc.valor_total)::numeric, 2)              AS valor_total_periodo,
    ROUND(percentile_cont(0.5) WITHIN GROUP (
        ORDER BY rc.valor_total)::numeric, 2)           AS mediana_valor_contrato,
    ROUND(percentile_cont(0.25) WITHIN GROUP (
        ORDER BY rc.valor_total)::numeric, 2)           AS p25_valor,
    ROUND(percentile_cont(0.75) WITHIN GROUP (
        ORDER BY rc.valor_total)::numeric, 2)           AS p75_valor,
    NOW()                                               AS atualizado_em
FROM analytics.item_canonical ic
JOIN raw.compras rc ON rc.id = ic.raw_id
LEFT JOIN analytics.municipio_pr mp
    ON mp.cd_tce = rc.raw_payload->>'cd_tce'
WHERE rc.source = 'tce_pr/contrato'
  AND ic.em_quarentena = FALSE
  AND ic.eliminada_em IS NULL
  AND ic.confianca_resolucao >= 0.5
GROUP BY 1, 2, 3, 4, 5, 6, 7;

CREATE UNIQUE INDEX idx_mart_contratos_municipio_pk
    ON analytics.mart_contratos_municipio (
        cluster_id, cluster_version, cd_ibge, orgao_codigo
    );


-- mart_fornecedores_municipio NAO faz JOIN com item_canonical (le direto
-- raw.compras pra cobrir tambem itens em quarentena). Pra respeitar
-- eliminacao, faz LEFT JOIN com analytics.eliminacao e filtra.
DROP MATERIALIZED VIEW IF EXISTS analytics.mart_fornecedores_municipio CASCADE;
CREATE MATERIALIZED VIEW analytics.mart_fornecedores_municipio AS
SELECT
    mp.cd_ibge                                          AS cd_ibge,
    COALESCE(mp.nome, rc.raw_payload->>'municipio')     AS municipio,
    rc.fornecedor_cnpj,
    rc.fornecedor_nome,
    COUNT(*)                                            AS n_contratos,
    ROUND(SUM(rc.valor_total)::numeric, 2)              AS valor_total_periodo,
    COUNT(DISTINCT rc.orgao_codigo)                     AS n_orgaos_distintos,
    NOW()                                               AS atualizado_em
FROM raw.compras rc
LEFT JOIN analytics.municipio_pr mp
    ON mp.cd_tce = rc.raw_payload->>'cd_tce'
LEFT JOIN analytics.eliminacao el ON el.raw_id = rc.id
WHERE rc.source = 'tce_pr/contrato'
  AND rc.fornecedor_cnpj IS NOT NULL
  AND el.raw_id IS NULL
GROUP BY 1, 2, 3, 4;

CREATE UNIQUE INDEX idx_mart_fornecedores_municipio_pk
    ON analytics.mart_fornecedores_municipio (cd_ibge, fornecedor_cnpj, fornecedor_nome);


-- cluster_discrepancias: usa item_canonical como base; basta adicionar
-- AND ic.eliminada_em IS NULL no WHERE da CTE base.
DROP MATERIALIZED VIEW IF EXISTS analytics.cluster_discrepancias CASCADE;
CREATE MATERIALIZED VIEW analytics.cluster_discrepancias AS
WITH ref AS (
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
      AND ic.eliminada_em IS NULL                  -- LGPD art. 18 IV
      AND ic.confianca_resolucao >= 0.6
      AND rc.valor_total > 0
      AND COALESCE(rc.orgao_nome, '') !~* 'cons[óo]rcio|consud|conims'
      AND rc.descricao !~* 'cons[óo]rcio|consud|conims'
),
cluster_stats AS (
    SELECT
        cluster_id, cluster_version,
        COUNT(*) AS n_cluster,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY valor)::numeric AS med_cluster,
        percentile_cont(0.25) WITHIN GROUP (ORDER BY valor)::numeric AS p25_cluster,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY valor)::numeric AS p75_cluster,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY valor)
            FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '90 days')::numeric AS med_cluster_90d,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY valor)
            FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '180 days')::numeric AS med_cluster_180d,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY valor)
            FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '365 days')::numeric AS med_cluster_365d,
        (SELECT SUM(s*s) FROM (SELECT COUNT(*)::numeric / NULLIF(SUM(COUNT(*)) OVER (), 0) AS s
            FROM base b2 WHERE b2.cluster_id = b.cluster_id GROUP BY COALESCE(b2.modalidade, 'sem')) sub) AS hhi_modalidade,
        (SELECT SUM(s*s) FROM (SELECT COUNT(*)::numeric / NULLIF(SUM(COUNT(*)) OVER (), 0) AS s
            FROM base b2 WHERE b2.cluster_id = b.cluster_id AND b2.fornecedor_cnpj IS NOT NULL
            GROUP BY b2.fornecedor_cnpj) sub) AS hhi_fornecedor,
        (COUNT(DISTINCT mes)::numeric / 12.0) AS spread_temporal
    FROM base b
    GROUP BY cluster_id, cluster_version
),
sujeito_stats AS (
    SELECT
        cluster_id, cluster_version, cd_tce,
        COUNT(*) AS n_sujeito,
        SUM(valor) AS valor_total_sujeito,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY valor)::numeric AS med_sujeito,
        percentile_cont(0.25) WITHIN GROUP (ORDER BY valor)::numeric AS p25_sujeito,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY valor)::numeric AS p75_sujeito,
        MAX(valor) AS max_sujeito,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY valor)
            FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '90 days')::numeric AS med_sujeito_90d,
        COUNT(*) FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '90 days') AS n_sujeito_90d,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY valor)
            FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '180 days')::numeric AS med_sujeito_180d,
        COUNT(*) FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '180 days') AS n_sujeito_180d,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY valor)
            FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '365 days')::numeric AS med_sujeito_365d,
        COUNT(*) FILTER (WHERE contract_date >= (SELECT max_date FROM ref) - INTERVAL '365 days') AS n_sujeito_365d
    FROM base
    GROUP BY cluster_id, cluster_version, cd_tce
)
SELECT
    s.cluster_id, s.cluster_version, s.cd_tce,
    s.n_sujeito, s.valor_total_sujeito, s.med_sujeito, s.p25_sujeito, s.p75_sujeito, s.max_sujeito,
    (s.med_sujeito / NULLIF(c.med_cluster, 0))               AS spread,
    (s.p75_sujeito / NULLIF(s.p25_sujeito, 0))               AS iqr_sujeito,
    c.n_cluster, c.med_cluster, c.p25_cluster, c.p75_cluster,
    (c.p75_cluster / NULLIF(c.p25_cluster, 0))               AS iqr_cluster,
    c.hhi_modalidade, c.hhi_fornecedor, c.spread_temporal,
    POWER(c.hhi_modalidade * (1 - c.hhi_fornecedor) * c.spread_temporal, 1.0/3.0) AS comparab_proxy,
    s.med_sujeito_90d, s.med_sujeito_180d, s.med_sujeito_365d,
    s.n_sujeito_90d, s.n_sujeito_180d, s.n_sujeito_365d,
    c.med_cluster_90d, c.med_cluster_180d, c.med_cluster_365d,
    (s.med_sujeito_90d  / NULLIF(c.med_cluster_90d, 0))      AS spread_90d,
    (s.med_sujeito_180d / NULLIF(c.med_cluster_180d, 0))     AS spread_180d,
    (s.med_sujeito_365d / NULLIF(c.med_cluster_365d, 0))     AS spread_365d,
    NOW()                                                    AS calculado_em
FROM sujeito_stats s
JOIN cluster_stats c
  ON c.cluster_id = s.cluster_id AND c.cluster_version = s.cluster_version;

CREATE UNIQUE INDEX idx_cluster_discrep_pk
    ON analytics.cluster_discrepancias (cluster_id, cluster_version, cd_tce);

CREATE INDEX idx_cluster_discrep_spread
    ON analytics.cluster_discrepancias (spread DESC);
