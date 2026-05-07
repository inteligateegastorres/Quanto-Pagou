import Link from "next/link";
import type { Metadata } from "next";
import { fmtBRL } from "@/lib/api";
import { escolas as escolasApi, type EscolaListItem } from "@/lib/tcepr";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Catálogo de obras escolares · Quanto Pagou",
  description:
    "Lista de obras públicas em escolas paranaenses extraídas dos contratos do TCE-PR. Catálogo de transparência cívica — não ranking. Cobertura ~0,17% (regex no objeto do contrato).",
};

type SearchParams = { q?: string };

export default async function EscolasPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const q = (params.q || "").trim();

  let lista: EscolaListItem[] = [];
  let error: string | null = null;
  try {
    lista = await escolasApi.lista({ search: q || undefined, limit: 100 });
  } catch (e) {
    error = e instanceof Error ? e.message : "erro";
  }

  const totalContratos = lista.reduce((s, e) => s + e.n_mencoes, 0);
  const totalValor = lista.reduce((s, e) => s + Number(e.valor_total), 0);

  return (
    <div className="space-y-10 max-w-3xl">
      <header className="space-y-2">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <p className="text-xs uppercase tracking-wide text-attention font-medium">
          Catálogo · TCE-PR · obras com escola identificável
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          Obras escolares no Paraná
        </h1>
        <p className="text-muted leading-relaxed">
          Contratos públicos cujo objeto menciona nome próprio de escola,
          CMEI, colégio ou creche. <strong>Catálogo de transparência</strong>,
          não ranking — para ~99% dos contratos relacionados a escola, o
          objeto descreve programa amplo (PNAE, "rede municipal de ensino"),
          não unidade individual. O que está aqui é o que sobrou após filtros
          por regex.
        </p>
      </header>

      <section className="border border-attention/40 bg-attention/5 rounded-md p-4 text-sm space-y-2">
        <p className="font-medium text-attention">Limites desta página</p>
        <p className="text-muted leading-relaxed">
          Extração via regex em <code>src/analytics/escolas.py</code>:
          ~270-1.000 contratos casam (de 156.769 totais). Concentrado em{" "}
          <strong>obras de edificação</strong> (reformas, construções
          pontuais). Para merenda/transporte/materiais, o contrato é por
          rede ou programa, não por escola — esses casos não aparecem aqui.
          Ruído visível é esperado: nomes truncados, palavras conjuntivas,
          escolas concatenadas.
        </p>
      </section>

      <section>
        <form action="/escolas" method="get" className="flex gap-2 flex-wrap mb-4">
          <input
            name="q"
            defaultValue={q}
            placeholder="buscar por nome de escola..."
            className="flex-1 min-w-0 border border-line rounded-md px-3 py-2 text-sm bg-paper"
          />
          <button
            type="submit"
            className="border border-ink rounded-md px-4 py-2 text-sm no-underline hover:bg-ink hover:text-paper"
          >
            Buscar
          </button>
        </form>

        <p className="text-xs text-muted mb-3">
          {q
            ? `${lista.length} escolas para "${q}"`
            : `${lista.length} escolas com mais menções`}
          {" · "}
          {totalContratos} contratos · volume {fmtBRL(totalValor.toFixed(2))}
        </p>

        {error && (
          <p className="text-sm text-attention">
            Falha ao consultar: {error}
          </p>
        )}

        {!error && lista.length === 0 && (
          <p className="text-sm text-muted">Sem resultados para esse termo.</p>
        )}

        <ol className="space-y-1">
          {lista.map((e, i) => (
            <li
              key={e.escola_slug}
              className="flex items-baseline gap-3 border-b border-line/60 py-2 text-sm"
            >
              <span className="w-6 text-right text-muted">{i + 1}.</span>
              <Link
                href={`/escolas/${encodeURIComponent(e.escola_slug)}`}
                className="flex-1 min-w-0 truncate font-medium no-underline hover:underline"
              >
                {e.escola_nome}
              </Link>
              <span className="text-xs text-muted whitespace-nowrap">
                {e.n_mencoes} obra{e.n_mencoes === 1 ? "" : "s"}
                {e.n_municipios > 1 && ` · ${e.n_municipios} mun.`}
              </span>
              <span className="font-mono text-xs text-right whitespace-nowrap">
                {fmtBRL(e.valor_total)}
              </span>
            </li>
          ))}
        </ol>
      </section>

      <section className="text-sm text-muted border-t border-line pt-6 space-y-2">
        <p>
          <strong>Como ler.</strong> Mesmo nome (slug) pode corresponder a
          escolas diferentes em municípios diferentes — "Carlos Gomes" pode
          existir em várias cidades. A coluna "mun." indica em quantos
          municípios distintos o slug aparece. Para ver os contratos
          específicos com órgão e cidade, abra a página da escola.
        </p>
        <p>
          <strong>Encontrou erro de extração?</strong> Reporte em{" "}
          <Link href="/correcoes">/correcoes</Link>. A função regex é
          determinística e fica em <code>src/analytics/escolas.py</code> —
          PRs aceitos.
        </p>
      </section>
    </div>
  );
}
