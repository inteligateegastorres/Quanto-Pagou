-- LGPD — distincao PJ vs MEI/EI/PF (PLANO §18 L.2).
--
-- Resolve achado "threshold >=5 contratos e heuristica sem fundamento":
-- defesa em camadas precisa, alem do threshold, separar pessoa juridica
-- (perfil publico legitimo) de MEI/EI/PF disfarcadas de CNPJ (dado pessoal).
--
-- Estrategia escolhida (default deny + heuristica determinista por sufixo):
--   1. Tabela analytics.fornecedor com tipo_juridico explicito
--   2. Job SQL classifica via sufixo INEQUIVOCO (LTDA, S.A./S/A, EIRELI,
--      SOCIEDADE ANONIMA, COOPERATIVA, ASSOCIACAO, FUNDACAO, INSTITUTO,
--      FEDERACAO, SINDICATO). Tudo o resto fica NULL.
--   3. Endpoint /fornecedor/{cnpj} mascara qualquer NULL ou != 'PJ'
--   4. Sufixos ME/EPP isolados NAO marcam PJ (ambiguos — podem ser MEI)
--   5. Fonte futura: dump RFB CNPJ aberto sobrescreve heuristica
--      (campo `fonte` versionado: 'heuristica_sufixo_v1' -> 'rfb_dump_AAAA-MM')

-- ---------------------------------------------------------------------------
-- 1. Tabela enriquecimento
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.fornecedor (
    cnpj             TEXT PRIMARY KEY,
    nome_normalizado TEXT,
    tipo_juridico    TEXT,
    fonte            TEXT NOT NULL,
    classificado_em  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (tipo_juridico IS NULL OR tipo_juridico IN
        ('PJ', 'MEI', 'EI', 'PF', 'EXTERIOR', 'INDETERMINADO'))
);

CREATE INDEX IF NOT EXISTS idx_fornecedor_tipo
    ON analytics.fornecedor (tipo_juridico);

COMMENT ON TABLE analytics.fornecedor IS
    'Enriquecimento de fornecedores (LGPD L.2). tipo_juridico NULL = nao classificado = mascarado por default. Fonte versionada: heuristica_sufixo_v1 (atual) ou rfb_dump_AAAA-MM (futuro).';

COMMENT ON COLUMN analytics.fornecedor.tipo_juridico IS
    'PJ = pessoa juridica (perfil publico legitimo). MEI/EI/PF = dado pessoal (mascarado). NULL = nao classificado, default deny no endpoint.';

-- ---------------------------------------------------------------------------
-- 2. Funcao classificadora por sufixo (conservadora — falsos positivos > falsos negativos seria pior)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION analytics.fn_classificar_tipo_juridico(p_nome TEXT)
RETURNS TEXT AS $$
BEGIN
    IF p_nome IS NULL OR length(trim(p_nome)) = 0 THEN
        RETURN NULL;
    END IF;

    -- Sufixos restritos por lei a sociedade limitada/anonima/etc:
    --   LTDA (Lei 10.406/2002 art. 1.052+)
    --   S.A. / S/A (Lei 6.404/1976)
    --   EIRELI (Lei 12.441/2011, hoje extinta mas nomes antigos persistem)
    --   COOPERATIVA, ASSOCIACAO, FUNDACAO, INSTITUTO etc — tipos sem ambiguidade
    -- NAO usamos ME/EPP isolados: ambiguos com MEI (microempreendedor individual).
    IF p_nome ~* '\m(LTDA|S\.?A\.?|EIRELI|SOCIEDADE\s+AN[OÔ]NIMA|COOPERATIVA|ASSOCIA[CÇ][AÃ]O|FUNDA[CÇ][AÃ]O|INSTITUTO|FEDERA[CÇ][AÃ]O|SINDICATO|IGREJA|HOSPITAL|UNIVERSIDADE|MUNIC[IÍ]PIO|PREFEITURA|UNI[AÃ]O|ESTADO)\M' THEN
        RETURN 'PJ';
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION analytics.fn_classificar_tipo_juridico(TEXT) IS
    'Classifica fornecedor por sufixo do nome. Conservadora: so retorna PJ quando sufixo e inequivoco; tudo o resto fica NULL (mascarado).';

-- ---------------------------------------------------------------------------
-- 3. Job de enriquecimento (idempotente, nao sobrescreve fonte autoritativa)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION analytics.fn_enriquecer_fornecedor()
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    INSERT INTO analytics.fornecedor (cnpj, nome_normalizado, tipo_juridico, fonte)
    SELECT
        fornecedor_cnpj,
        MAX(fornecedor_nome),
        analytics.fn_classificar_tipo_juridico(MAX(fornecedor_nome)),
        'heuristica_sufixo_v1'
    FROM raw.compras
    WHERE fornecedor_cnpj IS NOT NULL
    GROUP BY fornecedor_cnpj
    ON CONFLICT (cnpj) DO UPDATE
    SET nome_normalizado = EXCLUDED.nome_normalizado,
        tipo_juridico    = EXCLUDED.tipo_juridico,
        fonte            = EXCLUDED.fonte,
        classificado_em  = NOW()
    -- nao sobrescreve fonte autoritativa (ex: rfb_dump_*)
    WHERE analytics.fornecedor.fonte LIKE 'heuristica%'
      AND (analytics.fornecedor.tipo_juridico IS DISTINCT FROM EXCLUDED.tipo_juridico
           OR analytics.fornecedor.nome_normalizado IS DISTINCT FROM EXCLUDED.nome_normalizado);
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- 4. Trigger audit_log (L.10) em analytics.fornecedor
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_audit_fornecedor ON analytics.fornecedor;
CREATE TRIGGER trg_audit_fornecedor
    AFTER INSERT OR UPDATE OR DELETE ON analytics.fornecedor
    FOR EACH ROW
    EXECUTE FUNCTION analytics.fn_audit_log();

-- ---------------------------------------------------------------------------
-- 5. Popula a partir do estado atual (idempotente, seguro re-rodar)
-- ---------------------------------------------------------------------------
-- Trigger de audit_log captura cada linha. Pra primeira carga em massa
-- (~50k fornecedores), seta ator do job pra registrar legitimamente.
-- Envolvido em BEGIN/COMMIT para SET LOCAL valer.
DO $populate$
BEGIN
    SET LOCAL app.audit_actor = 'job:enriquecer_fornecedor';
    SET LOCAL app.audit_base_legal = 'LGPD art. 7 V — execucao de politica publica de transparencia';
    PERFORM analytics.fn_enriquecer_fornecedor();
END
$populate$;
