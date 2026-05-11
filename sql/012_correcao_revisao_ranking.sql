-- LGPD L.13 — direito a revisao de decisao automatizada (LGPD art. 20)
--
-- Adiciona tipo 'revisao_ranking' em analytics.correcao_ticket. Reusa o
-- pipeline de L.12 (ticket QP-AAAA-XXXX, SLA, audit_log) sem schema novo.
--
-- Por que ALTER CHECK em vez de coluna nova: art. 20 e' uma especie do
-- art. 18 (direito do titular) operacionalizado como tipo de ticket. Faz
-- sentido viver no mesmo workflow.

ALTER TABLE analytics.correcao_ticket
    DROP CONSTRAINT IF EXISTS correcao_ticket_tipo_check;

ALTER TABLE analytics.correcao_ticket
    ADD CONSTRAINT correcao_ticket_tipo_check
    CHECK (tipo IN (
        'factual',
        'lgpd_acesso',
        'lgpd_correcao',
        'lgpd_eliminacao',
        'classificacao_pj',
        'revisao_ranking',
        'outro'
    ));
