import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Correções públicas · Quanto Pagou",
  description:
    "Toda correção feita após um relato é registrada aqui — data, item, delta antes → depois. SLA: 48h.",
};

export default function CorrecoesPage() {
  return (
    <div className="max-w-2xl space-y-8">
      <Link href="/" className="text-xs text-muted no-underline">
        ← início
      </Link>
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">
          Correções públicas
        </h1>
        <p className="text-muted leading-relaxed">
          Esta página existe porque dados públicos errados são piores que
          dados ausentes. Toda vez que erramos — ou que a fonte primária
          mudou — registramos aqui, com data, item afetado e delta
          antes → depois.
        </p>
      </header>

      <section className="border border-line rounded-md p-5 bg-white space-y-3">
        <h2 className="text-base font-semibold">Como funciona</h2>
        <ol className="list-decimal pl-5 space-y-1 text-sm">
          <li>Você reporta via formulário abaixo ou e-mail.</li>
          <li>
            Investigamos — <strong>SLA 48h</strong> para a primeira resposta.
          </li>
          <li>
            Se confirmado, corrigimos no banco e registramos aqui com link
            para o commit + nova <code>cluster_version</code> (quando aplicável).
          </li>
          <li>
            Páginas afetadas mostram badge &quot;corrigido em X&quot; (a
            implementar quando houver primeira correção).
          </li>
        </ol>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold">Histórico</h2>
        <div className="border border-dashed border-line rounded-md p-5 text-sm text-muted space-y-2">
          <p>
            <strong className="text-ink">Sem correções confirmadas até agora.</strong>
          </p>
          <p>
            Não conte isso como &quot;nada acontece&quot; — conte como{" "}
            &quot;ninguém pegou erro grande ainda&quot;. Quando pegar, você
            vai ver aqui antes de ver no PR. A primeira correção também vai
            disparar a implementação do badge &quot;corrigido em X&quot;
            nas páginas afetadas e do schema{" "}
            <code>analytics.correcoes</code> (hoje a página é estática
            propositalmente).
          </p>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold">Reportar erro</h2>
        <p className="text-sm text-muted">
          Encontrou um número que parece errado, um cluster mal-classificado,
          uma escola atribuída ao município errado, ou qualquer outra coisa?
          Conte. Quanto mais específico, mais rápido a gente confirma.
        </p>
        <form
          action="mailto:contato@quantopagou.org"
          method="post"
          encType="text/plain"
          className="border border-line rounded-md p-4 bg-white space-y-3 text-sm"
        >
          <div className="space-y-1">
            <label htmlFor="url" className="text-xs uppercase tracking-wide text-muted block">
              URL afetada
            </label>
            <input
              id="url"
              name="url"
              required
              placeholder="ex: https://quantopagou.org/contrato/279460"
              className="w-full border border-line rounded-md px-3 py-2 bg-paper"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="problema" className="text-xs uppercase tracking-wide text-muted block">
              O que está errado
            </label>
            <textarea
              id="problema"
              name="problema"
              required
              rows={4}
              placeholder="ex: cluster diz 'medicamentos' mas é claramente material hospitalar"
              className="w-full border border-line rounded-md px-3 py-2 bg-paper"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="fonte" className="text-xs uppercase tracking-wide text-muted block">
              Fonte primária correta (se souber)
            </label>
            <input
              id="fonte"
              name="fonte"
              placeholder="ex: link pro XML do TCE-PR ou nota fiscal"
              className="w-full border border-line rounded-md px-3 py-2 bg-paper"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="email" className="text-xs uppercase tracking-wide text-muted block">
              Seu e-mail (opcional, se quiser receber a resposta)
            </label>
            <input
              id="email"
              name="email"
              type="email"
              placeholder="seu@email.com"
              className="w-full border border-line rounded-md px-3 py-2 bg-paper"
            />
          </div>
          <button
            type="submit"
            className="border border-ink rounded-md px-4 py-2 no-underline hover:bg-ink hover:text-paper"
          >
            Enviar relato
          </button>
          <p className="text-xs text-muted">
            Placeholder via <code>mailto:</code> enquanto o gateway de e-mail
            não está plugado. Formulário fica de verdade no lançamento da
            Fase 1.
          </p>
        </form>
      </section>

      <section className="text-xs text-muted border-t border-line pt-4">
        Prefere abrir issue pública? Use{" "}
        <a
          href="https://github.com/quanto-pagou"
          target="_blank"
          rel="noreferrer"
        >
          GitHub
        </a>{" "}
        (organização criada na Fase 0.5; até lá, e-mail vale).
      </section>
    </div>
  );
}
