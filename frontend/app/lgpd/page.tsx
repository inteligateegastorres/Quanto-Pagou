// LGPD L.7 — Canal LGPD + encarregado + direitos do titular (PLANO §18 L.7).
// Autodeclaracao de pequeno porte conforme Resolucao CD/ANPD n. 2/2022.

import Link from "next/link";
import type { Metadata } from "next";

export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "Canal LGPD · Quanto Pagou",
  description:
    "Direitos do titular (LGPD art. 18), canal de contato, encarregado e SLA de resposta — 15 dias (art. 19) ou 48h para correção factual.",
};

export default function LgpdPage() {
  return (
    <article className="space-y-8 max-w-3xl text-sm leading-relaxed">
      <header className="space-y-2">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <h1 className="text-3xl font-semibold tracking-tight">Canal LGPD</h1>
        <p className="text-xs uppercase tracking-wide text-muted">
          Direitos do titular · art. 18 LGPD · SLA 15 dias
        </p>
      </header>

      <section className="border border-ok/40 bg-ok/5 rounded-md p-4 space-y-2">
        <p className="font-medium">Como exercer seus direitos</p>
        <p>
          Envie e-mail para{" "}
          <a href="mailto:lgpd@quantopagou.org">
            <code>lgpd@quantopagou.org</code>
          </a>{" "}
          com assunto <code>[LGPD] &lt;tipo de pedido&gt;</code> e descreva o
          pedido. Você receberá um <strong>ticket ID</strong> em até 48h e a
          resposta substantiva em até <strong>15 dias</strong> (LGPD art.
          19).
        </p>
        <p className="text-muted">
          Para correção factual rápida (CNPJ atribuído errado, valor
          claramente equivocado): use{" "}
          <Link href="/correcoes">/correcoes</Link>{" "}
          com SLA de 48h.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">
          Direitos garantidos (LGPD art. 18)
        </h2>
        <table className="w-full text-xs border border-line rounded-md overflow-hidden">
          <thead className="bg-paper text-left">
            <tr>
              <th className="px-3 py-2 border-b border-line">Direito</th>
              <th className="px-3 py-2 border-b border-line">Como atendemos</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-line">
              <td className="px-3 py-2 align-top">
                <strong>I.</strong> Confirmação de tratamento
              </td>
              <td className="px-3 py-2 align-top">
                Respondemos por e-mail confirmando se há dado seu na base.
              </td>
            </tr>
            <tr className="border-b border-line">
              <td className="px-3 py-2 align-top">
                <strong>II.</strong> Acesso aos dados
              </td>
              <td className="px-3 py-2 align-top">
                Páginas <code>/fornecedor/&#123;cnpj&#125;</code>,{" "}
                <code>/municipio/&#123;id&#125;</code>,{" "}
                <code>/contrato/&#123;id&#125;</code> já são públicas para
                PJ confirmado. Outros casos: e-mail.
              </td>
            </tr>
            <tr className="border-b border-line">
              <td className="px-3 py-2 align-top">
                <strong>III.</strong> Correção
              </td>
              <td className="px-3 py-2 align-top">
                Via <Link href="/correcoes">/correcoes</Link> (SLA 48h) ou
                e-mail. Delta antes→depois fica documentado.
              </td>
            </tr>
            <tr className="border-b border-line">
              <td className="px-3 py-2 align-top">
                <strong>IV.</strong> Anonimização / bloqueio /
                eliminação de dado desnecessário ou tratado em
                desconformidade
              </td>
              <td className="px-3 py-2 align-top">
                Tombstone (PLANO §18 L.1) via{" "}
                <code>analytics.eliminacao</code>. Snapshot bruto é
                preservado para auditoria contra falsificação; o conteúdo
                some da vitrine. Lista pública de eliminações em{" "}
                <code>/eliminacoes/publicas</code> (raw_id + motivo + data,
                sem reproduzir o conteúdo eliminado).
              </td>
            </tr>
            <tr className="border-b border-line">
              <td className="px-3 py-2 align-top">
                <strong>V.</strong> Portabilidade
              </td>
              <td className="px-3 py-2 align-top">
                Dados são públicos e disponíveis em formato aberto (JSON
                via API, CSV via export). Atendemos por e-mail.
              </td>
            </tr>
            <tr className="border-b border-line">
              <td className="px-3 py-2 align-top">
                <strong>VI.</strong> Eliminação de dado tratado por
                consentimento
              </td>
              <td className="px-3 py-2 align-top">
                Não aplicável — não tratamos dado pessoal sob base de
                consentimento (ver Política, §3: base é interesse legítimo
                + obrigação legal).
              </td>
            </tr>
            <tr className="border-b border-line">
              <td className="px-3 py-2 align-top">
                <strong>VII.</strong> Informação sobre
                compartilhamento
              </td>
              <td className="px-3 py-2 align-top">
                Não compartilhamos dado pessoal com terceiros. Hosting
                listado em <code>docs/legal/SUBPROCESSADORES.md</code>{" "}
                (pendente — PLANO §18 L.8).
              </td>
            </tr>
            <tr className="border-b border-line">
              <td className="px-3 py-2 align-top">
                <strong>VIII.</strong> Informação sobre negativa de
                consentimento
              </td>
              <td className="px-3 py-2 align-top">Não aplicável (mesma razão de VI).</td>
            </tr>
            <tr>
              <td className="px-3 py-2 align-top">
                <strong>IX.</strong> Revogação de consentimento
              </td>
              <td className="px-3 py-2 align-top">Não aplicável (mesma razão de VI).</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">
          Direito à revisão de ranking (art. 20)
        </h2>
        <p>
          Quem aparece em manchete algorítmica (<Link href="/manchetes">/manchetes</Link>)
          tem direito à <strong>revisão humana</strong> da decisão
          automatizada que selecionou o caso. Use o canal acima ou — quando
          estiver disponível — o botão "Contestar este ranking" na própria
          página (PLANO §18 L.13, pendente).
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Encarregado (DPO)</h2>
        <p>
          O projeto adota <strong>autodeclaração de pequeno porte</strong>{" "}
          conforme Resolução CD/ANPD nº 2/2022 (art. 11, II). Não há
          obrigação de nomear DPO formal. O canal{" "}
          <a href="mailto:lgpd@quantopagou.org">lgpd@quantopagou.org</a>{" "}
          centraliza as comunicações.
        </p>
        <p className="text-muted">
          <strong>Mantenedor responsável:</strong> Egas Torres ·{" "}
          <code>lgpd@quantopagou.org</code>.
        </p>
        <p className="text-muted">
          Após instituição-âncora confirmada (PLANO §18 L.14) e/ou
          crescimento que descaracterize pequeno porte, nomearemos DPO
          formal aqui.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">
          O que NÃO atendemos sem ordem judicial
        </h2>
        <p>
          <strong>Remoção total</strong> de uma empresa pessoa jurídica
          com base apenas em "não quero aparecer". O dado de gasto público
          é de interesse social legítimo (LAI 12.527/2011 + LGPD art. 7º
          II/V/IX) e a empresa que vende ao governo aceita escrutínio. Em
          contrapartida:
        </p>
        <ul className="list-disc ml-6 space-y-1">
          <li>
            <strong>Garantimos direito de resposta pública</strong> em{" "}
            <Link href="/correcoes">/correcoes</Link>.
          </li>
          <li>
            <strong>Corrigimos qualquer erro de fato</strong> em 48h.
          </li>
          <li>
            <strong>Atendemos eliminação</strong> (tombstone) em casos com
            base legal específica (decisão judicial, erro de classificação
            grave que vincule a PF/MEI).
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">ANPD</h2>
        <p>
          Caso não esteja satisfeito com nossa resposta, você pode
          peticionar à Autoridade Nacional de Proteção de Dados (ANPD) em{" "}
          <a
            href="https://www.gov.br/anpd"
            target="_blank"
            rel="noreferrer"
          >
            gov.br/anpd
          </a>
          .
        </p>
      </section>

      <footer className="text-xs text-muted border-t border-line pt-6 space-y-2">
        <p>
          Documentos relacionados:{" "}
          <Link href="/politica-privacidade">Política de Privacidade</Link>
          {" · "}
          <Link href="/termos">Termos de Uso</Link>
          {" · "}
          <Link href="/correcoes">Correções</Link>
        </p>
      </footer>
    </article>
  );
}
