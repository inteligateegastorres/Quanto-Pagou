# Threat model — Quanto Pagou

**Versão:** v1 (2026-05-11)
**Escopo:** plataforma cívica de transparência sobre gastos públicos
brasileiros. Não tem login. Não armazena dado de visitante. Não é
e-commerce, não trata pagamento, não acessa documentação privada de
empresa nem dado pessoal não-público de cidadão.

Análise estruturada em [STRIDE](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats).
Foco nos vetores com **probabilidade × impacto** relevantes pro caso
específico.

---

## S — Spoofing (falsificação de identidade)

| Vetor | Probabilidade | Impacto | Mitigação atual |
|---|---|---|---|
| Atacante envia ticket de correção fingindo ser do titular | Média | Médio (mantenedor pode atender pedido de eliminação errado) | Mantenedor humano confirma identidade quando relevante (esp. `lgpd_eliminacao`). E-mail privado registrado no ticket dá retorno; rejeição registrada com motivo. |
| Atacante falsifica e-mail no header | Baixa | Médio | Idem; identificação não vale como prova de identidade sem confirmação. |
| Mantenedor compromete própria conta GitHub | Baixa | Alto (pode alterar tombstones/audit_log via SQL direto) | Branch protection em `main`, status checks obrigatórios, MFA obrigatório no GitHub (mantenedor). Snapshot bruto em `raw.snapshots` permanece — tampering em camadas derivadas é detectável. |

## T — Tampering (modificação não autorizada)

| Vetor | Probabilidade | Impacto | Mitigação atual |
|---|---|---|---|
| Atacante altera `raw.compras` para esconder contrato | N/A — fora de escopo (precisa de acesso ao banco) | Alto | Snapshot original em `raw.snapshots` com hash SHA-256; reproducível a partir de TCE-PR PIT público + Compras.gov.br. Auditoria contra falsificação preservada mesmo em tombstone (L.1 ADR-002). |
| Atacante altera `analytics.eliminacao` para ocultar exercício de direito | Baixa | Médio | Audit log (L.10) registra INSERT/UPDATE/DELETE com ator e timestamp; tabela append-only por convenção. Deleção de audit_log também é logada. |
| Drift de cobertura de cluster keyword silencioso | Média | Médio (jornalista usa dado incompleto) | `analytics.manchete_publicada` + `analytics.manchete_saida` registram entradas e saídas com hash do YAML. Quarentena visível (PLANO §17.0) — itens não-classificáveis aparecem com label, não somem. |

## R — Repudiation (negação de operação)

| Vetor | Probabilidade | Impacto | Mitigação atual |
|---|---|---|---|
| Mantenedor exclui contrato e nega que aconteceu | Baixa | Alto | Audit log (L.10) com `app.audit_actor` + base legal. `/eliminacoes/publicas` lista pública (sem reproduzir conteúdo). Snapshot bruto inalterável. |
| Reportador alega que nunca foi atendido | Baixa | Médio | Ticket público `/correcoes/{ticket_id}` com timeline visível ao próprio reportador, sem cadastro. Status workflow auditável. |
| Manchete algorítmica muda sem registro | Baixa | Médio | `manchete_publicada` + `manchete_saida` com hash da config aplicada. |

## I — Information disclosure (vazamento)

| Vetor | Probabilidade | Impacto | Mitigação atual |
|---|---|---|---|
| Perfil de MEI/EI exposto como PJ | **Média (até L.2)** → Baixa após L.2 | Alto (dado pessoal LGPD) | Default deny + heurística por sufixo (L.2/ADR-003). Helper `_require_pj_or_404` em 6 endpoints. MV `mart_fornecedores_municipio` filtra PJ na origem (defesa em camadas). 42% dos fornecedores ficam mascarados. |
| Servidor público nominado em payload bruto exposto na vitrine | Baixa | Médio | `raw_payload` JSONB não vai pra UI por padrão; só colunas dedicadas. Parser descarta endereço/telefone/e-mail pessoal (`data/PRIVACY.md` §2). |
| CPF mascarado pelo TCE-PR desmascarado por agregação | Baixa | Alto | Não desmascaramos. Agregação por nome distinguindo dois titulares com mesmo CPF mascarado garantida pelo unique index de `mart_fornecedores_municipio` incluir `fornecedor_nome`. |
| Secrets versionados acidentalmente | Baixa | Alto | `.env` em `.gitignore`, `.env.production.example` sem valores, Dependabot + gitleaks workflow em PR (2026-05-11). GitHub Secret Scanning ativo (configurado no painel). |
| Erro 500 vazando stack trace + connection string | Baixa | Alto | FastAPI default não vaza stack trace em produção. Logs estruturados pendentes (backlog). |
| Indexação Google de páginas com `/fornecedor/{cnpj}` antes do go-live | Baixa | Médio | `<meta name="robots" content="noindex, nofollow">` em todas as páginas sensíveis. PLANO §18.3 lista o critério explícito de quando ativar SEO público (depois de L.3/L.4/L.8/L.15 + Wave C.4). |

## D — Denial of service

| Vetor | Probabilidade | Impacto | Mitigação atual |
|---|---|---|---|
| Single request de scan caro derruba API | Média | Médio | Endpoints com `LIMIT` obrigatório e parâmetros validados via FastAPI. Partial indexes (Wave B.3) reduzem custo de drill-down em ~10×. |
| Scraping abusivo | Média (após go-live) | Médio | **Wave C.4 pendente**: Cloudflare na frente com rate-limit + WAF. Bloqueante pra go-live público (PLANO §18.3). |
| Ingestão semanal falha silenciosamente | Média | Médio | `ingest_with_split` (Wave A) faz window-splitting com retry e marca `failed` em `raw.snapshots` com `error_message` legível. Cron weekly tem `continue-on-error: true` em steps best-effort. Sentry pendente (backlog). |

## E — Elevation of privilege

| Vetor | Probabilidade | Impacto | Mitigação atual |
|---|---|---|---|
| SQL injection via parâmetros | Baixa | Alto | psycopg3 com prepared statements (`%s`) em todos os queries. Sem `f-string` ou `.format()` em SQL com input de usuário. |
| Subverter classificação `tipo_juridico` via valor enviado ao banco | N/A — usuário não escreve | Alto | Apenas job `fn_enriquecer_fornecedor` ou dump RFB escrevem. Trigger audit_log captura cada UPDATE. Coluna `fonte` versionada — dump RFB nunca sobrescreve a heurística sem ser explícito. |
| Server Action (Next 16) chamada com payload manipulado | Média | Médio | Validação em `actions.ts` valida tipo contra whitelist + `descricao.length >= 20` antes de POST pra API. API valida novamente via Pydantic (defesa em camadas). |
| XSS via descrição de contrato renderizada | Baixa | Alto | React/JSX escapa por padrão. Nenhum uso de `dangerouslySetInnerHTML` em conteúdo de usuário. |

---

## Riscos conhecidos não totalmente mitigados (backlog)

| Risco | Wave/ADR de origem | Plano |
|---|---|---|
| Rate-limit/WAF ausente | PLANO §17.C.4 | Cloudflare na frente — pré-go-live público |
| Sentry/logs estruturados ausentes | Backlog (esta análise) | Plug DSN + structlog — após DEPLOY.md inicial |
| Subprocessadores não catalogados formalmente | Wave LGPD L.8 | `docs/legal/SUBPROCESSADORES.md` — pendente |
| LIA e RIPD ausentes | Wave LGPD L.3 e L.4 | Trabalho com advogado especializado (L.15) |
| Heurística PJ pode ter falsos positivos residuais | ADR-003 | Dump RFB substituirá (`fonte='rfb_dump_AAAA-MM'`) |

## O que não modelamos (e por quê)

- **Ataque a infraestrutura de hosting** (Vercel/Supabase/Cloudflare):
  fora do escopo deste documento. Cada provider tem seu próprio
  threat model público.
- **Engenharia social do mantenedor** sem comprometer credencial: tem
  taxa-base baixa em projeto cívico pequeno e pouco visível. Reavaliar
  quando audiência crescer ou se receber instituição-âncora (L.14).
- **Insider threat de contribuidor com commit access**: mantenedor é
  único; bus factor já listado em PLANO §18.A L.14.

## Histórico de revisões

| Versão | Data | Mudança |
|---|---|---|
| v1 | 2026-05-11 | Versão inicial. Reflete Wave A/B/LGPD implementadas. |
