import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { fmtBRL } from "@/lib/api";
import { Stat } from "@/lib/Stat";
import { escolas as escolasApi, type EscolaContrato } from "@/lib/tcepr";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  return {
    title: `Obras na escola ${slug.replace(/-/g, " ")} · Quanto Pagou`,
    description:
      "Contratos públicos extraídos do TCE-PR vinculados a esta escola. Catálogo de transparência.",
    robots: { index: false, follow: false },
  };
}

export default async function EscolaSlugPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  let contratos: EscolaContrato[];
  try {
    contratos = await escolasApi.contratos(slug, 100);
  } catch {
    notFound();
  }

  if (!contratos || contratos.length === 0) notFound();

  // Como o slug pode aparecer com nome ligeiramente diferente em cada
  // contrato (case, sufixos), pegamos a primeira variante
  const nomeCanonical = contratos[0].escola_nome;

  // Agregados
  const totalValor = contratos.reduce((s, c) => s + Number(c.valor_total ?? 0), 0);
  const municipios = new Set(contratos.map((c) => c.municipio).filter(Boolean));
  const orgaos = new Set(contratos.map((c) => c.orgao_nome).filter(Boolean));

  // PLANO §13.8 Abordagem 1: ordenar contratos por valor desc para
  // dar visibilidade ao maior investimento. Catalogo de transparencia,
  // nao ranking de eficiencia (nao sabemos m2, n_alunos, escopo).
  const contratosOrdenados = [...contratos].sort(
    (a, b) => Number(b.valor_total ?? 0) - Number(a.valor_total ?? 0),
  );
  const maiorValor = Number(contratosOrdenados[0]?.valor_total ?? 0);

  return (
    <article className="space-y-10 max-w-3xl">
      <header className="space-y-2">
        <Link href="/escolas" className="text-xs text-muted no-underline">
          ← catálogo de escolas
        </Link>
        <p className="text-xs uppercase tracking-wide text-muted">
          slug: <code>{slug}</code>
        </p>
        <h1 className="text-3xl font-semibold tracking-tight leading-tight">
          {nomeCanonical}
        </h1>
        <p className="text-sm text-muted">
          Contratos do TCE-PR cujo objeto menciona esta escola/CMEI/colégio
          /creche. Pode incluir múltiplas escolas com nomes parecidos em
          municípios distintos — confira a coluna "Município" de cada linha.
        </p>
      </header>

      <section className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <Stat label="Contratos" value={String(contratos.length)} />
        <Stat
          label="Investimento total"
          value={fmtBRL(totalValor.toFixed(2))}
          hint={maiorValor > 0 ? `maior contrato: ${fmtBRL(maiorValor)}` : undefined}
        />
        <Stat label="Municípios" value={String(municipios.size)} />
        <Stat label="Órgãos contratantes" value={String(orgaos.size)} />
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold">
          Contratos vinculados <span className="text-xs text-muted font-normal">(maior valor primeiro)</span>
        </h2>
        <p className="text-xs text-muted">
          Cada linha leva ao detalhe completo + link para a fonte primária
          (ZIP do TCE-PR). Padrão = qual regex casou (auditoria). Volume
          total não indica eficiência — não temos m², n.º de alunos ou
          escopo de cada obra para comparar.
        </p>
        <ol className="space-y-2">
          {contratosOrdenados.map((c) => (
            <li key={c.raw_id}>
              <Link
                href={`/contrato/${c.raw_id}`}
                className="block border border-line rounded-md p-3 bg-white text-sm space-y-1 no-underline hover:border-ink"
              >
                <div className="flex items-baseline justify-between gap-2 flex-wrap">
                  <span className="font-medium">
                    {c.municipio ? `${c.municipio} · ` : ""}
                    {c.orgao_nome ?? "—"}
                  </span>
                  <span className="font-mono">{fmtBRL(c.valor_total)}</span>
                </div>
                <div className="text-xs text-muted">
                  {c.contract_date && <span>{fmtDateBR(c.contract_date)} · </span>}
                  contrato {c.contrato_id ?? c.raw_id}
                  {" · "}padrão <code>{c.padrao}</code>
                  {c.cluster_id && <span> · cluster {c.cluster_id}</span>}
                  <span className="ml-2 text-attention">→ ver detalhe</span>
                </div>
                <p className="text-muted leading-relaxed">
                  {c.descricao.length > 240
                    ? c.descricao.slice(0, 240) + "…"
                    : c.descricao}
                </p>
              </Link>
            </li>
          ))}
        </ol>
      </section>

      <section className="text-sm text-muted border-t border-line pt-6">
        <p>
          Erros de extração? Reporte em{" "}
          <Link href="/correcoes">/correcoes</Link>. O regex é
          determinístico e versionado em <code>src/analytics/escolas.py</code>.
        </p>
      </section>
    </article>
  );
}

function fmtDateBR(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}
