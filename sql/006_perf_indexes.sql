-- Indices de performance para queries quentes (PLANO §17.B.3).
--
-- Critica externa: "queries filtram source = 'tce_pr/contrato' primeiro;
-- composite com source a frente." Mas source so tem 2 valores
-- (tce_pr/contrato, compras_gov_br/...) — cardinalidade pessima para
-- ser primeira coluna de B-tree. Solucao melhor: PARTIAL INDEX com
-- WHERE source = 'tce_pr/contrato' nos campos quentes.
--
-- Indices criados (todos partial, indexam so 99% das linhas — TCE-PR):
--   idx_compras_tce_data    : (contract_date) — drill-down por periodo
--   idx_compras_tce_cd_tce  : ((raw_payload->>'cd_tce')) — drill-down por municipio
--   idx_compras_tce_modalidade: (modalidade) — filtro modalidade
--
-- EXPLAIN antes/depois esta documentado no PLANO §17.B.3 (commit X).

CREATE INDEX IF NOT EXISTS idx_compras_tce_data
    ON raw.compras (contract_date)
    WHERE source = 'tce_pr/contrato';

CREATE INDEX IF NOT EXISTS idx_compras_tce_cd_tce
    ON raw.compras ((raw_payload->>'cd_tce'))
    WHERE source = 'tce_pr/contrato';

CREATE INDEX IF NOT EXISTS idx_compras_tce_modalidade
    ON raw.compras (modalidade)
    WHERE source = 'tce_pr/contrato' AND modalidade IS NOT NULL;

-- item_canonical: query "todos por cluster_id" sem filtro de quarentena
-- nao usa idx_item_canon_cluster (que e WHERE em_quarentena=FALSE).
-- Para casos como /manchete/diagnostico (busca todos do municipio),
-- precisamos um indice geral de cluster_id.
CREATE INDEX IF NOT EXISTS idx_item_canon_cluster_all
    ON analytics.item_canonical (cluster_id)
    WHERE cluster_id IS NOT NULL;

-- ANALYZE para o planner saber sobre os novos indices imediatamente.
ANALYZE raw.compras;
ANALYZE analytics.item_canonical;
