-- LGPD art. 37 — registro de operacoes de tratamento (PLANO §18 L.10).
--
-- Cobre auditoria das operacoes que tocam dado pessoal ou estado regulado:
--   - analytics.eliminacao       (LGPD art. 18 IV — solicitacao de eliminacao)
--   - analytics.item_canonical   (sincronizacao de eliminada_em via trigger)
--   - analytics.fornecedor       (mudancas de tipo_juridico — criada em L.2)
--
-- NAO cobre operacoes de refresh de MV (volume alto, sem ganho probatorio:
-- refresh recria estado derivado, nao registra decisao sobre titular).
-- NAO cobre raw.compras (imutavel; eliminacao logica via tombstone).
--
-- Padrao de ator: psycopg seta `SET LOCAL app.audit_actor = 'dpo@...'`
-- antes do write; trigger captura via current_setting. Para INSERT em
-- analytics.eliminacao a coluna `ator` da propria linha tem precedencia.

-- ---------------------------------------------------------------------------
-- 1. Tabela append-only
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.audit_log (
    id              BIGSERIAL PRIMARY KEY,
    ocorrido_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    schema_name     TEXT NOT NULL,
    table_name      TEXT NOT NULL,
    operacao        CHAR(1) NOT NULL CHECK (operacao IN ('I', 'U', 'D')),
    pk_text         TEXT,
    raw_id_afetado  BIGINT,
    ator            TEXT,
    base_legal      TEXT,
    diff            JSONB
);

CREATE INDEX IF NOT EXISTS idx_audit_log_ocorrido
    ON analytics.audit_log (ocorrido_em DESC);

CREATE INDEX IF NOT EXISTS idx_audit_log_table
    ON analytics.audit_log (schema_name, table_name, ocorrido_em DESC);

CREATE INDEX IF NOT EXISTS idx_audit_log_raw_id
    ON analytics.audit_log (raw_id_afetado)
    WHERE raw_id_afetado IS NOT NULL;

COMMENT ON TABLE analytics.audit_log IS
    'Registro append-only de operacoes em tabelas com dado pessoal ou regulado (LGPD art. 37). Capturado via triggers; ator vem de current_setting app.audit_actor (psycopg SET LOCAL antes do write) ou da propria linha quando aplicavel.';

-- ---------------------------------------------------------------------------
-- 2. Funcao trigger generica
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION analytics.fn_audit_log()
RETURNS TRIGGER AS $$
DECLARE
    v_ator        TEXT;
    v_base_legal  TEXT;
    v_pk_text     TEXT;
    v_raw_id      BIGINT;
    v_diff        JSONB;
    v_op          CHAR(1);
    v_new_jsonb   JSONB;
    v_old_jsonb   JSONB;
BEGIN
    -- ator: setting de sessao tem prioridade; row.ator (eliminacao) cobre o caso
    -- de INSERT direto via SQL sem set explicito.
    v_ator       := NULLIF(current_setting('app.audit_actor', true), '');
    v_base_legal := NULLIF(current_setting('app.audit_base_legal', true), '');

    IF TG_OP = 'DELETE' THEN
        v_op := 'D';
        v_old_jsonb := to_jsonb(OLD);
        v_diff := jsonb_build_object('antigo', v_old_jsonb);
    ELSIF TG_OP = 'INSERT' THEN
        v_op := 'I';
        v_new_jsonb := to_jsonb(NEW);
        v_diff := jsonb_build_object('novo', v_new_jsonb);
    ELSE  -- UPDATE
        v_op := 'U';
        v_new_jsonb := to_jsonb(NEW);
        v_old_jsonb := to_jsonb(OLD);
        v_diff := jsonb_build_object('antigo', v_old_jsonb, 'novo', v_new_jsonb);
    END IF;

    -- pk_text + raw_id_afetado por tabela conhecida (cresce quando tabelas novas
    -- entram em L.2; deixar generico evita LATERAL por reflection)
    IF TG_TABLE_NAME = 'eliminacao' THEN
        v_raw_id := (COALESCE(v_new_jsonb, v_old_jsonb)->>'raw_id')::BIGINT;
        v_pk_text := v_raw_id::TEXT;
        IF v_ator IS NULL THEN
            v_ator := COALESCE(v_new_jsonb, v_old_jsonb)->>'ator';
        END IF;
        IF v_base_legal IS NULL THEN
            v_base_legal := COALESCE(v_new_jsonb, v_old_jsonb)->>'fundamento_legal';
        END IF;
    ELSIF TG_TABLE_NAME = 'item_canonical' THEN
        v_raw_id := (COALESCE(v_new_jsonb, v_old_jsonb)->>'raw_id')::BIGINT;
        v_pk_text := v_raw_id::TEXT;
    ELSIF TG_TABLE_NAME = 'fornecedor' THEN
        v_pk_text := COALESCE(v_new_jsonb, v_old_jsonb)->>'cnpj';
    ELSE
        v_pk_text := NULL;
    END IF;

    INSERT INTO analytics.audit_log
        (schema_name, table_name, operacao, pk_text, raw_id_afetado, ator, base_legal, diff)
    VALUES
        (TG_TABLE_SCHEMA, TG_TABLE_NAME, v_op, v_pk_text, v_raw_id, v_ator, v_base_legal, v_diff);

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION analytics.fn_audit_log() IS
    'Trigger generico de auditoria. Captura ator/base_legal de current_setting (preferido) ou da propria linha (fallback para analytics.eliminacao).';

-- ---------------------------------------------------------------------------
-- 3. Triggers em tabelas com dado pessoal ou estado regulado
-- ---------------------------------------------------------------------------

-- analytics.eliminacao: registra cada solicitacao atendida (LGPD art. 18 IV)
DROP TRIGGER IF EXISTS trg_audit_eliminacao ON analytics.eliminacao;
CREATE TRIGGER trg_audit_eliminacao
    AFTER INSERT OR UPDATE OR DELETE ON analytics.eliminacao
    FOR EACH ROW
    EXECUTE FUNCTION analytics.fn_audit_log();

-- analytics.item_canonical: so quando eliminada_em muda (resto e canonicalizacao
-- deterministica, sem decisao sobre titular).
DROP TRIGGER IF EXISTS trg_audit_item_canonical_eliminacao ON analytics.item_canonical;
CREATE TRIGGER trg_audit_item_canonical_eliminacao
    AFTER UPDATE OF eliminada_em ON analytics.item_canonical
    FOR EACH ROW
    WHEN (OLD.eliminada_em IS DISTINCT FROM NEW.eliminada_em)
    EXECUTE FUNCTION analytics.fn_audit_log();

-- analytics.fornecedor (L.2): trigger criado no proprio 009_fornecedor.sql
-- quando a tabela existir, pra evitar erro de tabela inexistente aqui.
