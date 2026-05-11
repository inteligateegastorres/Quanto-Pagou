# ADR-005 — Dual licensing: AGPL-3.0 (código) + CC-BY 4.0 (dados derivados)

**Status:** Aceito
**Data:** 2026-05-09 (LICENSE AGPL); 2026-05-11 (LICENSE-DATA CC-BY 4.0)
**Relacionado:** ADR-001 (progressive correctness)

## Contexto

Plataforma trabalha com 3 categorias distintas que precisam de
licença distinta:

1. **Código-fonte** — scripts Python, FastAPI, Next.js, SQL.
2. **Dados primários** — XMLs do TCE-PR, JSONs do Compras.gov.br.
3. **Dados derivados** — agregações, clusters, manchetes, perfis PJ,
   classificações, métricas estatísticas (mart_pares,
   cluster_discrepancias, etc).

Uma licença única não funciona:

- AGPL nos dados derivados não faz sentido (dados não são "software"
  no sentido da GPL).
- CC-BY no código gera ambiguidade jurídica.
- MIT/Apache no código permite captura privada (alguém pega o
  pipeline, vende como SaaS fechado sem contribuir de volta) — risco
  real em ferramentas cívicas.
- Sem licença explícita = retenção total de direitos autorais →
  inutilizável.

## Decisão

**Tripla configuração explícita:**

| Categoria | Licença | Arquivo |
|---|---|---|
| Código-fonte | **AGPL-3.0** | `LICENSE` (raiz) |
| Dados derivados | **CC-BY 4.0** | `LICENSE-DATA` (raiz) |
| Dados primários (TCE-PR, Compras.gov.br) | **Domínio público** (LAI 12.527/2011 + LC 131/2009) | Não licenciado por nós; ver `/termos` |

Frontend (`frontend/`) tem licença separada **MIT** (`frontend/LICENSE`)
pra facilitar reuso em outros frontends cívicos. Foi decisão deliberada
da Wave A.

### Por que AGPL e não MIT/Apache no código

Captura privada típica em ferramentas cívicas brasileiras:

- Empresa pega pipeline de transparência open-source.
- Adiciona scraping + cache + UI proprietária.
- Vende como SaaS para órgão público (que poderia rodar o original
  gratuito).
- Open-source original ganha 0; cidadão paga 2× (impostos + SaaS).

AGPL fecha esse loop: usar via rede em SaaS exige publicar
modificações. Reduz incentivo à captura sem proibir uso pessoal,
acadêmico ou em ONG.

### Por que CC-BY 4.0 e não ODbL nos dados derivados

ODbL (Open Database License) é tecnicamente mais correta pra "banco
de dados", mas:

- Cláusula de "share-alike" do ODbL gera dúvida jurídica quando
  combinado com analítica derivada.
- CC-BY 4.0 é universalmente entendido por jornalistas e ONGs —
  baixa fricção de adoção.
- Atribuição é o requisito real; share-alike de dados cívicos não é
  necessário (queremos que jornal use, mesmo em conteúdo proprietário).

## Atribuição sugerida

Quando reutilizar dados derivados:

> Dados derivados de Quanto Pagou (quantopagou.org), CC-BY 4.0, a
> partir de TCE-PR/PIT e Compras.gov.br (dados públicos).

## Alternativas consideradas

- **MIT em tudo**: rejeitado — abre captura privada (ver acima).
- **Sem licença explícita**: rejeitado — inutilizável legalmente.
- **CC0 nos dados**: rejeitado — perde a atribuição, que é o único
  requisito que sustenta credibilidade pública. CC-BY mantém
  rastreabilidade da fonte sem restringir uso.
- **Apache 2.0**: rejeitado pelo mesmo motivo do MIT.
- **GPL (sem A)**: rejeitado — produto é serviço web, AGPL é o caso
  específico que cobre uso remoto.

## Consequências

**Positivas:**

- Compatível com uso jornalístico (CC-BY) e com fork open-source de
  outras ONGs (AGPL).
- Empresa que queira encapsular o pipeline em SaaS comercial precisa
  publicar modificações → reduz incentivo à captura privada.
- Atribuição mantém ecossistema de credibilidade (quem citar Quanto
  Pagou linka de volta).

**Negativas / aceitas:**

- AGPL afasta empresas que queiram integrar comercialmente o código
  fechado. Decisão deliberada — não somos um produto comercial.
- Necessidade de manter `LICENSE-DATA` separado e referenciá-lo em
  `/termos` (L.6 da Wave LGPD).

## Referências

- `LICENSE` (raiz, AGPL-3.0).
- `LICENSE-DATA` (raiz, CC-BY 4.0).
- `frontend/LICENSE` (MIT).
- `frontend/app/termos/page.tsx` (página pública dos Termos).
- Wave A.1+A.2 (commit `4d3298b`), Wave LGPD L.6.
