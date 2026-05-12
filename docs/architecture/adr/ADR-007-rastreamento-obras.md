# ADR-007 — Rastreamento de obras públicas: escopo e limites

**Status:** Aceito (decisão de escopo) — implementação técnica pendente em §19.1.b
**Data:** 2026-05-11
**Relacionado:** ADR-001 (progressive correctness), ADR-002 (defesa em camadas LGPD)

## Contexto

Análise externa de produto de 2026-05-11 listou "rastreamento de
obras públicas" como **Prioridade 1**, citando como sub-features
essenciais:

- mapa
- fotos
- cronograma
- empresa responsável
- aditivos
- prazo real vs previsto

Diagnóstico: obra parada é visível pra todos, concentra corrupção e
afeta diretamente o cidadão. Concordamos com o diagnóstico — mas as
sub-features têm origens muito diferentes e fazem sentido endereçar
separadamente.

Descoberta técnica do mesmo dia: TCE-PR PIT publica **`Obra.zip` por
município** (397 arquivos no ano 2025) — fonte que ainda não estávamos
ingerindo. Isso muda o que é viável fazer.

## Decisão

Implementar rastreamento de obras **usando apenas dado estruturado do
TCE-PR PIT**, sem dependência de scraping de portais municipais
heterogêneos.

Para cada sub-feature da P1, classificação explícita:

| Sub-feature P1 | Decisão | Razão |
|---|---|---|
| **Empresa responsável** | ✅ Implementar | `fornecedor_cnpj` já existe em `raw.compras`; obra terá vínculo análogo em `Obra.xml`. Aplicar defesa em camadas L.2 (PJ vs MEI/EI). |
| **Valor original do contrato** | ✅ Implementar | Provavelmente em `Obra.xml` (a investigar em §19.1.b passo 1). |
| **Aditivos (valor + data)** | ⚠️ Implementar SE existir no XML | Investigação preliminar §19.1.b passo 1 vai inventariar. Se TCE estrutura aditivo em XML separado ou como campo, expomos. Se não estrutura, documentamos o limite e não fabricamos. |
| **Prazo previsto** | ✅ Implementar (separado em §19.9) | `dt_inicio` e `dt_fim` já estão em `raw_payload` para Contrato; idem para Obra provavelmente. |
| **Prazo real / data de encerramento** | ⚠️ Proxy apenas | TCE não publica termo de encerramento estruturado. Usamos heurística "vencido = dt_fim < NOW() AND sem registro posterior". Documentar como proxy, não verdade. |
| **% executado** | ❌ Não implementar nesta fase | Provavelmente não está em XML estruturado. Se aparecer, expomos; senão, não fabricamos. |
| **Cronograma (etapas)** | ❌ Não implementar nesta fase | Mesma razão. |
| **Mapa (georreferenciamento)** | ❌ Não implementar nunca a partir desta fonte | TCE-PR PIT não traz coordenadas. Dependeria de scraping de portais municipais individuais — fragmentação alta, ToS variado, custo de manutenção desproporcional. |
| **Fotos** | ❌ Não implementar nunca a partir desta fonte | Mesma razão. Storage + moderação + verificação seriam outro projeto. Considerar pós-L.14 (instituição-âncora) como integração com aplicativo cidadão de terceiro. |

## Critério de "honesto" vs "completo"

A análise externa pediu o **conjunto completo** de funcionalidades.
Vamos entregar o **subset honestamente sustentável** — coerente com
ADR-001 (progressive correctness).

UI da página de obra deve deixar explícito:

> Esta página mostra dados estruturados de obras publicados pelo TCE-PR
> (PIT). O TCE-PR não publica fotos, mapa, % executado nem cronograma
> físico de forma estruturada — esses campos não aparecem aqui mesmo
> quando a obra existe na realidade. Para reportar uma obra parada
> ou divergente, use [/correcoes](/correcoes).

Isso é mais honesto que renderizar "% executado: dado não disponível"
em cada linha — o leitor poderia interpretar como "está em 0%".

## Alternativas consideradas

- **Implementar fotos + mapa via scraping de portais municipais**:
  rejeitado. Cada município tem portal diferente; lei municipal varia;
  ToS variado; manutenção destrói a equipe atual (1 mantenedor).
  Caso surja instituição-âncora (L.14) com capacidade de manter
  scrapers regionais, reabrir.
- **Implementar via integração com SIMEC/SIOP** (federal): rejeitado.
  Projeto é foco PR/Compras federal; SIMEC é federal de obras
  ministeriais. Considerar quando houver caso de uso jornalístico
  claro.
- **Aceitar upload de fotos por cidadão**: rejeitado nesta fase.
  Storage R2 + custo de moderação + verificação de autenticidade
  excede capacidade atual. Pode entrar pós-L.14 + Wave C.4
  (Cloudflare WAF) + decisão de produto explícita sobre verificação.

## Consequências

**Positivas:**

- Entrega o subset de P1 que é **realmente sustentável** — empresa,
  valor, prazo previsto. Cobre boa parte do impacto cívico (cidadão
  pode identificar quem é responsável e se passou do prazo).
- Limite claro: nada de "mostrar 0% executado quando o dado não
  existe".
- Migração futura para fonte com mais campos (instituição parceira,
  scraper municipal mantido por terceiro) é aditiva — não invalida
  o que está exposto agora.

**Negativas / aceitas:**

- Análise externa pode considerar "incompleto". Resposta documentada:
  P1 inclui itens que dependem de fontes externas inexistentes
  estruturadas, e implementação honesta > implementação cosmética
  com NULLs.
- Mapa e fotos eventualmente vão chegar via outra rota (parceria,
  aplicativo cidadão de terceiro com API). Documentar em ADR
  futuro quando o cenário existir.

## Referências

- PLANO §19.1.b (plano de implementação técnica detalhado).
- PLANO §19.9 (prazo previsto vs real usando dt_inicio/dt_fim já
  carregados).
- PLANO §19.10 (features deliberadamente fora — fotos, mapa, etc).
- ADR-001 (progressive correctness — base filosófica desta decisão).
