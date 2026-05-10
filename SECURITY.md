# Política de Segurança

## Escopo

O Quanto Pagou serve **dados públicos** (contratos do TCE-PR e
Compras.gov.br). Não há autenticação no MVP — por design. Isto não é
uma vulnerabilidade.

Considere vulnerabilidades válidas:

- **Vazamento de dado privado** que conseguiu entrar no banco (ex: CPF
  não-mascarado, endereço pessoal). Apesar do filtro de mascaramento,
  pode ter buracos.
- **Escalada de queries arbitrárias** (SQL injection, command injection)
  via parâmetros de busca.
- **Bypass do guardrail §6.5** que permita expor perfil de fornecedor
  com < 5 contratos.
- **Cross-site scripting** em descrições de contratos renderizadas no
  frontend.
- **Leitura de credenciais** (secrets do GitHub Actions, env vars de
  produção, hash de senha de DB) por qualquer caminho.
- **Drift de auditoria**: manchete sendo alterada sem registro em
  `analytics.manchete_publicada` ou `analytics.manchete_saida`.
- **Negação de serviço barata** (request único que custa muito).

Considere fora de escopo:

- API pública sem rate-limit (planejado: Cloudflare na frente — vide
  PLANO §17.C). Reportar mesmo assim se tiver vetor crítico.
- Ausência de CORS allowlist (mesmo motivo).
- Bugs visuais no frontend (vão pra issues normais).
- Drift de cobertura do cluster keyword (esse é o ponto de v1).

## Como reportar

**Por enquanto** (até a organização GitHub estar formalizada e o canal
oficial existir):

- E-mail: `contato@quantopagou.org`
- Assunto: `[security] <descrição curta>`
- Inclua: passos para reproduzir, impacto estimado, e se já está em uso
  prod (se aplicável).

**Não abra issue pública** para vulnerabilidades de segurança. Use o
canal acima primeiro.

## SLA

- **Acuso de recebimento:** até **5 dias úteis**.
- **Triagem inicial:** até **10 dias úteis** (severidade + escopo).
- **Correção** (vulnerabilidades graves: vazamento de dado privado,
  SQL injection): até **30 dias** ou disclosure coordenado.
- **Crédito público** ao reporter (se quiser) na seção de agradecimentos
  do `/correcoes` ou release notes.

## O que esperar de volta

- Resposta humana, não auto-reply.
- Pergunta de esclarecimento, se necessário, **antes** de fechar.
- Status updates a cada 2 semanas durante a investigação.
- Versão corrigida pública + entrada em
  [`/correcoes`](http://127.0.0.1:3001/correcoes) (e equivalente em prod).

## Bug bounty

Não temos bounty financeiro. Plataforma cívica sem orçamento. Mas:
crédito público + carta de recomendação (se quiser) + nosso muito
obrigado em prosa.

---

Última atualização: 2026-05-09. Política sujeita a evolução. Mudanças
relevantes são anunciadas em [PLANO.md](./PLANO.md) §14 (changelog).
