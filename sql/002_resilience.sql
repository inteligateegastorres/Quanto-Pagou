-- Quanto Pagou - resiliencia da ingestao (002).
-- Adiciona status + error_message em raw.snapshots para suportar window
-- splitting com sucesso parcial (algumas sub-janelas concluem, outras falham).
-- Migration idempotente: pode rodar varias vezes seguidas.

ALTER TABLE raw.snapshots
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'completed';

ALTER TABLE raw.snapshots
    ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Snapshots existentes (criados antes dessa migration) ficam como 'completed'
-- pelo default acima — nada a backfillar.

CREATE INDEX IF NOT EXISTS idx_snapshots_status
    ON raw.snapshots (status, source);

COMMENT ON COLUMN raw.snapshots.status IS
    'Estado da ingestao: in_progress | completed | failed. Usado pelo window-split para deixar registro de janelas que falharam mesmo apos retentativas.';
COMMENT ON COLUMN raw.snapshots.error_message IS
    'Mensagem de erro abreviada (status=failed). Truncada em ~500 chars.';
