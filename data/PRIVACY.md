# Política de Privacidade — Quanto Pagou

> **Versão v1 (2026-05-09) — pendente revisão jurídica antes do go-live público.**
>
> Este documento descreve a postura atual do projeto em relação à
> proteção de dados, com base na **Lei Geral de Proteção de Dados
> Pessoais (LGPD — Lei 13.709/2018)**. Será revisada por advogado
> especializado antes do lançamento em domínio público.

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
| **CNPJ de Microempreendedor Individual (MEI)** | Idem | Publicado — MEI é PJ, mas atrelado a CPF; mascaramos quando o TCE-PR já mascara (campo `cnpj_mascarado=true`) |
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
2. **`noindex, nofollow`** no `<head>` da página `/fornecedor/{cnpj}` —
   não aparece em busca do Google.
3. **Modal "como interpretar"** obrigatório — explicita que presença
   na plataforma **não implica irregularidade**.
4. **Linguagem factual** — não usamos "suspeito", "irregular" ou
   "desviado" em UI. Mostramos números + fonte primária + intervalo
   p25-p75. Cabe ao leitor interpretar.
5. **Mascaramento de CPF** mantido — não desmascaramos o que o TCE-PR
   já mascarou.
6. **Manchetes algorítmicas (PLANO §15)** **não publicam sobre
   fornecedor** no v1. Manchetes são sempre sobre (cluster ×
   município) — entes públicos, não privados. Decisão registrada com
   motivo (risco jurídico de difamação por inferência).

## 5. Retenção

- **Snapshots brutos** (raw.snapshots, R2): mantidos indefinidamente
  como audit trail. São cópias do que o órgão publicou, não dado novo
  nosso.
- **Camada canônica** (item_canonical, marts, manchetes): atualizada
  semanalmente; substitui a anterior. O `analytics.manchete_publicada`
  preserva histórico de manchetes ativas para auditoria.
- **Logs de servidor**: retidos pelo hosting (Vercel/Fly.io) conforme
  política dele — geralmente ≤ 30 dias.

## 6. Direitos do titular (LGPD art. 18)

Qualquer titular de dado pessoal pode exercer os direitos do art. 18:
acesso, correção, anonimização, portabilidade, eliminação, informação
sobre tratamento, revogação de consentimento, oposição.

**Canal de contato:** `contato@quantopagou.org` (assunto `[lgpd] <pedido>`).

**Tipos de pedido típicos:**

| Pedido | Como tratamos |
|---|---|
| **Correção de dado errado** (CNPJ atribuído a empresa errada, modalidade incorreta) | Vai para `/correcoes`. SLA 48h. Se confirmado, corrigimos no banco e registramos a entrada com delta antes→depois. |
| **Anonimização ou remoção de perfil de pessoa física** com nome em fornecedor PF | Avaliamos caso a caso. Em geral: se o dado é cumprimento de obrigação legal pelo órgão, a base legal é forte e não removemos — encaminhamos para o TCE-PR (origem). Se for erro de extração nosso, removemos. |
| **Pedido de remoção total** de uma empresa | Não atendemos sem ordem judicial — dado público de gasto público é interesse social legítimo. Direito de **resposta pública** garantido na página `/correcoes`. |
| **Acesso aos dados** sobre uma entidade | Já é público — toda página `/fornecedor/`, `/municipio/`, `/contrato/` mostra tudo o que temos. |

SLA de resposta a pedidos LGPD: **15 dias** (art. 19 LGPD).

## 7. Encarregado (DPO)

Até a Fase 0.5 ir ao ar publicamente, o canal `contato@quantopagou.org`
responde por papel de DPO. Após o lançamento: nomear DPO formal e
publicar nesta página.

## 8. Compartilhamento com terceiros

Não compartilhamos dados pessoais com terceiros para fins comerciais.
**Toda a base é pública** — qualquer pessoa pode reproduzir nosso
pipeline a partir do código + snapshots versionados (AGPL-3.0).

Hosting (Vercel, Supabase, Cloudflare R2, Fly.io) processa os dados
sob seus próprios termos — todos aderentes à LGPD/GDPR.

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

- **Erro de dado** (CNPJ errado, valor errado): página
  [/correcoes](http://127.0.0.1:3001/correcoes) (formulário inline).
- **Direito LGPD** (art. 18): e-mail
  `contato@quantopagou.org` assunto `[lgpd]`.
- **Vulnerabilidade de privacidade** (vazamento): leia
  [SECURITY.md](../SECURITY.md) e use o canal de segurança.
