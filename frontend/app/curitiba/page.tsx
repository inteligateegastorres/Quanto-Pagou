import Link from "next/link";
import type { Metadata } from "next";
import { qd, fmtDate, type Gazette } from "@/lib/qd";
import { tcepr, type ContratoMunicipio, type FornecedorMunicipio } from "@/lib/tcepr";
import { fmtBRL } from "@/lib/api";

export const dynamic = "force-dynamic";

const CURITIBA_TERRITORY_ID = "4106902";
const CURITIBA_CD_IBGE = "4106902";

export const metadata: Metadata = {
  title: "Curitiba — compras públicas e diários oficiais · Quanto Pagou",
  description:
    "Quanto a Prefeitura e a Câmara de Curitiba pagaram em contratos públicos. Comparação com cidades-pares paranaenses e busca textual em diários oficiais. Fonte: TCE-PR (PIT) + Querido Diário.",
};

type SearchParams = { q?: string; since?: string; cluster?: string };

export default async function CuritibaPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const query = (params.q || "").trim();
  const sinceQd =
    params.since ||
    new Date(Date.now() - 90 * 24 * 60 * 60 * 1000)
      .toISOString()
      .slice(0, 10);

  // Disparamos tudo em paralelo (TCE-PR + QD).
  const [resumoR, fornecedoresR, contratosClusterR, gazetteR, oldestR] =
    await Promise.allSettled([
      tcepr.resumo(CURITIBA_CD_IBGE),
      tcepr.fornecedores(CURITIBA_CD_IBGE, 10),
      tcepr.contratosPorCluster(CURITIBA_CD_IBGE, { limit: 50 }),
      qd.gazettes(CURITIBA_TERRITORY_ID, {
        since: sinceQd,
        size: 10,
        ...(query ? { querystring: query } : {}),
      }),
      qd.gazettesAscending(CURITIBA_TERRITORY_ID),
    ]);

  const resumo =
    resumoR.status === "fulfilled" ? resumoR.value : null;
  const fornecedores =
    fornecedoresR.status === "fulfilled" ? fornecedoresR.value : [];
  const contratosCluster =
    contratosClusterR.status === "fulfilled" ? contratosClusterR.value : [];
  const gazettesResp =
    gazetteR.status === "fulfilled" ? gazetteR.value : null;
  const gazetteOldest =
    oldestR.status === "fulfilled" ? oldestR.value.gazettes[0] : null;

  // Agrupar contratos por cluster para vista de "categorias monitoradas"
  const porCluster = new Map<string, ContratoMunicipio[]>();
  for (const row of contratosCluster) {
    const key = row.cluster_id;
    if (!porCluster.has(key)) porCluster.set(key, []);
    porCluster.get(key)!.push(row);
  }

  return (
    <div className="space-y-12 max-w-3xl">
      <header className="space-y-3">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <p className="text-xs uppercase tracking-wide text-attention font-medium">
          Curitiba · PR · IBGE 4106902
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          Compras públicas e diários oficiais
        </h1>
        <p className="text-muted">
          Quanto a Prefeitura, a Câmara e demais órgãos do município de
          Curitiba pagaram em contratos públicos. Os números vêm direto dos
          arquivos consolidados do{" "}
          <a
            href="https://pit.tce.pr.gov.br/Dados/DadosConsulta/Consolidado"
            target="_blank"
            rel="noreferrer"
          >
            TCE-PR (PIT)
          </a>{" "}
          — atualizados semanalmente, públicos, sem cadastro.
        </p>
      </header>

      <section className="border border-attention/40 bg-attention/5 rounded-md p-4 text-sm">
        <p className="font-medium text-attention mb-1">
          Granularidade: por contrato, não por item
        </p>
        <p className="text-muted leading-relaxed">
          O TCE-PR publica valor total e descrição livre (objeto) de cada
          contrato — não a lista de itens com quantidade e preço unitário.
          Comparações aqui referem-se ao <strong>valor por contrato com
          objeto similar</strong>, agrupado por palavras-chave (ex: contratos
          cuja descrição menciona &ldquo;merenda escolar&rdquo;). Diferente da
          comparação federal de item-a-item por CATMAT que aparece no resto
          do site. Detalhes na <Link href="/metodologia">metodologia</Link>.
        </p>
      </section>

      {resumo && (
        <section className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <Stat
            label="Contratos analisados"
            value={resumo.n_contratos_total.toLocaleString("pt-BR")}
            hint="ano 2025-2026"
          />
          <Stat
            label="Volume total"
            value={fmtBRL(resumo.valor_total)}
          />
          <Stat
            label="Cobertura por cluster"
            value={`${(resumo.cobertura_pct * 100).toFixed(0)}%`}
            hint={`${resumo.n_em_cluster} categorizados / ${resumo.n_em_quarentena} sem cluster`}
          />
          <Stat
            label="Fornecedores únicos"
            value={fornecedores.length >= 10 ? "10+" : String(fornecedores.length)}
            hint="top exibidos abaixo"
          />
        </section>
      )}

      {!resumo && (
        <section className="border border-line rounded-md p-4 text-sm text-muted">
          Sem dados TCE-PR ingeridos para este município ainda. Rode{" "}
          <code>scripts/run_tce_pr.py --ano 2025 --municipios 410690</code>.
        </section>
      )}

      {fornecedores.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold mb-3">
            Top fornecedores por volume contratado
          </h2>
          <p className="text-sm text-muted mb-4">
            Fornecedores ordenados pela soma do valor de contratos firmados com
            órgãos do município de Curitiba na janela coberta. Lista alfabética
            quando empatados; presença aqui não implica irregularidade — apenas
            volume de negócios com o setor público.
          </p>
          <ol className="space-y-2">
            {fornecedores.map((f, i) => (
              <FornecedorRow key={`${f.fornecedor_cnpj}-${f.fornecedor_nome}`} pos={i + 1} f={f} />
            ))}
          </ol>
        </section>
      )}

      {porCluster.size > 0 && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">
            Contratos por categoria-piloto
          </h2>
          <p className="text-sm text-muted">
            Contratos cujo objeto bate com uma das categorias-piloto definidas
            em <code>config/cluster_keywords.yaml</code>. Mostra o ranking dos
            órgãos municipais que mais movimentaram volume em cada categoria.
            Categorias fora da lista entram em quarentena (visíveis com label,
            mas sem ranking).
          </p>
          {Array.from(porCluster.entries()).map(([clusterId, rows]) => (
            <ClusterCard
              key={clusterId}
              clusterId={clusterId}
              rows={rows}
            />
          ))}
        </section>
      )}

      <section className="border-t border-line pt-8 space-y-4">
        <header className="space-y-1">
          <h2 className="text-xl font-semibold">Diários oficiais</h2>
          <p className="text-sm text-muted">
            Atos oficiais publicados pela Prefeitura de Curitiba desde
            {gazetteOldest ? ` ${fmtDate(gazetteOldest.date)}` : " 1993"} via{" "}
            <a
              href="https://queridodiario.ok.org.br/"
              target="_blank"
              rel="noreferrer"
            >
              Querido Diário
            </a>{" "}
            (OKBR). Use a busca para localizar contratos não cobertos pelos
            clusters acima, nomes de fornecedores ou tópicos específicos.
          </p>
        </header>

        <form className="flex gap-2 flex-wrap" action="/curitiba" method="get">
          <input
            name="q"
            defaultValue={query}
            placeholder='ex: "merenda escolar", "iluminação pública", CNPJ...'
            className="flex-1 min-w-0 border border-line rounded-md px-3 py-2 text-sm bg-paper"
          />
          <input
            type="date"
            name="since"
            defaultValue={sinceQd}
            className="border border-line rounded-md px-3 py-2 text-sm bg-paper"
          />
          <button
            type="submit"
            className="border border-ink rounded-md px-4 py-2 text-sm no-underline hover:bg-ink hover:text-paper"
          >
            Buscar
          </button>
        </form>

        <div className="space-y-3">
          <div className="flex items-baseline justify-between">
            <h3 className="text-base font-semibold">
              {query ? `Resultados para "${query}"` : "Diários mais recentes"}
            </h3>
            {gazettesResp && (
              <span className="text-xs text-muted">
                {gazettesResp.total_gazettes.toLocaleString("pt-BR")} no total ·
                exibindo {gazettesResp.gazettes.length}
              </span>
            )}
          </div>

          {gazettesResp && gazettesResp.gazettes.length === 0 && (
            <p className="text-sm text-muted">
              Sem resultados nessa janela. Tente ampliar a janela ou outro termo.
            </p>
          )}

          <ol className="space-y-3">
            {(gazettesResp?.gazettes ?? []).map((g) => (
              <GazetteRow key={`${g.date}-${g.edition}-${g.url}`} gazette={g} />
            ))}
          </ol>
        </div>
      </section>

      <section className="text-sm text-muted border-t border-line pt-6 space-y-2">
        <p>
          <strong>Fontes:</strong>{" "}
          <a
            href="https://pit.tce.pr.gov.br/Dados/DadosConsulta/Consolidado"
            target="_blank"
            rel="noreferrer"
          >
            TCE-PR PIT
          </a>{" "}
          (Plataforma de Informação para Todos — ZIP semanal com 399
          municípios paranaenses) +{" "}
          <a
            href="https://queridodiario.ok.org.br/"
            target="_blank"
            rel="noreferrer"
          >
            Querido Diário
          </a>{" "}
          (OKBR, MIT, dados sob CC-BY).
        </p>
        <p>
          Imprecisões de extração devem ser reportadas em{" "}
          <Link href="/correcoes">/correcoes</Link>; o pipeline é função pura
          sobre os ZIPs do TCE — toda correção é reprocessável.
        </p>
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="border border-line rounded-md p-4">
      <div className="text-xs text-muted uppercase tracking-wide">{label}</div>
      <div className="text-xl font-mono font-semibold">{value}</div>
      {hint && <div className="text-xs text-muted mt-1">{hint}</div>}
    </div>
  );
}

function FornecedorRow({ pos, f }: { pos: number; f: FornecedorMunicipio }) {
  return (
    <li className="flex items-baseline gap-3 border-b border-line/60 py-2 text-sm">
      <span className="w-6 text-right text-muted">{pos}.</span>
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{f.fornecedor_nome ?? "—"}</div>
        <div className="text-xs text-muted">
          CNPJ {f.fornecedor_cnpj} · {f.n_contratos} contrato{f.n_contratos === 1 ? "" : "s"}
          {f.n_orgaos_distintos > 1 && ` · ${f.n_orgaos_distintos} órgãos`}
        </div>
      </div>
      <span className="font-mono text-right whitespace-nowrap">
        {fmtBRL(f.valor_total_periodo)}
      </span>
    </li>
  );
}

function ClusterCard({
  clusterId,
  rows,
}: {
  clusterId: string;
  rows: ContratoMunicipio[];
}) {
  // ordenar pela mediana decrescente — ja vem assim mas sample defensivo
  const sorted = [...rows].sort(
    (a, b) =>
      Number(b.valor_total_periodo) - Number(a.valor_total_periodo),
  );
  const totalContratos = sorted.reduce((s, r) => s + r.n_contratos, 0);
  const totalValor = sorted.reduce(
    (s, r) => s + Number(r.valor_total_periodo),
    0,
  );
  return (
    <article className="border border-line rounded-md p-4 bg-white">
      <header className="flex items-baseline justify-between mb-3 flex-wrap gap-2">
        <h3 className="text-base font-semibold">{prettyCluster(clusterId)}</h3>
        <span className="text-xs text-muted">
          {totalContratos} contratos · {fmtBRL(totalValor.toFixed(2))}
        </span>
      </header>
      <ol className="text-sm space-y-1">
        {sorted.map((r) => (
          <li
            key={r.orgao_codigo}
            className="flex items-baseline gap-3 border-b border-line/60 py-1"
          >
            <span className="flex-1 min-w-0 truncate">{r.orgao_nome}</span>
            <span className="text-xs text-muted w-20 text-right">
              {r.n_contratos} c.
            </span>
            <span className="font-mono w-28 text-right">
              {fmtBRL(r.valor_total_periodo)}
            </span>
          </li>
        ))}
      </ol>
    </article>
  );
}

function GazetteRow({ gazette }: { gazette: Gazette }) {
  return (
    <li className="border border-line rounded-md p-4 bg-white space-y-2">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div className="text-sm">
          <strong>{fmtDate(gazette.date)}</strong>
          {gazette.edition && (
            <span className="text-muted"> · edição {gazette.edition}</span>
          )}
          {gazette.is_extra_edition && (
            <span className="text-attention"> · extra</span>
          )}
        </div>
        <a href={gazette.url} target="_blank" rel="noreferrer" className="text-xs">
          PDF original →
        </a>
      </div>
      {gazette.excerpts && gazette.excerpts.length > 0 && (
        <div className="text-sm leading-relaxed text-muted space-y-1">
          {gazette.excerpts.slice(0, 2).map((excerpt, i) => (
            <p key={i} className="border-l-2 border-attention/30 pl-3">
              {excerpt.length > 320 ? excerpt.slice(0, 320) + "…" : excerpt}
            </p>
          ))}
        </div>
      )}
    </li>
  );
}

function prettyCluster(clusterId: string): string {
  const map: Record<string, string> = {
    merenda_escolar: "Merenda escolar",
    combustivel_servicos: "Combustíveis",
    medicamentos: "Medicamentos",
    papel_escritorio: "Papel e material de escritório",
    limpeza_higiene: "Limpeza e higiene",
    obras_pavimentacao: "Obras de pavimentação",
    obras_edificacao: "Obras de edificação",
    transporte_escolar: "Transporte escolar",
  };
  return map[clusterId] ?? clusterId;
}
