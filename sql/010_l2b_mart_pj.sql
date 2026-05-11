-- LGPD L.2.b — defesa em camadas em MVs (PLANO §18 L.2.b).
--
-- mart_fornecedores_municipio agora filtra `tipo_juridico = 'PJ'` na
-- origem. Mesmo que algum endpoint esqueca de checar, o dado nao chega
-- mascarado a MEI/EI via essa MV.
--
-- L.2 v1 (sql/009) garante:
--   tipo_juridico = 'PJ' quando o nome contem sufixo INEQUIVOCO de PJ
--   NULL caso contrario (default deny)
-- Esta MV agora exclui NULLs tambem — alinhada com o endpoint.

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
JOIN analytics.fornecedor f ON f.cnpj = rc.fornecedor_cnpj
WHERE rc.source = 'tce_pr/contrato'
  AND rc.fornecedor_cnpj IS NOT NULL
  AND el.raw_id IS NULL                              -- LGPD L.1 tombstone
  AND f.tipo_juridico = 'PJ'                         -- LGPD L.2.b default deny
GROUP BY 1, 2, 3, 4;

CREATE UNIQUE INDEX idx_mart_fornecedores_municipio_pk
    ON analytics.mart_fornecedores_municipio (cd_ibge, fornecedor_cnpj, fornecedor_nome);

COMMENT ON MATERIALIZED VIEW analytics.mart_fornecedores_municipio IS
    'Agregado de fornecedores por municipio PR. Filtra PJ confirmado (L.2.b) + tombstones LGPD (L.1). Refresh via build_marts.';

REFRESH MATERIALIZED VIEW analytics.mart_fornecedores_municipio;
