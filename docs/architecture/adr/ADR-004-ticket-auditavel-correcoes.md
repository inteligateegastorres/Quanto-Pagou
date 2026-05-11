# ADR-004 — Ticket auditável `QP-AAAA-XXXX` para correções e direitos do titular

**Status:** Aceito
**Data:** 2026-05-11
**Relacionado:** ADR-002 (defesa em camadas LGPD)

## Contexto

Versão pré-Wave LGPD da rota `/correcoes` era um `<form>` HTML com
`action="mailto:contato@quantopagou.org"`. Problemas:

- Fluxo sem persistência → não tem como o reportador acompanhar
  status sem checar e-mail privado.
- Sem prazo declarado → não há SLA mensurável.
- Sem auditoria → cumprimento de direitos LGPD (art. 18) precisa de
  prova de recebimento + processamento.
- Sem vitrine pública → "página de correções" prometia transparência
  que o produto não entregava.
- `mailto:` é vulnerável a spam e a indisponibilidade do cliente de
  e-mail do reportador.

Parecer externo (L.12 do PLANO §18) explicitou que canal formal é
bloqueante.

## Decisão

Implementar tabela `analytics.correcao_ticket` com:

- **ID público** `QP-AAAA-XXXX` (ano + 4 hex aleatórios, gerador com
  retry contra colisão). Não-sequencial — não vaza volume de tickets
  recebidos.
- **Categorização por tipo** (`factual`, `lgpd_acesso`,
  `lgpd_correcao`, `lgpd_eliminacao`, `classificacao_pj`,
  `revisao_ranking`, `outro`).
- **SLA derivado do tipo**:
  - `factual_48h` — correção de fato verificável.
  - `lgpd_15d` — pedidos LGPD (art. 18) e revisão de decisão
    automatizada (art. 20), conforme art. 19.
- **Flag `publicar_descricao`** (default `FALSE`): reportador controla
  se a descrição vai pra vitrine pública dos resolvidos.
- **Status workflow auditável**: `aberto` → `em_analise` →
  `resolvido_corrigido` / `resolvido_sem_correcao` / `rejeitado`.
- **Audit log** (L.10) via trigger AFTER INSERT/UPDATE/DELETE.

Endpoints públicos:

- `POST /correcoes/ticket` — cria + retorna ticket completo.
- `GET /correcoes/ticket/{ticket_id}` — consulta sem cadastro.
- `GET /correcoes/recentes` — vitrine pública dos resolvidos.

Frontend:

- `/correcoes` com Server Action `criarTicketAction` que valida +
  chama POST + redireciona pra página pública do ticket.
- `/correcoes/[ticket_id]` com `noindex/nofollow`, status colorido,
  prazo nominal, badge "Prazo vencido" quando vencido sem resposta —
  auditoria de SLA visível ao próprio reportador.

Para o **direito à revisão de decisão automatizada** (LGPD art. 20):

- Tipo `revisao_ranking` reusa o pipeline com SLA 15d.
- Componente `BotaoContestarRanking` em `/manchetes`, `/cluster/*`,
  `/fornecedor/*` gera link pra `/correcoes` pré-preenchido com tipo
  + url + contexto. Form aceita `searchParams` e usa `defaultValue`.

## Privacidade

- **E-mail do reportador nunca sai do banco** (auditável apenas via
  `analytics.audit_log` interno).
- **Descrição** só vai pra vitrine pública (`/correcoes/recentes`)
  quando `publicar_descricao=TRUE` OU enquanto o ticket está ativo
  (reportador precisa ver o que reportou).
- **Ticket público mostra apenas**: ID, tipo, SLA, status, prazo,
  referências cruzadas (raw_id, cnpj se houver), e `resolucao_publica`
  quando o mantenedor preenche.

## Alternativas consideradas

- **Manter `mailto:`**: rejeitado — falha em todos os critérios acima.
- **Issue tracker do GitHub**: rejeitado — exige conta GitHub, vaza
  e-mail dos reportadores em commits relacionados, não dá pra
  controlar privacidade da descrição.
- **Serviço externo (Linear, JIRA)**: rejeitado — vendor lock-in,
  custo, exfiltra dados pra terceiros sem fundamento.
- **Schema separado por tipo (tabela LGPD distinta de tabela
  factual)**: rejeitado — fragmentação, audit log duplicado,
  duplicação de workflow.

## Consequências

**Positivas:**

- Direitos do titular (art. 18 + art. 20) com SLA mensurável e
  auditoria pública.
- Workflow auditável de ponta a ponta via `analytics.audit_log` (L.10).
- Vitrine pública (`resolucao_publica`) vira ativo de credibilidade —
  página de correções deixa de ser promessa.
- Reusa pipeline existente: ticket único pra todos os tipos.

**Negativas / aceitas:**

- Spam: sem CAPTCHA atualmente. Mitigado por Wave C.4 (Cloudflare
  rate-limit) pré-go-live.
- Resolução automática não existe — todo ticket precisa de mantenedor
  humano. Aceitável para escala atual (zero tickets/dia).
- Workflow status só evolui por backoffice (CLI ainda não escrito —
  vai precisar quando o primeiro ticket real chegar).

## Referências

- `sql/011_correcoes.sql`, `sql/012_correcao_revisao_ranking.sql`.
- `src/api/main.py` (`POST /correcoes/ticket` etc.).
- `frontend/app/correcoes/actions.ts`, `[ticket_id]/page.tsx`,
  `lib/correcoes.ts`, `lib/BotaoContestarRanking.tsx`.
- PLANO §18 L.12 e L.13.
