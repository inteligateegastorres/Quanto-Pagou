# ADR-001 — Progressive correctness

**Status:** Aceito
**Data:** 2026-04-02 (princípio); formalizado 2026-05-11
**Autores:** Egas Torres

## Contexto

Plataformas cívicas brasileiras de transparência tradicionalmente
adotam dois caminhos extremos:

1. **Engenharia perfeccionista** — espera-se cobertura 100%, modelo de
   dados imutável, validação rigorosa antes do lançamento. Resultado:
   raramente saem do nicho técnico, perdem janela política, abandono
   por exaustão do mantenedor.
2. **Lançamento sem honestidade técnica** — publica com cobertura
   parcial sem explicitar limites; primeiro erro grande quebra
   credibilidade.

Quanto Pagou começou com 90 contratos federais em fixture sintética e
ambicionava cobrir TCE-PR + Compras.gov.br + Querido Diário. Tentar
fechar tudo antes de publicar produziria meses sem entrega visível.

## Decisão

Adotar **progressive correctness**: publicar com cobertura imperfeita
declarando precisão/recall + escopo + lacunas explicitamente, e
melhorar em ondas mensuráveis. Maturidade técnica é destino, não ponto
de partida.

Aplicações concretas:

- **Threshold ≥5 contratos** para gerar perfil de fornecedor.
  Reconhece que fornecedor eventual tem alto ruído sem fingir solução
  perfeita.
- **Quarentena visível com motivo legível** em vez de filtrar itens
  não-classificáveis silenciosamente (ver [memória `feedback_visibilidade_dados`](../../../README.md)).
- **Cluster keyword `confianca=0.6`** (TCE-PR) é menor que o threshold
  federal de 0.75 — declarado em UI, não escondido.
- **L.2 heurística por sufixo** (Wave LGPD) marca PJ confirmado quando
  inequívoco; tudo o resto fica NULL e mascarado por default deny. Não
  pretende ser autoritativo — fonte versionada permite dump RFB
  substituir depois.
- **L.9.c workflow mensal** roda sempre em **dry-run** automático;
  apply só via dispatch manual após validação humana. Não destrutivo
  por default.

## Alternativas consideradas

- **Modelo perfeccionista** rejeitado: bloqueio até dump RFB completo
  + LIA estruturada + revisor jurídico = ~3 meses sem entrega visível.
  Janela política da transparência é curta — quem não está no ar perde.
- **Ship-it-and-fix-later sem honestidade** rejeitado: gera *Painel de
  Preços v1* do governo federal — site existe mas ninguém usa porque
  números não batem e não há disclaimer.

## Consequências

**Positivas:**

- Lançamentos contínuos com escopo declarado.
- Críticas externas batem em pontos reconhecidos (não negação).
- Backlog explícito (PLANO §17/§18) substitui "promessa de futuro
  vago".

**Negativas / aceitas:**

- Sempre haverá lacunas visíveis. Atrai crítica de "ainda não está
  pronto" — esperado e tolerado.
- Exige disciplina pra **não pular degraus** (ex: não ativar SEO antes
  de Wave LGPD completar).

## Referências

- Memória `feedback_progressive_correctness`.
- PLANO §17 (Wave A/B/C), §18 (Wave LGPD).
- README seção "Estado atual".
