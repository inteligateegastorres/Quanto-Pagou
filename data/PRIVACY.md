# Política de Privacidade — Quanto Pagou

> **Versão v2 (2026-05-11) — pendente revisão jurídica externa (PLANO
> §18 L.15) antes do go-live público.**
>
> Este documento descreve a postura atual do projeto em relação à
> proteção de dados, com base na **Lei Geral de Proteção de Dados
> Pessoais (LGPD — Lei 13.709/2018)**. Página web equivalente em
> `/politica-privacidade` (PLANO §18 L.5). Em caso de divergência,
> prevalece a versão com timestamp mais recente.
>
> **Mudanças v1→v2:** integra Wave LGPD §18 (L.1 tombstones, L.2
> distinção PJ vs MEI/EI, L.9 retenção formal, L.10 audit log, L.12
> ticket de correções, L.13 contestar decisão automatizada). Conteúdo
> conceitual inalterado.

---

## 1. O que tratamos

Apenas **dados públicos** publicados pelos próprios órgãos de controle:

- **TCE-PR (PIT):** ZIPs anuais públicos em
  `pit.tce.pr.gov.br/Arquivos/{ano}_PIT_TodosArquivos.zip` (sem
  cadastro). Contém contratos, fornecedores (CNPJ + nome) e órgãos.
- **Compras.gov.br:** API pública `dadosabertos.compras.gov.br` (sem
  cadastro). Hoje em fixture sintética (90 contratos federais);
  ingestão real volta quando o backend deles estabilizar.
- **IBGE Censo 2022:** população por município (dado público).

Não coletamos: cookies de rastreamento, dados pessoais de visitantes,
formulários de cadastro, IP além de log padrão de servidor (sob
política do hosting).

## 2. Categorias de dado pessoal envolvidas

| Tipo | Origem | Como tratamos |
|---|---|---|
| **CNPJ de pessoa jurídica** | TCE-PR / Compras.gov.br | Publicado integralmente — é dado público de empresa, não pessoal LGPD |
| **CNPJ de Microempreendedor Individual (MEI) ou Empresário Individual (EI)** | Idem | **Mascarado por padrão (PLANO §18 L.2)** — `analytics.fornecedor` classifica por sufixo do nome (LTDA, S.A., EIRELI, COOPERATIVA, etc); só PJ confirmada gera perfil público. NULL ou MEI/EI/PF → endpoint `/fornecedor/{cnpj}` retorna 404 com mensagem explicativa e gancho para `/correcoes` |
| **CPF mascarado pelo TCE-PR** | TCE-PR (já vem mascarado: `***.017.***-**`) | Publicado como veio. Não desmascaramos. |
| **Nome de fornecedor pessoa física** | TCE-PR | Publicado quando vinculado a contrato público (interesse legítimo, art. 7º X LGPD) |
| **Endereço, telefone, e-mail pessoal** | — | **Não coletamos**. Se aparecer no XML do TCE, descartamos no parser. |

## 3. Base legal (LGPD art. 7º)

Tratamos com fundamento em:

- **Inciso II — cumprimento de obrigação legal**: a Lei de Acesso à
  Informação (12.527/2011) e a Lei de Transparência (Lei Complementar
  131/2009) **obrigam** os órgãos públicos a publicar esses dados.
  Nosso tratamento dá efetividade ao direito do cidadão à informação.
- **Inciso V — exercício regular de direitos em processo administrativo**:
  facilitar controle social sobre gasto público é exercício do direito
  constitucional do cidadão (CF art. 5º XXXIII e art. 37).
- **Inciso IX — interesse legítimo**: monitorar gasto público é interesse
  cívico legítimo, ponderado contra o impacto sobre o titular (que aqui
  é mínimo, dado que o dado já é público).

## 4. Salvaguardas em camadas

Para perfis de fornecedor pessoa jurídica:

1. **Threshold mínimo:** perfil só é gerado para fornecedor com
   **≥ 5 contratos públicos** registrados (`_FORNECEDOR_THRESHOLD = 5`
   em `src/api/main.py`). Reduz exposição de fornecedor eventual.
2. **Distinção PJ vs MEI/EI/PF (PLANO §18 L.2):** `analytics.fornecedor`
   classifica por sufixo do nome; helper `_require_pj_or_404` gateia
   todos os endpoints `/fornecedor/{cnpj}/*`. MV
   `mart_fornecedores_municipio` filtra `tipo_juridico='PJ'` na
   origem. Fonte versionada (`heuristica_sufixo_v1` agora; dump RFB
   substituirá depois).
3. **Tombstones — direito de eliminação art. 18 IV (PLANO §18 L.1):**
   `analytics.eliminacao` registra solicitações atendidas; trigger
   sincroniza `item_canonical.eliminada_em`; 5 MVs filtram
   automaticamente; `/contrato/{raw_id}` retorna 410 Gone se
   eliminado; `/eliminacoes/publicas` lista IDs + motivo + fundamento
   sem reproduzir conteúdo. Snapshot raw em `raw.snapshots` preservado
   (auditoria contra falsificação).
4. **`noindex, nofollow`** no `<head>` da página `/fornecedor/{cnpj}` —
   não aparece em busca do Google.
5. **Modal "como interpretar"** obrigatório — explicita que presença
   na plataforma **não implica irregularidade**.
6. **Linguagem factual** — não usamos "suspeito", "irregular" ou
   "desviado" em UI. Mostramos números + fonte primária + intervalo
   p25-p75. Cabe ao leitor interpretar.
7. **Mascaramento de CPF** mantido — não desmascaramos o que o TCE-PR
   já mascarou.
8. **Audit log art. 37 (PLANO §18 L.10):** `analytics.audit_log`
   append-only com triggers cirúrgicos em `analytics.eliminacao`,
   `item_canonical` (só quando `eliminada_em` muda), `fornecedor` e
   `correcao_ticket`. Ator capturado via
   `current_setting('app.audit_actor')`.
9. **Direito à revisão de decisão automatizada art. 20 (PLANO §18
   L.13):** botão "Contestar este ranking" em `/manchetes`, `/cluster/*`
   e `/fornecedor/*` abre `/correcoes` pré-preenchido com tipo
   `revisao_ranking` (SLA 15d). Resposta humana documentada.
10. **Manchetes algorítmicas (PLANO §15)** **não publicam sobre
    fornecedor** no v1. Manchetes são sempre sobre (cluster ×
    município) — entes públicos, não privados. Decisão registrada com
    motivo (risco jurídico de difamação por inferência).

## 5. Retenção

Política completa em [`docs/legal/RETENCAO.md`](legal/RETENCAO.md)
(PLANO §18 L.9.a). Resumo:

- **Snapshots brutos** (`raw.snapshots`, R2): retenção indefinida
  (imutáveis, audit trail contra falsificação).
- **`raw.compras.raw_payload`** (JSONB redundante): 90 dias após
  canonicalização validada. Script CLI
  `scripts/expurgar_raw_payload.py` (PLANO §18 L.9.b) com `--dry-run`
  default seguro + `--apply` em batches; workflow GH Actions
  `expurgar-mensal.yml` (L.9.c) roda mensalmente em dry-run, apply
  só via dispatch manual após ≥1 ciclo humano validado.
- **`analytics.audit_log`** (L.10): 5 anos (prescrição LGPD art. 52
  §1º + tolerância).
- **Camada canônica** (`item_canonical`, marts, manchetes): atualizada
  semanalmente; substitui a anterior. `manchete_publicada` preserva
  histórico para auditoria (2 anos).
- **`analytics.eliminacao`** e **`analytics.correcao_ticket`**:
  retenção indefinida (prova de cumprimento de direitos do titular,
  art. 37 LGPD).
- **Logs de servidor**: retidos pelo hosting (Vercel/Fly.io) conforme
  política — geralmente ≤ 30 dias.

## 6. Direitos do titular (LGPD art. 18 + art. 20)

Qualquer titular de dado pessoal pode exercer os direitos do art. 18:
acesso, correção, anonimização, portabilidade, eliminação, informação
sobre tratamento, revogação de consentimento, oposição. Além disso,
art. 20 garante revisão de decisões automatizadas.

**Canal de contato:**
- **Formulário web (preferido):** [/correcoes](https://quantopagou.org/correcoes) (PLANO §18 L.12).
  Gera ticket público `QP-AAAA-XXXX` acompanhável sem cadastro em
  `/correcoes/{ticket_id}`. Tipos pré-categorizados (factual,
  lgpd_acesso, lgpd_correcao, lgpd_eliminacao, classificacao_pj,
  revisao_ranking).
- **E-mail (alternativo):** `lgpd@quantopagou.org` (assunto `[LGPD] <pedido>`).
  Página detalhando direitos em [/lgpd](https://quantopagou.org/lgpd).

**Tipos de pedido típicos:**

| Pedido | Tipo no ticket | SLA | Como tratamos |
|---|---|---|---|
| **Correção de dado errado** (CNPJ atribuído a empresa errada, modalidade incorreta) | `factual` | 48h | Investigamos. Se confirmado, corrigimos no banco e registramos no ticket com delta antes→depois. Auditoria via `analytics.audit_log`. |
| **Acesso, correção ou eliminação de dado pessoal** (art. 18 II/III/IV) | `lgpd_acesso` / `lgpd_correcao` / `lgpd_eliminacao` | 15 dias (art. 19) | Avaliação caso a caso. Eliminação via tombstone (L.1) preserva snapshot bruto, remove conteúdo da vitrine. |
| **Perfil de PJ indevidamente bloqueado ou exposto** (classificação heurística L.2 errou) | `classificacao_pj` | 15 dias | Ajustamos `analytics.fornecedor.tipo_juridico` com `fonte='manual_correcao'` (não sobrescreve futuras cargas RFB). |
| **Contestar manchete ou ranking** (art. 20 §1º decisão automatizada) | `revisao_ranking` | 15 dias | Revisão humana documentada no ticket. Disponível via botão "Contestar este ranking" em `/manchetes`, `/cluster/*`, `/fornecedor/*`. |
| **Pedido de remoção total** de uma empresa PJ | — | — | Não atendemos sem ordem judicial — dado público de gasto público é interesse social legítimo. Direito de **resposta pública** garantido via `/correcoes`. |
| **Acesso aos dados** sobre uma entidade | — | — | Já é público — toda página `/fornecedor/`, `/municipio/`, `/contrato/` mostra tudo o que temos. |

## 7. Encarregado (DPO)

Projeto adota **autodeclaração de pequeno porte** conforme **Resolução
CD/ANPD nº 2/2022, art. 11 II** — sem CNPJ formal, sem funcionários
e sem fins lucrativos, não há obrigação de nomear DPO formal.

**Mantenedor responsável:** Egas Torres · `lgpd@quantopagou.org`.

Após instituição-âncora confirmada (PLANO §18 L.14) e/ou crescimento
que descaracterize pequeno porte, nomearemos DPO formal aqui e em
[/lgpd](https://quantopagou.org/lgpd).

## 8. Compartilhamento e licença

Não compartilhamos dados pessoais com terceiros para fins comerciais.
**Toda a base é pública** — qualquer pessoa pode reproduzir nosso
pipeline a partir do código + snapshots versionados.

- **Código-fonte:** AGPL-3.0 (`LICENSE` na raiz).
- **Dados derivados** (agregações, manchetes, perfis PJ, classificações):
  CC-BY 4.0 (`LICENSE-DATA` na raiz; Termos em
  [/termos](https://quantopagou.org/termos) — PLANO §18 L.6).
- **Dados primários** (TCE-PR, Compras.gov.br): domínio público sob
  LAI/Lei de Transparência. Não licenciados por nós.

Hosting (Vercel, Supabase, Cloudflare R2, Fly.io) processa os dados
sob seus próprios termos — todos aderentes à LGPD/GDPR. Catálogo
completo pendente em `docs/legal/SUBPROCESSADORES.md` (PLANO §18 L.8).

## 9. Cookies e rastreadores

Não usamos cookies de rastreamento, pixels de Facebook/Google, ou
analytics que identifique visitante individualmente.

Consideramos adicionar **Plausible** (analytics agregado, sem cookie,
GDPR-compliant) na Fase 1 para entender uso. Será documentado aqui
antes de ativar.

## 10. Mudanças nesta política

Mudanças relevantes geram entrada no [PLANO.md §14 (changelog)](../PLANO.md)
e ficam registradas no `git log` deste arquivo. Última atualização no
topo deste documento.

---

## Reportar problema de privacidade ou erro de dado

- **Erro de dado** (CNPJ errado, valor errado, classificação incorreta):
  página [/correcoes](https://quantopagou.org/correcoes) gera ticket
  público `QP-AAAA-XXXX` (PLANO §18 L.12). SLA 48h para fato.
- **Direito LGPD** (art. 18 ou 20): mesmo formulário com tipo
  `lgpd_*` ou `revisao_ranking`, ou e-mail
  `lgpd@quantopagou.org` assunto `[LGPD]`. SLA 15 dias (art. 19).
  Página dedicada em [/lgpd](https://quantopagou.org/lgpd) (PLANO §18 L.7).
- **Vulnerabilidade de privacidade** (vazamento): leia
  [SECURITY.md](../SECURITY.md) e use o canal de segurança.

---

## Histórico de revisões

| Versão | Data | Mudança |
|---|---|---|
| v1 | 2026-05-09 | Versão inicial (Wave A.6). |
| v2 | 2026-05-11 | Integra Wave LGPD §18 (L.1, L.2, L.5–L.7, L.9, L.10, L.11, L.12, L.13). |
