-- LGPD §19.4 — alerta de aumento progressivo trimestre a trimestre.
--
-- Detecta combinações (fornecedor_cnpj + cd_tce + cluster_id) onde a
-- mediana do valor de contrato cresceu trimestre a trimestre nos
-- últimos 3 trimestres consecutivos com dados — sinal de aumento
-- progressivo de preço que escapa do filtro IQR das manchetes (porque
-- cada trimestre, sozinho, está dentro da banda; é a tendência
-- ascendente que chama atenção).
--
-- Aplicação típica:
--   - contratos de coleta de lixo / merenda / combustível repactuados
--     a cada trimestre com IPCA + um pouco
--   - aditivos sucessivos em obra
--   - dependência de fornecedor com pressão crescente sobre preço
--
-- Threshold de crescimento por trimestre: 1.2× (= +20%). Em 2
-- trimestres consecutivos isso = ~44% acima do baseline. Mais
-- conservador que limiares de manchete (5×) — capta sinal sutil que
-- as manchetes não captam.
--
-- Defesa em camadas L.2: JOIN com analytics.fornecedor exige PJ.
-- Tombstones L.1: JOIN com item_canonical já filtra eliminada_em.

DROP MATERIALIZED VIEW IF EXISTS analytics.alerta_progressivo CASCADE;
CREATE MATERIALIZED VIEW analytics.alerta_progressivo AS
WITH trimestres AS (
    SELECT
        rc.fornecedor_cnpj,
        MAX(rc.fornecedor_nome)                                   AS fornecedor_nome,
        rc.raw_payload->>'cd_tce'                                 AS cd_tce,
        ic.cluster_id,
        DATE_TRUNC('quarter', rc.contract_date)::date             AS trimestre,
        COUNT(*)                                                  AS n,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY rc.valor_total
        )::numeric                                                AS mediana,
        ROUND(SUM(rc.valor_total)::numeric, 2)                    AS total
    FROM raw.compras rc
    JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
    JOIN analytics.fornecedor f ON f.cnpj = rc.fornecedor_cnpj
    WHERE rc.source = 'tce_pr/contrato'
      AND ic.eliminada_em IS NULL
      AND ic.em_quarentena = FALSE
      AND f.tipo_juridico = 'PJ'
      AND rc.contract_date IS NOT NULL
      AND rc.valor_total > 0
      AND rc.fornecedor_cnpj IS NOT NULL
    GROUP BY 1, 3, 4, 5
    HAVING COUNT(*) >= 2
),
sequencias AS (
    SELECT
        fornecedor_cnpj,
        MAX(fornecedor_nome)                          AS fornecedor_nome,
        cd_tce,
        cluster_id,
        array_agg(trimestre ORDER BY trimestre)        AS trimestres_arr,
        array_agg(mediana ORDER BY trimestre)          AS medianas_arr,
        array_agg(n ORDER BY trimestre)                AS n_arr,
        array_agg(total ORDER BY trimestre)            AS totais_arr,
        COUNT(*)                                       AS n_trimestres
    FROM trimestres
    GROUP BY 1, 3, 4
    HAVING COUNT(*) >= 3
)
SELECT
    s.fornecedor_cnpj,
    s.fornecedor_nome,
    s.cd_tce,
    s.cluster_id,
    s.trimestres_arr[s.n_trimestres - 2]                AS trimestre_1,
    s.trimestres_arr[s.n_trimestres - 1]                AS trimestre_2,
    s.trimestres_arr[s.n_trimestres]                    AS trimestre_3,
    s.medianas_arr[s.n_trimestres - 2]                  AS mediana_1,
    s.medianas_arr[s.n_trimestres - 1]                  AS mediana_2,
    s.medianas_arr[s.n_trimestres]                      AS mediana_3,
    ROUND((s.medianas_arr[s.n_trimestres]
           / NULLIF(s.medianas_arr[s.n_trimestres - 2], 0))::numeric, 3)
                                                        AS growth_ratio,
    s.n_arr[s.n_trimestres - 2]                         AS n_1,
    s.n_arr[s.n_trimestres - 1]                         AS n_2,
    s.n_arr[s.n_trimestres]                             AS n_3,
    s.totais_arr[s.n_trimestres - 2]                    AS total_1,
    s.totais_arr[s.n_trimestres - 1]                    AS total_2,
    s.totais_arr[s.n_trimestres]                        AS total_3,
    NOW()                                               AS calculado_em
FROM sequencias s
WHERE s.medianas_arr[s.n_trimestres - 1]
        > s.medianas_arr[s.n_trimestres - 2] * 1.2
  AND s.medianas_arr[s.n_trimestres]
        > s.medianas_arr[s.n_trimestres - 1] * 1.2;

CREATE UNIQUE INDEX idx_alerta_progressivo_pk
    ON analytics.alerta_progressivo
    (fornecedor_cnpj, cd_tce, cluster_id);

CREATE INDEX idx_alerta_progressivo_growth
    ON analytics.alerta_progressivo (growth_ratio DESC);

COMMENT ON MATERIALIZED VIEW analytics.alerta_progressivo IS
    'Alerta de aumento progressivo (PLANO §19.4): combinações (cnpj+cd_tce+cluster) onde a mediana do valor de contrato cresceu >1.2× em cada um dos 3 últimos trimestres consecutivos com dados. Defesa em camadas L.1+L.2 aplicada na origem.';

REFRESH MATERIALIZED VIEW analytics.alerta_progressivo;
