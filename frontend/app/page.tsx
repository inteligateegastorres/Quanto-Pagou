import Link from "next/link";
import { api, fmtBRL } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const clusters = await api.clusters();

  // Gancho viral: ranking dos órgãos federais que pagam mais por diesel.
  const featured = clusters.find((c) => c.cluster_id === "oleo_diesel_s10");
  const rankingFull = featured
    ? await api.rankingOrgaos(featured.cluster_id, "mediana_desc", 50)
    : [];
  const ranking = rankingFull.slice(0, 5);
  const featuredPares = featured ? await api.paresFor(featured.cluster_id) : [];
  const medianaPares = featuredPares[0]?.mediana
    ? Number(featuredPares[0].mediana)
    : null;
  const insightSpreadPct =
    rankingFull.length >= 2
      ? (Number(rankingFull[0].mediana_orgao) -
          Number(rankingFull[rankingFull.length - 1].mediana_orgao)) /
        Number(rankingFull[rankingFull.length - 1].mediana_orgao)
      : null;

  return (
    <div className="space-y-12">
      <section className="space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight">
          Quanto o governo pagou pela mesma coisa?
        </h1>
        <p className="text-muted max-w-2xl">
          Comparamos preços que órgãos públicos pagaram pelos mesmos itens.
          Mostramos o que está acima da mediana, com fonte primária. Não
          afirmamos irregularidade — mostramos os números.
        </p>
      </section>

      <section className="border border-attention/40 bg-attention/5 rounded-md p-5">
        <p className="text-xs uppercase tracking-wide text-attention font-medium mb-2">
          Insight da semana · 06 de maio de 2026
        </p>
        <h2 className="text-lg font-semibold leading-snug mb-2">
          <Link
            href="/insight/diesel-ministerios"
            className="no-underline hover:underline"
          >
            Por que ministérios pagam preços tão diferentes pelo mesmo diesel?
          </Link>
        </h2>
        <p className="text-sm text-muted">
          Em DF, no mesmo período, o spread entre o ministério que pagou mais
          caro e o que pagou mais barato pelo litro de diesel S10 chegou a{" "}
          {insightSpreadPct != null
            ? `${(insightSpreadPct * 100).toFixed(0)}%`
            : "150%"}{" "}
          — todos comprando o mesmo combustível, na mesma esfera.{" "}
          <Link href="/insight/diesel-ministerios">leia →</Link>
        </p>
      </section>

      {featured && (
        <section className="border border-line rounded-md p-6 bg-white">
          <div className="flex items-baseline justify-between mb-2">
            <h2 className="text-xl font-semibold">
              Órgãos federais que mais pagam por {featured.descricao_canonica.toLowerCase()}
            </h2>
            <Link
              href={`/cluster/${featured.cluster_id}`}
              className="text-sm text-muted"
            >
              ver tudo →
            </Link>
          </div>
          {medianaPares != null && (
            <p className="text-sm text-muted mb-4">
              Mediana entre pares federais: <strong>{fmtBRL(medianaPares)}</strong> por{" "}
              {featuredPares[0].porte === "federal_central"
                ? "litro"
                : "unidade-base"}.
            </p>
          )}
          <ol className="space-y-2">
            {ranking.map((r, idx) => {
              const m = Number(r.mediana_orgao);
              const acima = medianaPares ? (m - medianaPares) / medianaPares : 0;
              return (
                <li
                  key={r.orgao_codigo}
                  className="flex items-baseline gap-4 text-sm border-b border-line/60 pb-2"
                >
                  <span className="w-6 text-right text-muted">{idx + 1}.</span>
                  <span className="flex-1">{r.orgao_nome}</span>
                  <span className="font-mono">{fmtBRL(m)}</span>
                  {medianaPares != null && acima > 0.01 && (
                    <span className="text-attention text-xs w-16 text-right">
                      +{(acima * 100).toFixed(0)}%
                    </span>
                  )}
                </li>
              );
            })}
          </ol>
        </section>
      )}

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Categorias monitoradas</h2>
        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {clusters.map((c) => (
            <li key={c.cluster_id}>
              <Link
                href={`/cluster/${c.cluster_id}`}
                className="block border border-line rounded-md p-4 hover:bg-white no-underline"
              >
                <div className="font-medium">{c.descricao_canonica}</div>
                <div className="text-xs text-muted mt-1">
                  {c.n_itens} itens · {c.categoria} ·{" "}
                  <span className="text-ok">cluster {c.cluster_version}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section className="text-sm text-muted border-t border-line pt-6">
        <p>
          Fase 0.5 (sprint local). Cobertura inicial: 5 categorias-piloto
          federais via fixture sintética. API real Compras.gov.br entra em
          rotação assim que o backend deles estabilizar. Veja{" "}
          <Link href="/metodologia">metodologia</Link> para detalhes.
        </p>
      </section>
    </div>
  );
}
