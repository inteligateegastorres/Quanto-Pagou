# ADR-002 — Defesa em camadas LGPD (Wave §18)

**Status:** Aceito
**Data:** 2026-05-09 (formalizado); 2026-05-11 (atualizado com 11 itens implementados)
**Substituído por:** —
**Relacionado:** ADR-001 (progressive correctness), ADR-003 (default deny PJ)

## Contexto

Parecer técnico-jurídico externo recebido em 2026-05-09 levantou
preocupações sobre go-live público:

- Threshold ≥5 contratos foi considerado heurística sem fundamento.
- Imutabilidade de `raw.compras` conflita com direito de eliminação
  (LGPD art. 18 IV).
- CNPJ de MEI/EI tecnicamente é dado pessoal (atrelado a CPF).
- Falta de documentação LGPD operacional (LIA, RIPD, política
  pública, canal do titular).

Resposta intuitiva seria atacar **um** ponto (ex: subir threshold pra
20). Isso falha tanto em segurança quanto em produto:

- Critério isolado é frágil — qualquer falha derruba a defesa inteira.
- Cobertura legal precisa de **conjunto coerente**: finalidade
  documentada + proporcionalidade + direitos operacionalizáveis +
  revisão externa.

## Decisão

Atacar a questão em **camadas independentes que se reforçam** (Wave
§18 — 15 itens, 11 técnicos implementados em 2026-05-11):

1. **Mascaramento de origem** (L.2): `analytics.fornecedor` classifica
   PJ vs MEI/EI; default deny no endpoint principal e em todos os
   derivados (ver ADR-003).
2. **Tombstones** (L.1): `analytics.eliminacao` registra eliminações;
   trigger marca `item_canonical.eliminada_em`; 5 MVs filtram. Raw
   permanece em `raw.snapshots` para auditoria contra falsificação.
3. **Audit log** (L.10): `analytics.audit_log` append-only com
   triggers cirúrgicos em tabelas com PD/regulado. Ator via
   `current_setting('app.audit_actor')`.
4. **Retenção formal** (L.9): doc + CLI dry-run + workflow mensal
   nunca destrutivo automático.
5. **Direitos operacionalizáveis** (L.12/L.13): `/correcoes` com
   ticket auditável `QP-AAAA-XXXX`, SLA por tipo, vitrine pública.
   Inclui revisão de decisão automatizada (art. 20).
6. **Transparência ativa** (L.5/L.6/L.7/L.11): Política, Termos,
   canal LGPD, disclaimers de origem em 5 páginas.
7. **Cobertura documental jurídica** (L.3/L.4/L.8): pendentes —
   requerem trabalho humano com advogado.
8. **Validação externa** (L.14/L.15): instituição-âncora + revisor
   jurídico independente.

Cada camada cobre uma classe diferente de falha (vazamento, drift,
desvio de finalidade, falha de processo, ausência de prova).

## Alternativas consideradas

- **Não fazer nada antes do go-live**: rejeitado — parecer externo é
  fundamentado e a janela de exposição é ampla.
- **Mascarar tudo agressivamente (não publicar perfil de fornecedor)**:
  rejeitado — destrói o produto. Fornecedor PJ contratando o governo
  é interesse social legítimo (LAI 12.527/2011).
- **Só atacar pontos com base legal forte (art. 18 IV) e ignorar
  defesa em camadas**: rejeitado — falha se uma única defesa cai.
- **Aguardar parecer jurídico final antes de implementar (L.15)**:
  rejeitado — implementação concreta dá ao revisor jurídico algo
  específico para avaliar; abstrato gera parecer abstrato.

## Consequências

**Positivas:**

- Cobre múltiplos vetores de risco (vazamento, drift, falha de
  processo, ausência de prova).
- Cada camada é **independentemente auditável**: audit_log mostra
  quando tombstone foi acionado; correção_ticket mostra quando direito
  foi exercido; analytics.fornecedor mostra qual heurística
  classificou cada CNPJ.
- Coloca o revisor jurídico (L.15) numa posição substantiva (revisar
  pacote técnico real) em vez de redigir do zero.

**Negativas / aceitas:**

- Custo de implementação: 11 itens em ~2 dias úteis. Mas exige
  manutenção contínua (heurística L.2 evolui pra dump RFB; SLA do
  ticket precisa ser cumprido na prática).
- Cobertura documental jurídica (L.3 LIA, L.4 RIPD, L.8
  subprocessadores) **não pode ser implementada por dev** — requer
  trabalho humano com conhecimento jurídico aplicado a LGPD cívica.
- Wave C.4 (Cloudflare + rate-limit + CORS) continua sendo bloqueante
  separado para go-live.

## Referências

- PLANO §18 inteiro (15 itens com aceite e tempo).
- Memórias `feedback_produto_legal`, `feedback_visibilidade_dados`.
- Commits: `af20e47` (L.1), `3d844d9` (L.2 v1 + L.10 + L.9.a),
  `2676bfb` (L.2.b + L.5/L.6/L.7 + L.11), `23af840` (L.12),
  `955d3dc` (L.13 + L.9.b + L.9.c).
