-- Quanto Pagou — schema inicial (Day 1)
-- Progressive correctness: simples e suficiente. Sofisticar depois.

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Camada de durabilidade mínima: cada batch de ingestão é um snapshot imutável.
CREATE TABLE IF NOT EXISTS raw.snapshots (
    id              TEXT PRIMARY KEY,
    source          TEXT NOT NULL,
    period_start    DATE,
    period_end      DATE,
    records_count   INTEGER,
    hash_sha256     TEXT,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabela bruta de contratos/itens. Schema deliberadamente raso — o JSON
-- original fica em `raw_payload` para reprocessamento futuro.
CREATE TABLE IF NOT EXISTS raw.compras (
    id              BIGSERIAL PRIMARY KEY,
    snapshot_id     TEXT NOT NULL REFERENCES raw.snapshots(id),
    source          TEXT NOT NULL,
    source_id       TEXT,
    source_url      TEXT,
    contract_date   DATE,
    orgao_codigo    TEXT,
    orgao_nome      TEXT,
    fornecedor_cnpj TEXT,
    fornecedor_nome TEXT,
    catmat_id       TEXT,
    catser_id       TEXT,
    descricao       TEXT NOT NULL,
    quantidade      NUMERIC,
    unidade         TEXT,
    valor_unitario  NUMERIC,
    valor_total     NUMERIC,
    modalidade      TEXT,
    raw_payload     JSONB NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_compras_catmat        ON raw.compras (catmat_id) WHERE catmat_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_compras_orgao         ON raw.compras (orgao_codigo);
CREATE INDEX IF NOT EXISTS idx_compras_data          ON raw.compras (contract_date);
CREATE INDEX IF NOT EXISTS idx_compras_snapshot      ON raw.compras (snapshot_id);
CREATE INDEX IF NOT EXISTS idx_compras_fornecedor    ON raw.compras (fornecedor_cnpj);

COMMENT ON TABLE raw.compras IS 'Itens de contratos públicos brutos. JSON original em raw_payload para reprocessamento.';
COMMENT ON COLUMN raw.compras.snapshot_id IS 'Referência ao batch imutável de origem (camada de durabilidade).';
