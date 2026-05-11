// LGPD L.5 — Política de Privacidade pública (PLANO §18 L.5).
// Espelha data/PRIVACY.md v1 (2026-05-09). Atualizações: editar
// data/PRIVACY.md e refletir aqui no mesmo PR.

import Link from "next/link";
import type { Metadata } from "next";

export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "Política de Privacidade · Quanto Pagou",
  description:
    "Como o Quanto Pagou trata dados públicos sob a LGPD (Lei 13.709/2018) — finalidade, base legal, salvaguardas, direitos do titular.",
};

export default function PoliticaPrivacidadePage() {
  return (
    <article className="prose-like space-y-8 max-w-3xl text-sm leading-relaxed">
      <header className="space-y-2">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <h1 className="text-3xl font-semibold tracking-tight">
          Política de Privacidade
        </h1>
        <p className="text-xs uppercase tracking-wide text-muted">
          Versão v1 · 2026-05-11 · pendente revisão jurídica antes do go-live
        </p>
      </header>

      <section className="border border-attention/40 bg-attention/5 rounded-md p-4 space-y-2 text-xs">
        <p className="font-medium text-attention">Status atual</p>
        <p>
          Este documento descreve a postura do projeto sob a{" "}
          <strong>LGPD (Lei 13.709/2018)</strong>. Será revisado por
          advogado especializado (PLANO §18 L.15) antes do lançamento em
          domínio público.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">1. O que tratamos</h2>
        <p>
          Apenas <strong>dados públicos</strong> publicados pelos próprios
          órgãos de controle:
        </p>
        <ul className="list-disc ml-6 space-y-1">
          <li>
            <strong>TCE-PR (PIT)</strong> — ZIPs anuais em
            pit.tce.pr.gov.br/Arquivos/&#123;ano&#125;_PIT_TodosArquivos.zip
            (sem cadastro): contratos, fornecedores e órgãos.
          </li>
          <li>
            <strong>Compras.gov.br</strong> — API pública
            dadosabertos.compras.gov.br (sem cadastro). Hoje em fixture
            sintética; ingestão real quando o backend deles estabilizar.
          </li>
          <li>
            <strong>IBGE Censo 2022</strong> — população por município.
          </li>
        </ul>
        <p>
          <strong>Não coletamos:</strong> cookies de rastreamento, dados
          pessoais de visitantes, formulários de cadastro, ou IPs além do
          log padrão do hosting.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">
          2. Categorias de dado envolvidas
        </h2>
        <ul className="list-disc ml-6 space-y-1">
          <li>
            <strong>CNPJ de pessoa jurídica</strong> — publicado
            integralmente; dado público de empresa, não pessoal LGPD.
          </li>
          <li>
            <strong>CNPJ de MEI / EI / pessoa física</strong> —{" "}
            <strong>mascarado por padrão</strong> (PLANO §18 L.2). Perfil
            público só é gerado quando o tipo jurídico é confirmado como
            PJ. Fonte da classificação: heurística por sufixo do nome
            (v1) ou dump RFB CNPJ aberto (v2 futura).
          </li>
          <li>
            <strong>CPF mascarado pelo TCE-PR</strong> — publicado como
            veio (***.017.***-**). Não desmascaramos.
          </li>
          <li>
            <strong>Endereço, telefone, e-mail pessoal</strong> —{" "}
            <strong>não coletamos</strong>. Se aparecer no XML do TCE,
            descartamos no parser.
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">3. Base legal (LGPD art. 7º)</h2>
        <ul className="list-disc ml-6 space-y-2">
          <li>
            <strong>Inciso II — cumprimento de obrigação legal:</strong> a
            Lei de Acesso à Informação (12.527/2011) e a Lei de
            Transparência (LC 131/2009) obrigam órgãos públicos a publicar
            esses dados. Nosso tratamento dá efetividade ao direito do
            cidadão à informação.
          </li>
          <li>
            <strong>Inciso V — políticas públicas:</strong> facilitar
            controle social sobre gasto público é exercício do direito
            constitucional do cidadão (CF art. 5º XXXIII e art. 37).
          </li>
          <li>
            <strong>Inciso IX — interesse legítimo</strong> (Guia ANPD).
            Ponderado contra impacto sobre o titular, que é mínimo dado
            que o dado já é público. LIA estruturada será publicada em{" "}
            <code>docs/legal/LIA.md</code> (PLANO §18 L.3).
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">4. Salvaguardas em camadas</h2>
        <ol className="list-decimal ml-6 space-y-2">
          <li>
            <strong>Threshold mínimo:</strong> perfil só é gerado para
            fornecedor com ≥ 5 contratos públicos registrados.
          </li>
          <li>
            <strong>Distinção PJ vs MEI/EI/PF (LGPD L.2):</strong>{" "}
            tabela <code>analytics.fornecedor</code> classifica por tipo
            jurídico; endpoints retornam 404 para tudo que não é PJ
            confirmado.
          </li>
          <li>
            <strong>Tombstones (LGPD L.1):</strong> registros eliminados
            por solicitação do titular (art. 18 IV) somem da vitrine via{" "}
            <code>analytics.eliminacao</code>; snapshot bruto preservado
            para auditoria contra falsificação.
          </li>
          <li>
            <strong>noindex/nofollow</strong> nos perfis sensíveis — não
            aparecem em busca do Google.
          </li>
          <li>
            <strong>Linguagem factual estrita</strong> — não usamos
            "suspeito", "irregular" ou "desviado" em UI.
          </li>
          <li>
            <strong>Audit log (LGPD L.10):</strong>{" "}
            <code>analytics.audit_log</code> registra operações em
            tabelas com dado pessoal ou regulado (art. 37 LGPD).
          </li>
          <li>
            <strong>Manchetes algorítmicas</strong> não publicam sobre
            fornecedor no v1 — sempre sobre (cluster × município).
          </li>
        </ol>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">5. Retenção</h2>
        <p>
          Política de retenção completa em{" "}
          <a
            href="https://github.com/anthropics/quantopagou/blob/main/docs/legal/RETENCAO.md"
            target="_blank"
            rel="noreferrer"
          >
            docs/legal/RETENCAO.md
          </a>
          {" "}(LGPD L.9). Resumo:
        </p>
        <ul className="list-disc ml-6 space-y-1">
          <li>
            Snapshots brutos: <strong>retenção indefinida</strong>{" "}
            (imutáveis, auditoria contra falsificação).
          </li>
          <li>
            <code>raw_payload</code> redundante: <strong>90 dias</strong>{" "}
            após canonicalização validada.
          </li>
          <li>
            Audit log: <strong>5 anos</strong> (prescrição LGPD art. 52
            §1º + tolerância).
          </li>
          <li>
            Manchetes: <strong>2 anos</strong>.
          </li>
          <li>
            Logs do hosting: 30 dias (Vercel/Fly.io padrão).
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">
          6. Direitos do titular (LGPD art. 18)
        </h2>
        <p>
          Qualquer titular pode exercer os direitos do art. 18: acesso,
          correção, anonimização, portabilidade, eliminação, informação
          sobre tratamento, revogação, oposição. Detalhes em{" "}
          <Link href="/lgpd">/lgpd</Link>.
        </p>
        <p>
          <strong>SLA de resposta:</strong> 15 dias (LGPD art. 19) ou 48h
          para correção factual via <Link href="/correcoes">/correcoes</Link>.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">7. Encarregado (DPO)</h2>
        <p>
          O projeto adota autodeclaração de pequeno porte (Resolução
          CD/ANPD nº 2/2022) por hora. Canal de contato:{" "}
          <code>lgpd@quantopagou.org</code>. Detalhes em{" "}
          <Link href="/lgpd">/lgpd</Link>.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">
          8. Compartilhamento e licença
        </h2>
        <p>
          <strong>Não compartilhamos</strong> dados pessoais com terceiros
          para fins comerciais. Os dados derivados (agregações,
          manchetes, perfis PJ) são publicados sob{" "}
          <a
            href="https://creativecommons.org/licenses/by/4.0/legalcode.pt"
            target="_blank"
            rel="noreferrer"
          >
            CC-BY 4.0
          </a>
          {" "}— ver <Link href="/termos">Termos de Uso</Link>.
        </p>
        <p>
          Hosting (Vercel, Supabase, Cloudflare R2, Fly.io) processa os
          dados sob seus próprios termos. Catálogo completo em{" "}
          <code>docs/legal/SUBPROCESSADORES.md</code> (pendente — PLANO
          §18 L.8).
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">9. Cookies</h2>
        <p>
          Não usamos cookies de rastreamento, pixels de Facebook/Google,
          ou analytics que identifique visitante individualmente.
          Plausible (analytics agregado, sem cookie, GDPR-compliant) será
          documentado aqui antes de ativar.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">10. Mudanças nesta política</h2>
        <p>
          Mudanças relevantes geram entrada no{" "}
          <a
            href="https://github.com/anthropics/quantopagou/blob/main/PLANO.md"
            target="_blank"
            rel="noreferrer"
          >
            PLANO.md §14 (changelog)
          </a>
          {" "}e ficam registradas no <code>git log</code>. Última
          atualização: 2026-05-11.
        </p>
      </section>

      <footer className="text-xs text-muted border-t border-line pt-6 space-y-2">
        <p>
          Documento canônico: <code>data/PRIVACY.md</code> + esta página.
          Em caso de divergência, prevalece <code>data/PRIVACY.md</code>{" "}
          com timestamp mais recente.
        </p>
        <p>
          Links relacionados: <Link href="/termos">Termos de Uso</Link>
          {" · "}
          <Link href="/lgpd">Canal LGPD</Link>
          {" · "}
          <Link href="/correcoes">Reportar erro</Link>
          {" · "}
          <Link href="/metodologia">Metodologia</Link>
        </p>
      </footer>
    </article>
  );
}
