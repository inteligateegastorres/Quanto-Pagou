import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { api, fmtBRL } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ raw_id: string }>;
}): Promise<Metadata> {
  const { raw_id } = await params;
  return {
    title: `Item #${raw_id} · Quanto Pagou`,
    description: "Item canonicalizado com comparação contra pares e fonte primária.",
    robots: { index: false, follow: false },
  };
}

export default async function ItemPage({
  params,
}: {
  params: Promise<{ raw_id: string }>;
}) {
  const { raw_id } = await params;
  const id = Number(raw_id);
  if (!Number.isFinite(id)) notFound();

  let item;
  try {
    item = await api.item(id);
  } catch {
    notFound();
  }

  const valor = item.valor_unitario_normalizado
    ? Number(item.valor_unitario_normalizado)
    : null;
  const med = item.pares ? Number(item.pares.mediana) : null;
  const acima = valor != null && med != null && med > 0 ? (valor - med) / med : null;

  // Posição relativa para barra: clamp em [0, 2x mediana].
  const barCap = med ? med * 2 : 1;
  const fracVoce = valor != null && barCap > 0 ? Math.min(valor / barCap, 1) : 0;
  const fracMed = med != null && barCap > 0 ? Math.min(med / barCap, 1) : 0;

  const conf = item.confianca_resolucao;
  const badge =
    conf >= 0.95
      ? { label: "Dados completos", color: "text-ok" }
      : conf >= 0.75
        ? { label: "Dados parciais", color: "text-attention" }
        : { label: "Em verificação", color: "text-muted" };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Link href="/" className="text-xs text-muted no-underline">
        ← início
      </Link>

      <header className="space-y-1">
        <div className="text-xs text-muted">
          {item.orgao_nome} · {item.contract_date}
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">
          {item.descricao_original}
        </h1>
      </header>

      {item.em_quarentena ? (
        <section className="border border-attention/40 bg-attention/5 rounded-md p-4 text-sm">
          <div className="font-semibold text-attention mb-1">
            Em quarentena · não comparável ainda
          </div>
          <div className="text-muted">
            Motivo: <code>{item.motivo_quarentena ?? "-"}</code>. Os dados deste
            item ficam visíveis, mas não entram em rankings ou comparações até
            que possamos resolvê-lo.
          </div>
        </section>
      ) : (
        <section className="border border-line rounded-md p-6 bg-white space-y-4">
          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-3xl font-semibold tabular-nums">
                {fmtBRL(valor)}
              </div>
              <div className="text-xs text-muted">
                por {item.unidade_base ?? "-"} · valor unitário original{" "}
                {fmtBRL(item.valor_unitario)}
              </div>
            </div>
            <span className={`text-xs ${badge.color}`}>● {badge.label}</span>
          </div>

          {item.pares && (
            <div className="space-y-3 pt-2">
              <div className="text-sm">
                Comparando com pares: <strong>{item.pares.ente_nivel}</strong> ·{" "}
                {item.pares.uf} · {item.pares.porte} (n={item.pares.n})
              </div>

              <div className="space-y-2">
                <Bar label="você" frac={fracVoce} value={fmtBRL(valor)} />
                <Bar
                  label="mediana de pares"
                  frac={fracMed}
                  value={fmtBRL(med)}
                  muted
                />
                <div className="text-xs text-muted">
                  intervalo p25–p75: {fmtBRL(item.pares.p25)} –{" "}
                  {fmtBRL(item.pares.p75)}
                </div>
              </div>

              {acima != null && (
                <div
                  className={`text-sm ${
                    acima > 0.05 ? "text-attention" : acima < -0.05 ? "text-ok" : ""
                  }`}
                >
                  {acima > 0.01
                    ? `${(acima * 100).toFixed(0)}% acima da mediana de pares`
                    : acima < -0.01
                      ? `${Math.abs(acima * 100).toFixed(0)}% abaixo da mediana de pares`
                      : "próximo da mediana de pares"}
                </div>
              )}
            </div>
          )}
        </section>
      )}

      <section className="space-y-2 text-sm">
        <h2 className="font-semibold">Sinais de atenção</h2>
        <ul className="text-sm space-y-1">
          {acima != null && acima > 0.20 && (
            <li>• Preço acima de pares (mais de 20%)</li>
          )}
          {item.metodo_resolucao !== "tier1_catmat_golden" && (
            <li className="text-muted">
              • Resolução não-canônica ({item.metodo_resolucao})
            </li>
          )}
          {(acima == null || Math.abs(acima) <= 0.20) &&
            item.metodo_resolucao === "tier1_catmat_golden" && (
              <li className="text-muted">• Nenhum sinal crítico nesta análise.</li>
            )}
        </ul>
      </section>

      <section className="space-y-1 text-sm border-t border-line pt-4">
        <h2 className="font-semibold mb-2">Detalhes</h2>
        <Row k="Fornecedor" v={item.fornecedor_nome ?? "-"} />
        <Row k="CNPJ" v={item.fornecedor_cnpj ?? "-"} />
        <Row k="Órgão" v={item.orgao_nome ?? "-"} />
        <Row k="CATMAT" v={item.catmat_id ?? "-"} />
        <Row k="Cluster" v={`${item.cluster_id ?? "-"} (${item.cluster_version ?? "-"})`} />
        <Row k="Método de resolução" v={item.metodo_resolucao} />
        <Row k="Confiança" v={conf.toFixed(2)} />
      </section>

      <section className="text-xs text-muted">
        Linguagem factual: este item apresenta apenas dados públicos. Não afirma
        irregularidade.{" "}
        <Link href="/correcoes">Reportar erro</Link> ·{" "}
        <Link href="/metodologia">como interpretamos</Link>
      </section>
    </div>
  );
}

function Bar({
  label,
  frac,
  value,
  muted,
}: {
  label: string;
  frac: number;
  value: string;
  muted?: boolean;
}) {
  const w = `${Math.max(2, Math.min(100, frac * 100))}%`;
  return (
    <div>
      <div className="flex justify-between text-xs">
        <span className={muted ? "text-muted" : ""}>{label}</span>
        <span className="font-mono">{value}</span>
      </div>
      <div className="bar mt-1">
        <div
          className={muted ? "h-2 rounded-sm bg-muted/40" : "bar-fill"}
          style={{ width: w }}
        />
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex gap-3">
      <span className="text-muted w-44 shrink-0">{k}</span>
      <span className="break-all">{v}</span>
    </div>
  );
}
