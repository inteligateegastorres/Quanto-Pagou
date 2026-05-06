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
    <div className="space-y-14">
      <section className="space-y-5">
        <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight leading-tight">
          Quanto o governo pagou pela mesma coisa?
        </h1>
        <p className="text-muted max-w-2xl text-lg leading-relaxed">
          O Painel de Preços oficial parou de receber atualizações em julho
          de 2025. <em>Quanto Pagou</em> é o sucessor cívico — comparamos
          preços que órgãos públicos pagaram pelos mesmos itens, com fonte
          primária. Mostramos os números, sem adjetivos.
        </p>
        <div className="flex gap-3 flex-wrap pt-2">
          <Link
            href="/manifesto"
            className="border border-ink rounded-md px-4 py-2 text-sm no-underline hover:bg-ink hover:text-paper"
          >
            Leia o manifesto →
          </Link>
          <Link
            href="/insight/diesel-ministerios"
            className="border border-line rounded-md px-4 py-2 text-sm no-underline hover:border-ink"
          >
            Insight: spread no diesel federal
          </Link>
          <Link
            href="/metodologia"
            className="border border-line rounded-md px-4 py-2 text-sm no-underline hover:border-ink"
          >
            Como calculamos
          </Link>
        </div>
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

      <section className="border border-line rounded-md p-6 bg-white">
        <h2 className="text-xl font-semibold mb-2">Boletim semanal</h2>
        <p className="text-sm text-muted mb-4 max-w-xl">
          Toda quarta enviamos um e-mail com o ranking semanal recalculado, o
          insight editorial e o que mudou em correções públicas. Sem
          paywall, sem patrocinador, sem rastreador comercial.
        </p>
        <form
          className="flex gap-2 max-w-md flex-wrap"
          action="mailto:contato@quantopagou.org?subject=Inscrever%20no%20boletim"
          method="post"
          encType="text/plain"
        >
          <input
            type="email"
            name="email"
            required
            placeholder="seu@email.com"
            className="flex-1 min-w-0 border border-line rounded-md px-3 py-2 text-sm bg-paper"
          />
          <button
            type="submit"
            className="border border-ink rounded-md px-4 py-2 text-sm no-underline hover:bg-ink hover:text-paper"
          >
            Inscrever
          </button>
        </form>
        <p className="text-xs text-muted mt-2">
          Placeholder via <code>mailto:</code> enquanto o gateway de e-mail
          não está plugado. Sua inscrição abre seu cliente de e-mail — o
          formulário fica de verdade no lançamento da Fase 1.
        </p>
      </section>

      <section className="text-sm text-muted border-t border-line pt-6 space-y-3">
        <p>
          <strong>Status:</strong> Fase 0.5 (sprint local). Cobertura
          inicial: 5 categorias-piloto federais via fixture sintética. A
          API Compras.gov.br está com instabilidade crônica de backend
          (JPA EntityManager); a ingestão real entra em rotação assim que
          estabilizar. A engenharia já está pronta — vamos publicar os
          números reais sem mudar uma linha de produto.
        </p>
        <p>
          <strong>Aberto desde o primeiro commit.</strong> Backend AGPL-3.0,
          frontend MIT, datasets sob ODbL/CC-BY 4.0. Repositório, testes,
          metodologia e CSV do golden set tudo público — quem discordar de
          uma escolha pode abrir uma issue. Quem encontrar erro tem o
          botão <Link href="/correcoes">reportar</Link>.
        </p>
      </section>
    </div>
  );
}
