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

-- Seed inicial: 35 municipios mais expressivos do PR com porte por tier.
-- cd_tce e cd_ibge sao chaves OFICIAIS distintas (TCE-PR usa primeiros 6
-- digitos do IBGE; o digito verificador IBGE eh determinístico).
-- Tier 1 (capital + grandes >250k habitantes): grande
-- Tier 2 (medio 50-250k): medio
-- Demais municipios PR ficam como 'municipio_pr_pequeno' por default.
INSERT INTO analytics.municipio_pr (cd_tce, cd_ibge, nome, porte, populacao) VALUES
    ('410690', '4106902', 'CURITIBA',                  'municipio_pr_grande',  1773733),
    ('411370', '4113700', 'LONDRINA',                  'municipio_pr_grande',   580870),
    ('411520', '4115200', 'MARINGA',                   'municipio_pr_grande',   436472),
    ('410480', '4104808', 'CASCAVEL',                  'municipio_pr_grande',   332333),
    ('411990', '4119905', 'PONTA GROSSA',              'municipio_pr_grande',   358838),
    ('410830', '4108304', 'FOZ DO IGUACU',             'municipio_pr_grande',   285415),
    ('412550', '4125506', 'SAO JOSE DOS PINHAIS',      'municipio_pr_grande',   329058),
    ('412770', '4127700', 'TOLEDO',                    'municipio_pr_medio',    142809),
    ('410140', '4101408', 'APUCARANA',                 'municipio_pr_medio',    136234),
    ('411850', '4118501', 'PATO BRANCO',               'municipio_pr_medio',     83894),
    ('410550', '4105508', 'CIANORTE',                  'municipio_pr_medio',     83567),
    ('410840', '4108403', 'FRANCISCO BELTRAO',         'municipio_pr_medio',     94390),
    ('412810', '4128104', 'UMUARAMA',                  'municipio_pr_medio',    113261),
    ('410940', '4109401', 'GUARAPUAVA',                'municipio_pr_medio',    181504),
    ('411460', '4114609', 'MARECHAL CANDIDO RONDON',   'municipio_pr_medio',     53272),
    ('410430', '4104303', 'CAMPO MOURAO',              'municipio_pr_medio',     95406),
    ('411180', '4111803', 'JACAREZINHO',               'municipio_pr_medio',     39476),
    ('410420', '4104204', 'CAMPO LARGO',               'municipio_pr_medio',    132017),
    ('410180', '4101804', 'ARAUCARIA',                 'municipio_pr_medio',    142010),
    ('410490', '4104907', 'CASTRO',                    'municipio_pr_medio',     71929),
    ('410150', '4101507', 'ARAPONGAS',                 'municipio_pr_medio',    127116),
    ('411580', '4115804', 'MEDIANEIRA',                'municipio_pr_medio',     46720),
    ('412710', '4127106', 'TELEMACO BORBA',            'municipio_pr_medio',     76728),
    ('411840', '4118402', 'PARANAVAI',                 'municipio_pr_medio',     86374),
    ('411020', '4110201', 'PARANAGUA',                 'municipio_pr_medio',    159679),
    ('410775', '4107754', 'FAZENDA RIO GRANDE',        'municipio_pr_medio',    100662),
    ('410450', '4104501', 'COLOMBO',                   'municipio_pr_medio',    220678),
    ('411095', '4110951', 'ITAIPULANDIA',              'municipio_pr_pequeno',   12231),
    ('410880', '4108809', 'GUAIRA',                    'municipio_pr_medio',     31426),
    ('412410', '4124103', 'SANTO ANTONIO DA PLATINA',  'municipio_pr_medio',     43889),
    ('411605', '4116059', 'MISSAL',                    'municipio_pr_pequeno',   10474),
    ('411400', '4114005', 'MAMBORE',                   'municipio_pr_pequeno',   13961),
    ('412740', '4127405', 'TERRA ROXA',                'municipio_pr_pequeno',   17537),
    ('412060', '4120606', 'PRUDENTOPOLIS',             'municipio_pr_medio',     51728),
    ('411150', '4111506', 'IVAIPORA',                  'municipio_pr_medio',     30021)
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
