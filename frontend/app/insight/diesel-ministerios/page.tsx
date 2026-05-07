import Link from "next/link";
import type { Metadata } from "next";
import { api, fmtBRL } from "@/lib/api";

export const dynamic = "force-dynamic";

const CLUSTER_ID = "oleo_diesel_s10";

export const metadata: Metadata = {
  title:
    "Por que ministérios pagam preços tão diferentes pelo mesmo diesel? · Quanto Pagou",
  description:
    "No mesmo período, em DF, o Ministério da Fazenda pagou mais de duas vezes o que a Educação pagou pelo litro de diesel S10. Os números — sem adjetivos.",
};

export default async function InsightDieselPage() {
  const [paresList, ranking, clusters] = await Promise.all([
    api.paresFor(CLUSTER_ID),
    api.rankingOrgaos(CLUSTER_ID, "mediana_desc", 50),
    api.clusters(),
  ]);
  const cluster = clusters.find((c) => c.cluster_id === CLUSTER_ID);
  const pares = paresList[0] ?? null;

  if (!pares || ranking.length === 0 || !cluster) {
    return (
      <article className="max-w-2xl space-y-4">
        <h1 className="text-2xl font-semibold">Insight indisponível</h1>
        <p className="text-sm text-muted">
          O cluster <code>{CLUSTER_ID}</code> não tem dados suficientes para
          este insight no momento. Volte quando houver mais ingestões.
        </p>
      </article>
    );
  }

  const mediana = Number(pares.mediana);
  const top = ranking[0];
  const bottom = ranking[ranking.length - 1];
  const topPct = (Number(top.mediana_orgao) - mediana) / mediana;
  const bottomPct = (Number(bottom.mediana_orgao) - mediana) / mediana;
  const spreadPct =
    (Number(top.mediana_orgao) - Number(bottom.mediana_orgao)) /
    Number(bottom.mediana_orgao);

  return (
    <article className="max-w-2xl space-y-8">
      <header className="space-y-3">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <p className="text-xs text-attention uppercase tracking-wide font-medium">
          Insight editorial · 06 de maio de 2026
        </p>
        <h1 className="text-3xl font-semibold tracking-tight leading-tight">
          Por que ministérios pagam preços tão diferentes pelo mesmo diesel?
        </h1>
        <p className="text-base text-muted leading-relaxed">
          Entre os contratos federais analisados, o ministério que pagou{" "}
          <strong>mais caro</strong> por litro de diesel S10 desembolsou{" "}
          <strong>{spreadPct >= 0 ? `${(spreadPct * 100).toFixed(0)}%` : "-"}</strong>{" "}
          a mais que o ministério que pagou mais barato — todos comprando o
          mesmo combustível, na mesma esfera, no mesmo período.
        </p>
      </header>

      <section className="grid grid-cols-3 gap-4 border border-line rounded-md p-6 bg-white">
        <Stat
          label="Mediana federal"
          value={fmtBRL(mediana)}
          hint={`pares: n=${pares.n} · IQR ${fmtBRL(pares.iqr)}`}
        />
        <Stat
          label={`Mais caro · ${shortName(top.orgao_nome)}`}
          value={fmtBRL(top.mediana_orgao)}
          hint={
            topPct > 0
              ? `+${(topPct * 100).toFixed(0)}% acima da mediana`
              : "abaixo da mediana"
          }
          flavor="attention"
        />
        <Stat
          label={`Mais barato · ${shortName(bottom.orgao_nome)}`}
          value={fmtBRL(bottom.mediana_orgao)}
          hint={
            bottomPct < 0
              ? `${(bottomPct * 100).toFixed(0)}% da mediana`
              : "acima da mediana"
          }
          flavor="ok"
        />
      </section>

      <section className="space-y-4 leading-relaxed">
        <h2 className="text-lg font-semibold">O que os números mostram</h2>
        <p>
          O diesel S10 é um produto regulado, com especificação técnica fixa
          definida pela ANP. Para o Estado, é praticamente uma{" "}
          <em>commodity</em>: o que muda de contrato para contrato é volume,
          local de entrega e fornecedor — não o produto. Por isso, é uma das
          poucas categorias onde comparar preço entre órgãos faz sentido sem
          ressalvas longas.
        </p>
        <p>
          Na nossa amostra de {pares.n} contratos federais, a{" "}
          <strong>mediana</strong> ficou em{" "}
          <strong>{fmtBRL(mediana)}</strong> por litro, com a metade central
          (p25–p75) entre {fmtBRL(pares.p25)} e {fmtBRL(pares.p75)}. Esse
          intervalo é estreito — IQR de {fmtBRL(pares.iqr)} — porque diesel é
          um produto homogêneo. Quando um órgão se afasta dessa faixa, o
          desvio merece atenção.
        </p>
        <p>
          O <strong>{top.orgao_nome}</strong> aparece no topo do ranking com
          mediana de <strong>{fmtBRL(top.mediana_orgao)}</strong> por litro
          {topPct > 0
            ? ` — ${(topPct * 100).toFixed(0)}% acima da mediana de pares federais`
            : ""}
          . O <strong>{bottom.orgao_nome}</strong>, na ponta oposta, registra{" "}
          <strong>{fmtBRL(bottom.mediana_orgao)}</strong>. Em volume, a
          situação se inverte: a Educação compra volumes maiores (
          <code>{fmtBRL(bottom.valor_total_periodo)}</code> no período), o que
          pode explicar parte do desconto, mas não o tamanho do{" "}
          <em>spread</em>.
        </p>
        <p>
          Essas diferenças não implicam irregularidade. Diferenças legítimas
          entre contratos podem decorrer de modalidade (pregão vs. dispensa),
          logística (entrega na ponta vs. centralizada), prazo, ou simples
          janela de mercado. O que a comparação faz é levantar a pergunta — e
          devolver os números com link para a fonte primária. Quem precisa
          interpretar o desvio é o órgão de controle ou o jornalista que
          investiga o caso.
        </p>
        <p>
          O que fazemos aqui é simples e auditável: pegamos cada contrato com
          CATMAT correspondente a diesel S10, normalizamos a unidade para
          litro (o YAML versionado fica em{" "}
          <Link href="/metodologia">metodologia</Link>) e comparamos órgãos
          dentro do mesmo recorte (esfera × UF × porte). Mediana e IQR — não
          média e desvio padrão — porque um único contrato atípico não pode
          mover a referência. Se você acha que um número aqui está errado,
          existe um botão de reportar em cada item, e a página de{" "}
          <Link href="/correcoes">correções</Link> torna público o histórico
          de quem nos avisou e o que mudamos.
        </p>
      </section>

      <section className="border-t border-line pt-6 space-y-3">
        <h2 className="text-base font-semibold">Ranking completo</h2>
        <ol className="text-sm space-y-1">
          {ranking.map((r, idx) => {
            const m = Number(r.mediana_orgao);
            const acima = (m - mediana) / mediana;
            return (
              <li
                key={r.orgao_codigo}
                className="flex items-baseline gap-3 border-b border-line/60 py-1.5"
              >
                <span className="w-6 text-right text-muted">{idx + 1}.</span>
                <span className="flex-1">{r.orgao_nome}</span>
                <span className="text-xs text-muted w-14 text-right">
                  n={r.n_compras}
                </span>
                <span className="font-mono w-24 text-right">{fmtBRL(m)}</span>
                {acima > 0.01 && (
                  <span className="text-attention text-xs w-16 text-right">
                    +{(acima * 100).toFixed(0)}%
                  </span>
                )}
                {acima < -0.01 && (
                  <span className="text-ok text-xs w-16 text-right">
                    {(acima * 100).toFixed(0)}%
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      </section>

      <section className="text-sm text-muted border-t border-line pt-6 space-y-2">
        <p>
          <strong>Como verificamos.</strong> Cluster{" "}
          <code>
            {CLUSTER_ID} · {cluster.cluster_version}
          </code>{" "}
          (CATMAT direto, confiança 1.0). Janela do snapshot fixada em
          metodologia. Itens em quarentena (sem CATMAT, unidade ambígua) não
          entram nesta análise — eles permanecem visíveis no site sob{" "}
          <Link href="/metodologia">metodologia</Link>.
        </p>
        <p>
          <strong>Lembrete:</strong> esta plataforma está em modo
          demonstração. A história acima vale como exercício metodológico
          sobre dados sintéticos enquanto a API Compras.gov.br não estabilizar.
          A engenharia, a normalização de unidade e o pipeline são os mesmos
          que usaremos com dados reais — só os números mudam.
        </p>
        <p className="pt-3">
          <Link href={`/cluster/${CLUSTER_ID}`}>
            ver distribuição completa do cluster →
          </Link>
        </p>
      </section>
    </article>
  );
}

function Stat({
  label,
  value,
  hint,
  flavor,
}: {
  label: string;
  value: string;
  hint?: string;
  flavor?: "attention" | "ok";
}) {
  const tone =
    flavor === "attention"
      ? "text-attention"
      : flavor === "ok"
        ? "text-ok"
        : "text-ink";
  return (
    <div className="space-y-1 min-w-0 overflow-hidden">
      <div className="text-xs text-muted uppercase tracking-wide truncate">{label}</div>
      <div
        className={`text-xl font-mono font-semibold whitespace-nowrap overflow-hidden text-ellipsis ${tone}`}
        title={value}
      >
        {value}
      </div>
      {hint && <div className="text-xs text-muted truncate" title={hint}>{hint}</div>}
    </div>
  );
}

function shortName(full: string): string {
  return full
    .replace(/^MINISTERIO DA /i, "Min. ")
    .replace(/^MINISTERIO DO /i, "Min. ");
}
