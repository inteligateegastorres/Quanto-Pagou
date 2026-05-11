-- LGPD L.12 — /correcoes formal com ticket auditavel (PLANO §18 L.12).
--
-- Substitui o mailto: estatico por fluxo ticket+SLA documentado:
--   - tipo classifica natureza (factual vs LGPD vs classificacao PJ)
--   - sla_classe define prazo (48h fato / 15d LGPD art. 19)
--   - status auditavel (aberto -> em_analise -> resolvido_*/rejeitado)
--   - publicar_descricao default FALSE: descricao so vai pra vitrine
--     publica se reportador autorizar
--   - audit_log (L.10) capturado via trigger generico
--   - ticket_id publico no formato QP-AAAA-XXXX (ano + 4 hex)

CREATE TABLE IF NOT EXISTS analytics.correcao_ticket (
    id                    BIGSERIAL PRIMARY KEY,
    ticket_id             TEXT UNIQUE NOT NULL,
    criado_em             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- categorizacao
    tipo                  TEXT NOT NULL,
    sla_classe            TEXT NOT NULL,
    -- conteudo
    url_afetada           TEXT,
    raw_id_afetado        BIGINT,
    fornecedor_cnpj       TEXT,
    descricao             TEXT NOT NULL,
    fonte_correta         TEXT,
    publicar_descricao    BOOLEAN NOT NULL DEFAULT FALSE,
    -- contato opcional
    contato_email         TEXT,
    -- workflow
    status                TEXT NOT NULL DEFAULT 'aberto',
    -- resolucao
    resolvido_em          TIMESTAMPTZ,
    resolucao_publica     TEXT,
    resolucao_delta       JSONB,
    CHECK (tipo IN (
        'factual', 'lgpd_acesso', 'lgpd_correcao', 'lgpd_eliminacao',
        'classificacao_pj', 'outro'
    )),
    CHECK (sla_classe IN ('factual_48h', 'lgpd_15d')),
    CHECK (status IN (
        'aberto', 'em_analise',
        'resolvido_corrigido', 'resolvido_sem_correcao', 'rejeitado'
    ))
);

CREATE INDEX IF NOT EXISTS idx_correcao_status_data
    ON analytics.correcao_ticket (status, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_correcao_raw_id
    ON analytics.correcao_ticket (raw_id_afetado)
    WHERE raw_id_afetado IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_correcao_resolvidos_pub
    ON analytics.correcao_ticket (resolvido_em DESC)
    WHERE status IN ('resolvido_corrigido', 'resolvido_sem_correcao');

COMMENT ON TABLE analytics.correcao_ticket IS
    'Tickets de correcao (LGPD L.12) — fluxo auditavel substitui o mailto: estatico. Status workflow: aberto -> em_analise -> resolvido_{corrigido,sem_correcao}/rejeitado. SLA: factual_48h (correcao de fato verificavel) ou lgpd_15d (art. 19). publicar_descricao FALSE por default — reportador controla o que vira vitrine publica.';

-- ---------------------------------------------------------------------------
-- Gerador de ticket_id publico (QP-AAAA-XXXX)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION analytics.fn_gerar_ticket_id()
RETURNS TEXT AS $$
DECLARE
    v_id      TEXT;
    v_attempt INTEGER := 0;
BEGIN
    LOOP
        v_attempt := v_attempt + 1;
        v_id := 'QP-' || EXTRACT(YEAR FROM NOW())::TEXT || '-' ||
                UPPER(
                    SUBSTRING(
                        MD5(RANDOM()::TEXT || CLOCK_TIMESTAMP()::TEXT)
                        FROM 1 FOR 4
                    )
                );
        IF NOT EXISTS (
            SELECT 1 FROM analytics.correcao_ticket WHERE ticket_id = v_id
        ) THEN
            RETURN v_id;
        END IF;
        IF v_attempt >= 10 THEN
            RAISE EXCEPTION
                'fn_gerar_ticket_id: nao foi possivel gerar ID unico em 10 tentativas';
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- Trigger de audit_log (L.10) em correcao_ticket
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_audit_correcao_ticket ON analytics.correcao_ticket;
CREATE TRIGGER trg_audit_correcao_ticket
    AFTER INSERT OR UPDATE OR DELETE ON analytics.correcao_ticket
    FOR EACH ROW
    EXECUTE FUNCTION analytics.fn_audit_log();
