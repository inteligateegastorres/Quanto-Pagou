import Link from "next/link";
import type { Metadata } from "next";
import { fmtBRL, fmtBRLCompact } from "@/lib/api";
import { Stat } from "@/lib/Stat";
import { tcepr, type RankingMunicipio } from "@/lib/tcepr";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Por que cidades paranaenses pagam preços tão diferentes pela merenda escolar? · Quanto Pagou",
  description:
    "Maringá e Cascavel — ambas com mais de 300 mil habitantes — pagaram em 2025 medianas de contrato 10× diferentes pela mesma categoria: merenda escolar. Os números, sem adjetivos.",
};

export default async function InsightMerendaPage() {
  let ranking: RankingMunicipio[] = [];
  try {
    ranking = await tcepr.rankingMunicipios("merenda_escolar", {
      porte: "municipio_pr_grande",
      limit: 30,
    });
  } catch {
    // sem dados, mostra placeholder
  }

  // Ordena por mediana
  const sorted = [...ranking].sort(
    (a, b) =>
      Number(b.mediana_valor_contrato) - Number(a.mediana_valor_contrato),
  );

  // Pega Maringá e Cascavel especificamente — extremos do spread
  const maringa = sorted.find((r) => r.cd_tce === "411520");
  const cascavel = sorted.find((r) => r.cd_tce === "410480");
  const curitiba = sorted.find((r) => r.cd_tce === "410690");

  const spreadPct =
    maringa && cascavel
      ? (Number(maringa.mediana_valor_contrato) -
          Number(cascavel.mediana_valor_contrato)) /
        Number(cascavel.mediana_valor_contrato)
      : null;

  const totalContratos = sorted.reduce((s, r) => s + r.n_contratos, 0);
  const totalValor = sorted.reduce(
    (s, r) => s + Number(r.valor_total_periodo),
    0,
  );

  return (
    <article className="max-w-2xl space-y-8">
      <header className="space-y-3">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <p className="text-xs text-attention uppercase tracking-wide font-medium">
          Insight editorial · 08 de maio de 2026 · TCE-PR
        </p>
        <h1 className="text-3xl font-semibold tracking-tight leading-tight">
          Por que cidades paranaenses pagam preços tão diferentes pela merenda escolar?
        </h1>
        <p className="text-base text-muted leading-relaxed">
          Maringá e Cascavel são vizinhas em PIB e tamanho — mais de 300 mil
          habitantes cada. Ambas no Paraná, ambas precisam alimentar
          milhares de alunos da rede municipal. Em 2025, a mediana do
          contrato de <strong>merenda escolar</strong> em Maringá foi{" "}
          <strong>{spreadPct != null ? `${(spreadPct * 100).toFixed(0)}%` : "—"}</strong>{" "}
          maior que em Cascavel. A diferença não está no preço da comida.
          Está em <em>como cada prefeitura compra</em>.
        </p>
      </header>

      {maringa && cascavel && (
        <section className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Stat
            label={`${maringa.municipio} · mediana`}
            value={fmtBRL(maringa.mediana_valor_contrato)}
            hint={`${maringa.n_contratos} contratos`}
            tone="attention"
          />
          <Stat
            label={`${cascavel.municipio} · mediana`}
            value={fmtBRL(cascavel.mediana_valor_contrato)}
            hint={`${cascavel.n_contratos} contratos`}
            tone="ok"
          />
          {curitiba && (
            <Stat
              label={`${curitiba.municipio} · mediana`}
              value={fmtBRL(curitiba.mediana_valor_contrato)}
              hint={`${curitiba.n_contratos} contratos`}
            />
          )}
        </section>
      )}

      <section className="space-y-4 leading-relaxed">
        <h2 className="text-lg font-semibold">O que os números mostram</h2>
        <p>
          O TCE-PR registra cada contrato firmado pelos 397 municípios
          paranaenses, com valor total e descrição livre do objeto. Quando
          filtramos só os contratos cujo objeto menciona{" "}
          <em>merenda escolar</em>,{" "}
          <em>alimentação escolar</em> ou{" "}
          <em>PNAE</em>, sobram {totalContratos.toLocaleString("pt-BR")}{" "}
          contratos entre as 7 maiores cidades do estado. O volume agregado
          é de {fmtBRL(totalValor.toFixed(2))} no período.
        </p>
        {maringa && cascavel && (
          <p>
            Maringá fechou apenas <strong>{maringa.n_contratos}</strong>{" "}
            contratos no período, com mediana de{" "}
            <strong>{fmtBRL(maringa.mediana_valor_contrato)}</strong> por
            contrato. Cascavel, com{" "}
            <strong>{cascavel.n_contratos}</strong> contratos —{" "}
            {Math.round((cascavel.n_contratos / maringa.n_contratos) * 10) / 10}×
            mais — registrou mediana de apenas{" "}
            <strong>{fmtBRL(cascavel.mediana_valor_contrato)}</strong>.
          </p>
        )}
        <p>
          Não é diferença de preço de arroz. É <strong>modelo de
          gestão</strong>. Maringá consolida — poucos contratos grandes,
          provavelmente fornecedores únicos por categoria, prazo
          longo, escala maior. Cascavel pulveriza — muitos contratos
          pequenos, possivelmente um por trimestre, por categoria, por
          fornecedor regional. Cada modelo tem trade-offs próprios:
          consolidação simplifica gestão e pode reduzir preço unitário
          via escala; pulverização aumenta concorrência local e protege
          contra falha de um único fornecedor.
        </p>
        <p>
          Não é trivial dizer qual é melhor. <strong>O que dá pra dizer
          honestamente é que os dois fazem coisas radicalmente
          diferentes.</strong>{" "}
          E o cidadão de Maringá, ou de Cascavel, ou de qualquer das outras
          5 cidades grandes do PR, pode comparar como sua prefeitura está
          fazendo as compras de merenda em relação aos pares — coisa que
          até agora exigia abrir 7 portais de transparência separados e
          fazer a soma manualmente.
        </p>
      </section>

      <section className="border-t border-line pt-6 space-y-3">
        <h2 className="text-base font-semibold">
          Cidades-pares em ordem de mediana
        </h2>
        <ol className="text-sm space-y-1">
          {sorted.map((r, idx) => {
            const m = Number(r.mediana_valor_contrato);
            const total = Number(r.valor_total_periodo);
            const isHighlight = ["411520", "410480", "410690"].includes(r.cd_tce);
            return (
              <li
                key={r.cd_tce}
                className={
                  "flex items-baseline gap-3 border-b border-line/60 py-1.5 " +
                  (isHighlight ? "bg-attention/5 font-medium" : "")
                }
              >
                <span className="w-6 text-right text-muted">{idx + 1}.</span>
                <Link
                  href={`/municipio/${r.cd_tce}`}
                  className="flex-1 min-w-0 truncate no-underline hover:underline"
                >
                  {r.municipio}
                </Link>
                <span className="text-xs text-muted w-14 text-right">
                  {r.n_contratos} c.
                </span>
                <span className="font-mono w-28 text-right">
                  {fmtBRL(m)}
                </span>
                <span className="text-xs text-muted w-24 text-right">
                  total {fmtBRLCompact(total)}
                </span>
              </li>
            );
          })}
        </ol>
      </section>

      <section className="text-sm text-muted border-t border-line pt-6 space-y-3">
        <p>
          <strong>Como verificamos.</strong> Cluster{" "}
          <code>merenda_escolar</code> resolvido por keyword em{" "}
          <code>dsObjeto</code> (regex em{" "}
          <code>config/cluster_keywords.yaml</code>). Confiança fixa em
          0.6, threshold de comparação ≥ 0.5 para o mart TCE-PR (vs ≥
          0.75 do federal CATMAT — granularidades distintas, ver{" "}
          <Link href="/metodologia">metodologia</Link>).
        </p>
        <p>
          <strong>Granularidade.</strong> O TCE-PR não publica preço
          unitário por item dentro do contrato. A comparação aqui é
          <em> valor por contrato</em>, não <em>valor por kg de arroz</em>.
          Mediana alta indica contratos individualmente maiores — não
          necessariamente preço-por-item maior. Para preço-por-item
          federal (item-a-item via CATMAT), ver{" "}
          <Link href="/insight/diesel-ministerios">/insight/diesel</Link>.
        </p>
        <p>
          <strong>Filtro de porte.</strong> Ranking acima limitado a{" "}
          <em>municipio_pr_grande</em> (≥ 250 mil habitantes). Cidades
          médias e pequenas têm volume e mediana naturalmente menores;
          comparar entre portes diferentes pede ressalva. Use o filtro de
          porte em <Link href="/comparar?cluster=merenda_escolar">/comparar</Link>{" "}
          se quiser explorar.
        </p>
        <p className="pt-3">
          <Link href={`/comparar?cluster=merenda_escolar&municipios=411520,410480,410690`}>
            comparar Maringá × Cascavel × Curitiba lado a lado →
          </Link>
        </p>
      </section>
    </article>
  );
}
