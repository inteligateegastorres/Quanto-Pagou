import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Página não encontrada · Quanto Pagou",
  robots: { index: false, follow: false },
};

export default function NotFound() {
  return (
    <div className="max-w-2xl mx-auto space-y-6 py-8">
      <div>
        <p className="text-xs uppercase tracking-wide text-muted font-medium">
          404
        </p>
        <h1 className="text-3xl font-semibold tracking-tight mt-1">
          Não encontramos esta página
        </h1>
      </div>

      <p className="text-muted">
        O endereço pode estar errado, o item pode ter sido removido da fonte
        primária, ou (no caso de fornecedores) pode ainda não ter o mínimo
        de 5 contratos para ter perfil público — guardrail §6.5 da{" "}
        <Link href="/metodologia">metodologia</Link>.
      </p>

      <section className="border border-line rounded-md p-5 bg-white text-sm space-y-2">
        <p className="font-medium">O que tentar agora:</p>
        <ul className="list-disc pl-5 space-y-1 text-muted">
          <li>
            Conferir se o CNPJ ou cd_tce está completo e numérico.
          </li>
          <li>
            Buscar pela <Link href="/buscar">página de busca</Link> (município
            ou fornecedor).
          </li>
          <li>
            Para fornecedores eventuais (&lt; 5 contratos), procurar via{" "}
            <Link href="/contratos">/contratos</Link> com filtro por CNPJ.
          </li>
          <li>
            Achou que era pra existir?{" "}
            <Link href="/correcoes">Reportar como erro</Link> — SLA 48h.
          </li>
        </ul>
      </section>

      <div className="pt-2">
        <Link
          href="/"
          className="border border-ink rounded-md px-4 py-2 text-sm no-underline hover:bg-ink hover:text-paper"
        >
          ← voltar à página inicial
        </Link>
      </div>
    </div>
  );
}
