# Architecture Decision Records (ADRs)

Diretório de **decisões arquiteturais relevantes** do Quanto Pagou.
Cada ADR documenta uma decisão tomada, o contexto que a motivou, as
alternativas consideradas e as consequências aceitas.

Formato inspirado em [Michael Nygard, 2011](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

## Convenções

- Arquivos numerados sequencialmente: `ADR-NNN-slug.md`.
- Status: `Proposto`, `Aceito`, `Substituído por ADR-XXX`, `Obsoleto`.
- Mudanças significativas em ADR aceitos = novo ADR que substitui o
  anterior (preserva história). Não editar ADR aceito além de erratas
  e link de "Substituído por".
- Granularidade: decisões com **trade-off real**. Refactors óbvios e
  microajustes não viram ADR.

## Índice

| # | Título | Status |
|---|---|---|
| [001](./ADR-001-progressive-correctness.md) | Progressive correctness (maturidade técnica é destino, não ponto de partida) | Aceito |
| [002](./ADR-002-defesa-em-camadas-lgpd.md) | Defesa em camadas LGPD (Wave §18) | Aceito |
| [003](./ADR-003-default-deny-pj-vs-mei.md) | Default deny para distinção PJ vs MEI/EI (L.2) | Aceito |
| [004](./ADR-004-ticket-auditavel-correcoes.md) | Ticket auditável `QP-AAAA-XXXX` para correções (L.12/L.13) | Aceito |
| [005](./ADR-005-dual-licensing.md) | Dual licensing — AGPL-3.0 código + CC-BY 4.0 dados | Aceito |

## Threat model

Análise complementar em [`THREAT_MODEL.md`](../THREAT_MODEL.md).
