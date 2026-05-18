-- L.19.11.a — Cadastro de órgãos federais (Compras.gov.br /modulo-uasg).
--
-- Tabela materializada a partir do endpoint
--   GET /modulo-uasg/2_consultarOrgao?statusOrgao=true
-- (~11k linhas em 23 páginas). Serve como tabela-de-loop para L.19.11.b:
-- o spider de contratos passa a iterar por `codigo_orgao` (parâmetro
-- agora obrigatório no endpoint /modulo-contratos/2_consultarContratosItem).
--
-- Convenção: nomeamos campos em snake_case PT-BR para casar com o resto
-- de analytics, mantendo `raw_payload` com o DTO original do upstream.
-- Upsert por `codigo_orgao` (PK): re-sincronizações atualizam linhas
-- existentes em vez de duplicar.

CREATE TABLE IF NOT EXISTS analytics.orgao_federal (
    codigo_orgao                INTEGER     PRIMARY KEY,
    nome                        TEXT        NOT NULL,
    nome_mnemonico              TEXT,
    cnpj                        TEXT,
    codigo_orgao_vinculado      INTEGER,
    nome_orgao_vinculado        TEXT,
    codigo_orgao_superior       INTEGER,
    nome_orgao_superior         TEXT,
    codigo_tipo_administracao   INTEGER,
    nome_tipo_administracao     TEXT,
    poder                       TEXT,
    esfera                      TEXT,
    uso_sisg                    BOOLEAN,
    status_ativo                BOOLEAN     NOT NULL,
    data_movimento              TIMESTAMPTZ,
    raw_payload                 JSONB       NOT NULL,
    snapshot_id                 TEXT        NOT NULL REFERENCES raw.snapshots(id),
    primeira_sync               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ultima_sync                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orgao_federal_cnpj
    ON analytics.orgao_federal (cnpj)
    WHERE cnpj IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_orgao_federal_poder_esfera
    ON analytics.orgao_federal (poder, esfera);

-- Index sobre `nome` para heurística top-N de L.19.11.c
-- (ILIKE '%ministerio%', '%fundo%', '%universidade%'). Btree é
-- suficiente; pg_trgm não está habilitado e não compensa por enquanto.
CREATE INDEX IF NOT EXISTS idx_orgao_federal_nome
    ON analytics.orgao_federal (nome);

COMMENT ON TABLE analytics.orgao_federal IS
    'Cadastro de órgãos federais (Compras.gov.br /modulo-uasg). Tabela-de-loop para o spider /modulo-contratos pós-breaking-change (PLANO §19.11).';
COMMENT ON COLUMN analytics.orgao_federal.codigo_orgao IS
    'codigoOrgao do DTO upstream. PK natural — upsert por este campo.';
COMMENT ON COLUMN analytics.orgao_federal.status_ativo IS
    'statusOrgao do upstream (true=ativo). O spider só coleta ativos por default.';
COMMENT ON COLUMN analytics.orgao_federal.ultima_sync IS
    'Atualizado a cada execução do spider que reencontra este código_orgao. Use para detectar órgãos sumindo do cadastro upstream.';
