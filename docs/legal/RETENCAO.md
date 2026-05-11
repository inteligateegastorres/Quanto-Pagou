# Política de Retenção de Dados — Quanto Pagou

**Versão**: v1 (2026-05-11)
**Fundamento**: LGPD art. 16 (eliminação) + art. 37 (registro de operações)
**Escopo**: aplica-se a todas as camadas do banco de dados do projeto.

---

## Princípio

Reter apenas o que é necessário à finalidade declarada (controle social,
fiscalização e jornalismo de dados sobre gastos públicos brasileiros) e
documentar prazos por tipo de dado.

Onde a fonte primária é pública e replicável (TCE-PR, Compras.gov.br,
Querido Diário), preferimos **eliminação local** sobre **retenção
defensiva**: se o dado pode ser re-baixado, não precisa ser mantido
indefinidamente.

---

## Tabela de retenção

| Camada / Tabela | Conteúdo | Retenção | Estratégia de expurgo |
|---|---|---|---|
| `raw.snapshots` | Bytes brutos do download da fonte + hash | **Indefinida (imutável)** | Não expurgar — auditoria contra falsificação. Tamanho controlado por compactação Postgres TOAST. |
| `raw.compras.raw_payload` (JSONB) | Payload original da linha, redundante com colunas dedicadas | **90 dias após canonicalização bem-sucedida** | CLI `scripts/expurgar_raw_payload.py` (ver L.9.b) substitui por `'{}'::jsonb` quando todas as colunas dedicadas estão populadas e a qualidade do parse foi verificada. |
| `raw.compras` (colunas dedicadas) | `fornecedor_cnpj`, `valor_total`, `contract_date`, etc. | **Indefinida** | Não expurgar — base de comparações. Eliminação só via L.1 tombstone (LGPD art. 18 IV). |
| `analytics.item_canonical` | Camada canônica 1:1 com `raw.compras` | **Indefinida** | Mesmo regime de `raw.compras`. Coluna `eliminada_em` (L.1) marca tombstone sem deletar. |
| `analytics.fornecedor` | Enriquecimento de `tipo_juridico` | **Indefinida** | Re-classificado a cada execução de `fn_enriquecer_fornecedor`. Linhas órfãs (CNPJs que sumiram de `raw.compras`) podem ser limpas anualmente. |
| `analytics.eliminacao` | Registro de eliminações atendidas | **Indefinida (LGPD art. 37)** | Não expurgar — prova de cumprimento do direito do titular. |
| `analytics.audit_log` | Operações registradas (L.10) | **5 anos** | Suficiente pra prazo prescricional da LGPD (art. 52 §1º) + tolerância. Após 5 anos, expurgar registros com `ocorrido_em < NOW() - INTERVAL '5 years'`. |
| Materialized views (`mart_*`, `cluster_discrepancias`) | Estado derivado | **Sem retenção** | Recriadas a cada refresh; não armazenam histórico próprio. |
| `analytics.manchete_publicada` | Histórico de manchetes algorítmicas publicadas | **2 anos** | Manchetes antigas perdem valor probatório; expurgar mensalmente. |
| Logs de aplicação (Vercel/Fly/Cloudflare) | Acessos, erros | **30 dias** | Default das plataformas; documentar em `SUBPROCESSADORES.md` (L.8). |

---

## Operacionalização

1. **L.9.a (este documento, entregue)**: política escrita.
2. **L.9.b (próxima sessão)**: `scripts/expurgar_raw_payload.py`
   com `--dry-run` mostrando linhas afetadas + tamanho liberado, e
   verificação obrigatória de qualidade (todas as colunas dedicadas
   NOT NULL) antes de zerar `raw_payload`.
3. **L.9.c (após ≥1 ciclo manual validado)**: workflow GitHub Actions
   mensal rodando `expurgar_raw_payload.py` em modo não-interativo.

Cadência: nenhum expurgo automatizado entra em produção sem ≥1 ciclo
manual com dry-run revisado.

---

## Direito de eliminação (LGPD art. 18 IV)

Não confundir retenção com eliminação por solicitação do titular. Esta é
imediata (SLA 15d) e atendida via `scripts/eliminar.py` + tombstones
(L.1), independentemente dos prazos desta política.

`raw.compras` e `raw.snapshots` **não são apagados** mesmo em
eliminação — o tombstone em `analytics.item_canonical.eliminada_em`
remove o conteúdo da vitrine pública preservando integridade do
snapshot bruto contra alegações de falsificação. Ver `sql/007_eliminacao.sql`.

---

## Histórico de revisões

| Versão | Data | Mudança |
|---|---|---|
| v1 | 2026-05-11 | Versão inicial (PLANO §18 L.9.a) |
