import Link from "next/link";
import { notFound } from "next/navigation";
import { api, fmtBRL } from "@/lib/api";
import { ManchteContextBox } from "@/lib/ManchteContext";
import { DisclaimerOrigem } from "@/lib/DisclaimerOrigem";

export const dynamic = "force-dynamic";

export default async function ClusterPage({
  params,
}: {
  params: Promise<{ cluster_id: string }>;
}) {
  const { cluster_id } = await params;

  // Resolve cluster a partir da listagem (n_itens vem populado).
  const all = await api.clusters();
  const cluster = all.find((c) => c.cluster_id === cluster_id);
  if (!cluster) notFound();

  const [paresList, ranking] = await Promise.all([
    api.paresFor(cluster_id).catch(() => []),
    api.rankingOrgaos(cluster_id, "mediana_desc", 20).catch(() => []),
  ]);
  const pares = paresList[0] ?? null;

  return (
    <div className="space-y-10">
      <header className="space-y-2">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight">
          {cluster.descricao_canonica}
        </h1>
        <p className="text-xs text-muted">
          cluster: <code>{cluster.cluster_id}</code> ·{" "}
          versão <span className="text-ok">{cluster.cluster_version}</span> ·{" "}
          categoria {cluster.categoria} · {cluster.n_itens} itens analisados
        </p>
      </header>

      <DisclaimerOrigem fonte="mista" />

      <ManchteContextBox cluster_id={cluster_id} />

      {pares && (
        <section className="border border-line rounded-md p-6 bg-white">
          <h2 className="text-lg font-semibold mb-3">
            Distribuição entre pares ({pares.ente_nivel} · {pares.uf} ·{" "}
            {pares.porte})
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 text-sm">
            <Stat label="mínimo" value={fmtBRL(pares.minimo)} />
            <Stat label="p25" value={fmtBRL(pares.p25)} />
            <Stat label="mediana" value={fmtBRL(pares.mediana)} highlight />
            <Stat label="p75" value={fmtBRL(pares.p75)} />
            <Stat label="máximo" value={fmtBRL(pares.maximo)} />
          </div>
          <p className="text-xs text-muted mt-3">
            Intervalo p25–p75: {fmtBRL(pares.p25)} – {fmtBRL(pares.p75)} (n={pares.n}).
            IQR de {fmtBRL(pares.iqr)}.
          </p>
        </section>
      )}

      <section>
        <h2 className="text-lg font-semibold mb-3">
          Ranking de órgãos por mediana
        </h2>
        {ranking.length === 0 && (
          <p className="text-sm text-muted">Sem ranking disponível para este cluster.</p>
        )}
        <ol className="space-y-1">
          {ranking.map((r, idx) => {
            const m = Number(r.mediana_orgao);
            const med = pares ? Number(pares.mediana) : null;
            const acima = med ? (m - med) / med : 0;
            return (
              <li
                key={r.orgao_codigo}
                className="flex items-baseline gap-3 text-sm border-b border-line/60 py-2"
              >
                <span className="w-6 text-right text-muted">{idx + 1}.</span>
                <span className="flex-1">{r.orgao_nome}</span>
                <span className="text-xs text-muted w-16 text-right">
                  n={r.n_compras}
                </span>
                <span className="font-mono w-24 text-right">{fmtBRL(m)}</span>
                {med != null && acima > 0.01 && (
                  <span className="text-attention text-xs w-16 text-right">
                    +{(acima * 100).toFixed(0)}%
                  </span>
                )}
                {med != null && acima < -0.01 && (
                  <span className="text-ok text-xs w-16 text-right">
                    {(acima * 100).toFixed(0)}%
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="min-w-0 overflow-hidden">
      <div className="text-xs text-muted uppercase tracking-wide truncate">
        {label}
      </div>
      <div
        className={
          "font-mono whitespace-nowrap overflow-hidden text-ellipsis " +
          (highlight ? "text-base font-semibold" : "")
        }
        title={value}
      >
        {value}
      </div>
    </div>
  );
}
