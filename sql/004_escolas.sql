-- Quanto Pagou — catalogo de obras escolares (004).
-- Persiste mencoes de escola/CMEI/creche extraidas via regex em
-- src/analytics/escolas.py. Cobertura medida em ~270 contratos no PR
-- (0.17% do total), concentrada em obras_edificacao.
--
-- Migration idempotente. Tabela popula via build_marts.

CREATE TABLE IF NOT EXISTS analytics.escola_mencao (
    raw_id          BIGINT PRIMARY KEY REFERENCES raw.compras(id) ON DELETE CASCADE,
    escola_nome     TEXT NOT NULL,
    escola_slug     TEXT NOT NULL,
    padrao          TEXT NOT NULL,                -- id do regex que casou (auditoria)
    cd_tce          TEXT,                         -- denormalizado para query rapida
    detectado_em    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_escola_slug    ON analytics.escola_mencao (escola_slug);
CREATE INDEX IF NOT EXISTS idx_escola_cd_tce  ON analytics.escola_mencao (cd_tce);

COMMENT ON TABLE analytics.escola_mencao IS
    'Mencoes de escola individual extraidas do dsObjeto via regex. Cobertura ~0.17% — feature de catalogo, nao ranking.';
COMMENT ON COLUMN analytics.escola_mencao.escola_slug IS
    'Slug normalizado (lowercase, sem acento, hyphens) — chave de agrupamento. Mesma escola em municipios diferentes pode colidir; tratar como label, nao identidade.';
