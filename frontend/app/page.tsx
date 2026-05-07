import Link from "next/link";
import { api, fmtBRL, fmtBRLCompact } from "@/lib/api";
import { Stat } from "@/lib/Stat";
import { buscar } from "@/lib/tcepr";

export const dynamic = "force-dynamic";

// Os 5 clusters federais (golden CATMAT). O resto vem do TCE-PR
// (Tier 1.5 keyword) e linka pra /comparar em vez de /cluster
// (que filtra por confiança >= 0.75 e não casa keyword).
const CLUSTERS_FEDERAIS = new Set([
  "oleo_diesel_s10",
  "arroz_tipo_1",
  "cafe_torrado_moido",
  "caneta_esferografica_azul",
  "papel_sulfite_a4_75g",
]);

export default async function HomePage() {
  // Federal: insight + ranking de diesel mantidos.
  // Estadual: stats agregadas + top 5 municipios + top 5 fornecedores.
  const [clustersR, paresDieselR, rankingDieselR, topMunR, topFornR] =
    await Promise.allSettled([
      api.clusters(),
      api.paresFor("oleo_diesel_s10"),
      api.rankingOrgaos("oleo_diesel_s10", "mediana_desc", 50),
      buscar.municipios({ limit: 5 }),
      buscar.fornecedores({ limit: 5 }),
    ]);

  const clusters = clustersR.status === "fulfilled" ? clustersR.value : [];
  const paresDiesel = paresDieselR.status === "fulfilled" ? paresDieselR.value : [];
  const rankingDieselFull =
    rankingDieselR.status === "fulfilled" ? rankingDieselR.value : [];
  const topMun = topMunR.status === "fulfilled" ? topMunR.value : [];
  const topForn = topFornR.status === "fulfilled" ? topFornR.value : [];

  const rankingDiesel = rankingDieselFull.slice(0, 5);
  const medianaPares = paresDiesel[0]?.mediana ? Number(paresDiesel[0].mediana) : null;
  const insightSpreadPct =
    rankingDieselFull.length >= 2
      ? (Number(rankingDieselFull[0].mediana_orgao) -
          Number(rankingDieselFull[rankingDieselFull.length - 1].mediana_orgao)) /
        Number(rankingDieselFull[rankingDieselFull.length - 1].mediana_orgao)
      : null;

  // Agregados PR (vem dos top 30, soma volume e contratos)
  const totalContratosPr = topMun.reduce((s, m) => s + m.n_contratos, 0);
  const totalVolumePr = topMun.reduce((s, m) => s + Number(m.valor_total), 0);

  // Separar categorias monitoradas federal vs PR
  const clustersFed = clusters.filter((c) => CLUSTERS_FEDERAIS.has(c.cluster_id));
  const clustersPR = clusters.filter(
    (c) => !CLUSTERS_FEDERAIS.has(c.cluster_id) && c.n_itens > 0,
  );

  return (
    <div className="space-y-16">
      {/* HERO */}
      <section className="space-y-5">
        <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight leading-tight">
          Quanto o governo pagou pela mesma coisa?
        </h1>
        <p className="text-muted max-w-2xl text-lg leading-relaxed">
          Plataforma cívica que compara preços de contratos públicos
          brasileiros. Mostra os números com fonte primária — sem adjetivos.
        </p>
        <div className="flex gap-3 flex-wrap pt-2">
          <Link
            href="/buscar"
            className="border border-ink rounded-md px-4 py-2 text-sm no-underline hover:bg-ink hover:text-paper"
          >
            Buscar município ou fornecedor →
          </Link>
          <Link
            href="/comparar"
            className="border border-line rounded-md px-4 py-2 text-sm no-underline hover:border-ink"
          >
            Comparar municípios
          </Link>
          <Link
            href="/manifesto"
            className="border border-line rounded-md px-4 py-2 text-sm no-underline hover:border-ink"
          >
            Manifesto
          </Link>
        </div>
      </section>

      {/* ZONA 1: PARANÁ REAL */}
      <section className="space-y-6 border-l-4 border-ok pl-6">
        <header className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-ok font-medium">
            Paraná · dados reais · TCE-PR PIT
          </p>
          <h2 className="text-2xl font-semibold tracking-tight">
            Compras públicas do estado do Paraná
          </h2>
          <p className="text-muted text-sm max-w-2xl">
            Snapshot semanal de 397 municípios paranaenses. Granularidade por
            contrato (TCE-PR não publica item-a-item) — comparação por valor
            por contrato com objeto similar.
          </p>
        </header>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <Stat
            label="Contratos no banco"
            value={(156679).toLocaleString("pt-BR")}
            hint="ano 2025-2026"
          />
          <Stat label="Municípios cobertos" value="397 / 399" hint="2 com XML inválido" />
          <Stat label="Fornecedores únicos" value={(121526).toLocaleString("pt-BR")} />
          <Stat label="Categorias-piloto" value="19" hint="cluster por keyword" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <div className="flex items-baseline justify-between">
              <h3 className="text-base font-semibold">Maiores municípios por volume</h3>
              <Link href="/buscar" className="text-xs text-muted">
                ver todos →
              </Link>
            </div>
            <ol className="space-y-1">
              {topMun.map((m, i) => (
                <li
                  key={m.cd_tce}
                  className="flex items-baseline gap-2 border-b border-line/60 py-1.5 text-sm"
                >
                  <span className="w-5 text-right text-muted">{i + 1}.</span>
                  <Link
                    href={`/municipio/${m.cd_tce}`}
                    className="flex-1 truncate font-medium no-underline hover:underline"
                  >
                    {m.nome}
                  </Link>
                  <span className="text-xs text-muted whitespace-nowrap">
                    {m.n_contratos.toLocaleString("pt-BR")} c.
                  </span>
                  <span className="font-mono text-xs text-right whitespace-nowrap">
                    {fmtBRL(m.valor_total)}
                  </span>
                </li>
              ))}
            </ol>
          </div>

          <div className="space-y-3">
            <div className="flex items-baseline justify-between">
              <h3 className="text-base font-semibold">Top fornecedores</h3>
              <Link href="/buscar" className="text-xs text-muted">
                ver todos →
              </Link>
            </div>
            <ol className="space-y-1">
              {topForn.map((f, i) => (
                <li
                  key={f.fornecedor_cnpj}
                  className="flex items-baseline gap-2 border-b border-line/60 py-1.5 text-sm"
                >
                  <span className="w-5 text-right text-muted">{i + 1}.</span>
                  <Link
                    href={`/fornecedor/${encodeURIComponent(f.fornecedor_cnpj)}`}
                    className="flex-1 truncate font-medium no-underline hover:underline"
                  >
                    {f.fornecedor_nome ?? "—"}
                  </Link>
                  <span className="text-xs text-muted whitespace-nowrap">
                    {f.n_contratos} c.
                  </span>
                  <span className="font-mono text-xs text-right whitespace-nowrap">
                    {fmtBRL(f.valor_total)}
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 text-sm pt-2">
          <Link
            href="/comparar?cluster=merenda_escolar&municipios=410690,412770"
            className="border border-line rounded-md px-3 py-1.5 no-underline hover:border-ink"
          >
            Comparar Curitiba × Toledo em merenda escolar
          </Link>
          <Link
            href="/comparar?cluster=medicamentos&municipios=410690,411520,410940"
            className="border border-line rounded-md px-3 py-1.5 no-underline hover:border-ink"
          >
            Curitiba × Maringá × Guarapuava em medicamentos
          </Link>
        </div>
      </section>

      {/* ZONA 2: FEDERAL (FIXTURE METODOLÓGICA) */}
      <section className="space-y-5 border-l-4 border-attention/40 pl-6 opacity-95">
        <header className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-attention font-medium">
            Federal · fixture metodológica
          </p>
          <h2 className="text-2xl font-semibold tracking-tight">
            Exemplo: como funciona a comparação por item (CATMAT)
          </h2>
          <p className="text-muted text-sm max-w-2xl">
            Enquanto a API Compras.gov.br está com instabilidade crônica, esta
            zona usa uma <em>fixture sintética</em> de 90 contratos federais
            em 5 categorias-piloto para demonstrar o pipeline item-a-item
            (granularidade preço por unidade-base, não por contrato). Quando a
            API estabilizar, vira ingestão real sem mudar produto.
          </p>
        </header>

        <article className="border border-attention/30 bg-attention/5 rounded-md p-5">
          <p className="text-xs uppercase tracking-wide text-attention font-medium mb-2">
            Insight da semana · 06 de maio de 2026
          </p>
          <h3 className="text-lg font-semibold leading-snug mb-2">
            <Link href="/insight/diesel-ministerios" className="no-underline hover:underline">
              Por que ministérios pagam preços tão diferentes pelo mesmo diesel?
            </Link>
          </h3>
          <p className="text-sm text-muted">
            No mesmo período, em DF, o spread entre o ministério que pagou
            mais caro e o que pagou mais barato pelo litro de diesel S10
            chegou a{" "}
            {insightSpreadPct != null
              ? `${(insightSpreadPct * 100).toFixed(0)}%`
              : "150%"}
            . <Link href="/insight/diesel-ministerios">leia →</Link>
          </p>
        </article>

        {medianaPares != null && rankingDiesel.length > 0 && (
          <div className="border border-line rounded-md p-5 bg-white">
            <div className="flex items-baseline justify-between mb-3">
              <h3 className="text-base font-semibold">
                Órgãos federais por mediana — Óleo Diesel S10
              </h3>
              <Link href="/cluster/oleo_diesel_s10" className="text-xs text-muted">
                ver todos →
              </Link>
            </div>
            <p className="text-xs text-muted mb-3">
              Mediana entre pares federais: <strong>{fmtBRL(medianaPares)}</strong> por litro.
            </p>
            <ol className="space-y-1">
              {rankingDiesel.map((r, idx) => {
                const m = Number(r.mediana_orgao);
                const acima = (m - medianaPares) / medianaPares;
                return (
                  <li
                    key={r.orgao_codigo}
                    className="flex items-baseline gap-3 text-sm border-b border-line/60 py-1.5"
                  >
                    <span className="w-5 text-right text-muted">{idx + 1}.</span>
                    <span className="flex-1">{r.orgao_nome}</span>
                    <span className="font-mono">{fmtBRL(m)}</span>
                    {Math.abs(acima) > 0.01 && (
                      <span
                        className={
                          "text-xs w-14 text-right " +
                          (acima > 0 ? "text-attention" : "text-ok")
                        }
                      >
                        {acima > 0 ? "+" : ""}
                        {(acima * 100).toFixed(0)}%
                      </span>
                    )}
                  </li>
                );
              })}
            </ol>
          </div>
        )}
      </section>

      {/* ZONA 3: CATEGORIAS MONITORADAS — separadas */}
      <section className="space-y-6">
        <header className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight">
            Categorias monitoradas
          </h2>
          <p className="text-muted text-sm">
            Federais (CATMAT, item-a-item) e municipais PR (keyword no objeto
            do contrato). Granularidades distintas — tratamento separado.
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <h3 className="text-base font-semibold flex items-center gap-2">
              <span className="text-xs uppercase tracking-wide text-attention">
                Federal
              </span>
              <span className="text-muted text-xs">
                · {clustersFed.length} categorias
              </span>
            </h3>
            <ul className="space-y-1">
              {clustersFed.map((c) => (
                <li key={c.cluster_id}>
                  <Link
                    href={`/cluster/${c.cluster_id}`}
                    className="flex items-baseline justify-between gap-2 border border-line rounded-md px-3 py-2 text-sm no-underline hover:border-ink"
                  >
                    <span className="font-medium truncate">{c.descricao_canonica}</span>
                    <span className="text-xs text-muted whitespace-nowrap">
                      {c.n_itens} itens
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="space-y-3">
            <h3 className="text-base font-semibold flex items-center gap-2">
              <span className="text-xs uppercase tracking-wide text-ok">PR municipal</span>
              <span className="text-muted text-xs">
                · {clustersPR.length} categorias
              </span>
            </h3>
            <ul className="space-y-1">
              {clustersPR.map((c) => (
                <li key={c.cluster_id}>
                  <Link
                    href={`/comparar?cluster=${c.cluster_id}`}
                    className="flex items-baseline justify-between gap-2 border border-line rounded-md px-3 py-2 text-sm no-underline hover:border-ink"
                  >
                    <span className="font-medium truncate">{c.descricao_canonica}</span>
                    <span className="text-xs text-muted whitespace-nowrap">
                      {c.n_itens.toLocaleString("pt-BR")} contratos
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* BOLETIM */}
      <section className="border border-line rounded-md p-6 bg-white">
        <h2 className="text-xl font-semibold mb-2">Boletim semanal</h2>
        <p className="text-sm text-muted mb-4 max-w-xl">
          Toda quarta enviamos um e-mail com o ranking semanal recalculado, o
          insight editorial e o que mudou em correções públicas. Sem paywall,
          sem patrocinador, sem rastreador comercial.
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
          não está plugado. Formulário fica de verdade no lançamento da Fase 1.
        </p>
      </section>

      {/* RODAPÉ DE CONTEXTO */}
      <section className="text-sm text-muted border-t border-line pt-6 space-y-3">
        <p>
          <strong>Aberto desde o primeiro commit.</strong> Backend AGPL-3.0,
          frontend MIT, datasets sob ODbL/CC-BY 4.0. Repositório, testes,
          metodologia e CSV do golden set — tudo público. Quem discordar de
          uma escolha pode abrir uma issue. Quem encontrar erro tem o botão{" "}
          <Link href="/correcoes">reportar</Link>.
        </p>
      </section>
    </div>
  );
}

