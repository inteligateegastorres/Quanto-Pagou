-- PLANO §19.6 — alerta de dispensa emergencial repetida.
--
-- Hipótese: combinação (fornecedor_cnpj + orgao_codigo + cd_tce) com ≥3
-- contratos em modalidade `dispensa` nos últimos 12 meses é sinal de
-- "dispensa emergencial recorrente" — caso clássico de captura de
-- fornecedor que escapa do filtro IQR das manchetes (§15) e do filtro
-- de tendência do alerta progressivo (§19.4).
--
-- Análise externa P3 mencionou explicitamente este padrão. Pré-estimativa
-- sobre o dataset atual (TCE-PR, 156k contratos): 71 sinais reais.
--
-- Threshold: 3 dispensas em 12 meses. Por construção:
--   - 1-2 dispensas/ano em mesmo CNPJ+órgão é comum (variação legítima).
--   - 3+ dispensas/ano sugere uso recorrente do mecanismo emergencial,
--     que por lei (Lei 14.133/2021) deveria ser excepcional.
--
-- Defesa em camadas (mesma de §19.4):
--   - L.1 tombstones: JOIN com item_canonical filtra eliminada_em.
--   - L.2 PJ: JOIN com analytics.fornecedor exige tipo_juridico='PJ'
--     (MEI/EI ficam fora pelo design da política).
--
-- Limite conhecido: 3 dispensas pode ter explicação legítima (calamidade
-- pública, especialização técnica, fracasso de processos anteriores). UI
-- precisa de disclaimer "não implica irregularidade" — reusa o
-- DisclaimerOrigem (L.11). Manchete não deve publicar nome de fornecedor
-- sem revisão humana (regra §15 transferida).
--
-- UNIQUE INDEX habilita REFRESH MATERIALIZED VIEW CONCURRENTLY (sem
-- bloquear leituras), padrão das demais MVs.

DROP MATERIALIZED VIEW IF EXISTS analytics.alerta_dispensa_repetida CASCADE;
CREATE MATERIALIZED VIEW analytics.alerta_dispensa_repetida AS
SELECT
    rc.fornecedor_cnpj,
    MAX(rc.fornecedor_nome)                             AS fornecedor_nome,
    rc.orgao_codigo,
    MAX(rc.orgao_nome)                                  AS orgao_nome,
    rc.raw_payload->>'cd_tce'                           AS cd_tce,
    COUNT(*)                                            AS n_dispensas_12m,
    ROUND(SUM(rc.valor_total)::numeric, 2)              AS valor_total_dispensas,
    ROUND(percentile_cont(0.5) WITHIN GROUP (
        ORDER BY rc.valor_total)::numeric, 2)           AS mediana_valor_dispensa,
    MIN(rc.contract_date)                               AS primeira_dispensa,
    MAX(rc.contract_date)                               AS ultima_dispensa,
    NOW()                                               AS calculado_em
FROM raw.compras rc
JOIN analytics.fornecedor f ON f.cnpj = rc.fornecedor_cnpj
JOIN analytics.item_canonical ic ON ic.raw_id = rc.id
WHERE rc.source = 'tce_pr/contrato'
  AND rc.modalidade = 'dispensa'
  AND rc.contract_date >= NOW() - INTERVAL '12 months'
  AND f.tipo_juridico = 'PJ'
  AND ic.eliminada_em IS NULL
  AND rc.fornecedor_cnpj IS NOT NULL
  AND rc.orgao_codigo IS NOT NULL
GROUP BY rc.fornecedor_cnpj, rc.orgao_codigo, rc.raw_payload->>'cd_tce'
HAVING COUNT(*) >= 3;

CREATE UNIQUE INDEX idx_alerta_dispensa_pk
    ON analytics.alerta_dispensa_repetida
    (fornecedor_cnpj, orgao_codigo, cd_tce);

CREATE INDEX idx_alerta_dispensa_n
    ON analytics.alerta_dispensa_repetida (n_dispensas_12m DESC);

CREATE INDEX idx_alerta_dispensa_valor
    ON analytics.alerta_dispensa_repetida (valor_total_dispensas DESC);

CREATE INDEX idx_alerta_dispensa_cnpj
    ON analytics.alerta_dispensa_repetida (fornecedor_cnpj);

COMMENT ON MATERIALIZED VIEW analytics.alerta_dispensa_repetida IS
    'PLANO §19.6 — combinações (CNPJ PJ + órgão + município) com ≥3 dispensas nos últimos 12 meses. Defesa L.1+L.2 na origem. 3+ não implica irregularidade (calamidade/especialização podem explicar) — UI mostra disclaimer.';
COMMENT ON COLUMN analytics.alerta_dispensa_repetida.n_dispensas_12m IS
    'Contagem de contratos modalidade=dispensa nos últimos 12 meses calendar (não rolling em refresh).';
COMMENT ON COLUMN analytics.alerta_dispensa_repetida.primeira_dispensa IS
    'contract_date mais antiga na janela de 12m. Útil para detectar concentração temporal (todas no mesmo mês = mais suspeito que espalhadas).';

REFRESH MATERIALIZED VIEW analytics.alerta_dispensa_repetida;
