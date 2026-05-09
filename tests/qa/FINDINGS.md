# QA Findings — Quanto Pagou

Registro de problemas encontrados durante execução do
[`CHECKLIST.md`](./CHECKLIST.md).

> **Regras:**
> - Uma entrada por bug observado. Não agrupar.
> - **Não consertar.** Só descrever.
> - Se você acha que não é bug e sim "intencional, mas estranho",
>   registre mesmo assim como `severity: question`.

---

## Template de entrada (copie + cole pra cada finding)

````markdown
### F-NNN: [título curto e específico]

- **Categoria:** infra | api | frontend | drill-down | guardrail | ux | docs | edge-case | performance | data | question
- **Severidade:** critical | high | medium | low | question
  - `critical`: stack down, dado errado em produção, regressão de invariante (§6.5, quarentena, cluster_version)
  - `high`: feature principal quebrada (busca, comparação, perfil)
  - `medium`: feature secundária quebrada, ou erro em edge case provável
  - `low`: cosmético, copy, link errado, edge case improvável
  - `question`: comportamento ambíguo — pede decisão de produto
- **Onde:** URL ou endpoint exato (`/instituicoes?q=UPA`, `GET /stats/pr`)
- **Item do checklist:** seção e número (`§1.6`, `§3 drill-down /comparar`)

**Reprodução:**

1. Passo
2. Passo
3. Passo

**Esperado:**

> O que deveria acontecer (idealmente cite o item do checklist ou a
> documentação relevante).

**Observado:**

> O que aconteceu de fato. Cole o trecho relevante do payload, do erro,
> ou descreva o estado da UI.

```
[trecho de log / payload / erro, se aplicável]
```

**Hipótese de causa raiz** (opcional, só se óbvia):

> Linha X do arquivo Y parece estar fazendo Z em vez de W.

**Sugestão de fix** (opcional, só se trivial):

> Trocar `foo` por `bar` em `arquivo.ts:123`.

````

---

## Findings registrados

<!-- A IA executora preenche abaixo. Mantém numeração contínua F-001, F-002, ... -->

(nenhum ainda — preencher durante execução)

---

## Resumo final

A IA executora preenche este bloco quando concluir o checklist:

- **Itens marcados ✅:** ___
- **Itens marcados ❌:** ___
- **Itens não testados** (ex: stack offline impediu): ___
- **Total de findings registrados:** ___
- **Tempo total da execução:** ___

### Top 3 prioridades

1. **F-___** — descrição curta de 1 linha
2. **F-___** —
3. **F-___** —

### Notas livres

> Coisas que não cabem em finding individual: padrões observados,
> ambiguidades sistêmicas, sugestões de cobertura para próxima rodada
> de QA.
