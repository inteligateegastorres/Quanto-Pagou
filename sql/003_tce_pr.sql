-- Quanto Pagou - schema TCE-PR (Day 8+).
-- TCE-PR publica ZIP anual em pit.tce.pr.gov.br/Arquivos/{ano}_PIT_TodosArquivos.zip,
-- contendo um sub-zip por (municipio x tema). Granularidade e por contrato (nao
-- por item) — schema diferente do federal Compras.gov.br. Pipelines coexistem
-- via coluna `source`; threshold de comparacao e separado.
--
-- Migration idempotente: pode rodar varias vezes seguidas.

CREATE SCHEMA IF NOT EXISTS analytics;

-- ---------------------------------------------------------------------------
-- Catalogo de municipios PR (tabela auxiliar para porte e nome canonico).
-- Populada manualmente; ~30-40 municipios maiores cobrem >70% do PIB do PR.
-- Demais municipios entram com porte='municipio_pr_pequeno' por default.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.municipio_pr (
    cd_tce          TEXT PRIMARY KEY,            -- codigo TCE-PR (ex: 410690)
    cd_ibge         TEXT,                        -- codigo IBGE (ex: 4106902)
    nome            TEXT NOT NULL,
    porte           TEXT NOT NULL DEFAULT 'municipio_pr_pequeno',
    populacao       INTEGER,
    atualizado_em   TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE analytics.municipio_pr IS
    'Catalogo dos 399 municipios do PR com porte para o pipeline TCE-PR.';

-- Seed inicial: top municipios + porte por tier de populacao.
-- Tier 1 (capital + grandes >300k): grande
-- Tier 2 (medio 50-300k): medio
-- Demais: pequeno (default)
INSERT INTO analytics.municipio_pr (cd_tce, cd_ibge, nome, porte, populacao) VALUES
    ('410690', '4106902', 'CURITIBA',                       'municipio_pr_grande', 1773733),
    ('411370', '4113700', 'LONDRINA',                       'municipio_pr_grande', 580870),
    ('411520', '4115200', 'MARINGA',                        'municipio_pr_grande', 436472),
    ('410500', '4105050', 'CASCAVEL',                       'municipio_pr_grande', 332333),
    ('411740', '4117406', 'PONTA GROSSA',                   'municipio_pr_grande', 358838),
    ('410830', '4108304', 'FOZ DO IGUACU',                  'municipio_pr_grande', 285415),
    ('412550', '4125506', 'SAO JOSE DOS PINHAIS',           'municipio_pr_grande', 329058),
    ('410480', '4104808', 'COLOMBO',                        'municipio_pr_medio', 220678),
    ('410260', '4102604', 'ARAUCARIA',                      'municipio_pr_medio', 142010),
    ('411330', '4113304', 'GUARAPUAVA',                     'municipio_pr_medio', 181504),
    ('411020', '4110102', 'PARANAGUA',                      'municipio_pr_medio', 159679),
    ('411410', '4114104', 'MARECHAL CANDIDO RONDON',        'municipio_pr_medio',  53272),
    ('410450', '4104501', 'CIANORTE',                       'municipio_pr_medio',  82911),
    ('410585', '4105805', 'CAMPO LARGO',                    'municipio_pr_medio', 132017),
    ('410775', '4107754', 'FAZENDA RIO GRANDE',             'municipio_pr_medio', 100662),
    ('411450', '4114501', 'MEDIANEIRA',                     'municipio_pr_medio',  46720),
    ('410435', '4104351', 'CHOPINZINHO',                    'municipio_pr_medio',  20146),
    ('411990', '4119905', 'SAO JOAO DO IVAI',               'municipio_pr_pequeno', 11625)
ON CONFLICT (cd_tce) DO UPDATE SET
    cd_ibge   = EXCLUDED.cd_ibge,
    nome      = EXCLUDED.nome,
    porte     = EXCLUDED.porte,
    populacao = EXCLUDED.populacao;

CREATE INDEX IF NOT EXISTS idx_municipio_pr_porte ON analytics.municipio_pr (porte);
CREATE INDEX IF NOT EXISTS idx_municipio_pr_ibge  ON analytics.municipio_pr (cd_ibge);

-- ---------------------------------------------------------------------------
-- Mart 3: ranking de orgaos municipais por cluster (PR).
-- Mesma ideia do mart_orgao_cluster federal, mas:
--  - filtra source='tce_pr/contrato'
--  - threshold de confianca >= 0.5 (cluster por keyword e mais fraco que CATMAT)
--  - agrupa por orgao + municipio (multiple entidades por municipio:
--    prefeitura, camara, autarquias)
-- ---------------------------------------------------------------------------
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
  AND ic.confianca_resolucao >= 0.5
GROUP BY 1, 2, 3, 4, 5, 6, 7;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mart_contratos_municipio_pk
    ON analytics.mart_contratos_municipio (
        cluster_id, cluster_version, cd_ibge, orgao_codigo
    );

COMMENT ON MATERIALIZED VIEW analytics.mart_contratos_municipio IS
    'Granularidade contrato (TCE-PR). Threshold confianca >= 0.5 porque cluster por keyword e mais fraco que CATMAT. Mediana e p25/p75 referem-se a valor por contrato, nao por item.';

-- ---------------------------------------------------------------------------
-- Mart 4: ranking de fornecedores por municipio (PR).
-- Gancho viral "Top fornecedores que mais ganham contratos da Prefeitura X".
-- ---------------------------------------------------------------------------
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
WHERE rc.source = 'tce_pr/contrato'
  AND rc.fornecedor_cnpj IS NOT NULL
GROUP BY 1, 2, 3, 4;

-- CPFs vem mascarados pelo TCE-PR (ex: "***.017.***-**"), entao multiplas
-- pessoas fisicas distintas colidem no mesmo cnpj-mascarado. Incluimos
-- fornecedor_nome no UNIQUE pra desambiguar — mantendo refresh concorrente.
CREATE UNIQUE INDEX IF NOT EXISTS idx_mart_fornecedores_municipio_pk
    ON analytics.mart_fornecedores_municipio (cd_ibge, fornecedor_cnpj, fornecedor_nome);

COMMENT ON MATERIALIZED VIEW analytics.mart_fornecedores_municipio IS
    'Top fornecedores por municipio do PR. Sem threshold de cluster — inclui todos os contratos do TCE-PR para esse municipio, mesmo em quarentena (fornecedor existe independente do cluster).';
