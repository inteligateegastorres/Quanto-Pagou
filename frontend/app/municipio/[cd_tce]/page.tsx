import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import {
  tcepr,
  type ContratoMunicipio,
  type FornecedorMunicipio,
  type MunicipioInfo,
  type RankingMunicipio,
} from "@/lib/tcepr";
import { qd, fmtDate, type Gazette } from "@/lib/qd";
import { fmtBRL, fmtBRLCompact } from "@/lib/api";
import { Stat } from "@/lib/Stat";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ cd_tce: string }>;
}): Promise<Metadata> {
  const { cd_tce } = await params;
  let info: MunicipioInfo | null = null;
  try {
    info = await tcepr.resolveMunicipio(cd_tce);
  } catch {
    /* ignore */
  }
  const titulo = info ? `${info.nome} — compras públicas` : "Município";
  return {
    title: `${titulo} · Quanto Pagou`,
    description: info
      ? `Compras públicas, fornecedores e categorias monitoradas em ${info.nome}/PR. Fonte: TCE-PR (PIT).`
      : "Compras públicas municipais (TCE-PR).",
  };
}

export default async function MunicipioPage({
  params,
}: {
  params: Promise<{ cd_tce: string }>;
}) {
  const { cd_tce } = await params;

  let info: MunicipioInfo;
  try {
    info = await tcepr.resolveMunicipio(cd_tce);
  } catch {
    notFound();
  }

  // Para municipios catalogados (com cd_ibge), fazemos as queries por
  // cd_ibge (que e o que os endpoints /tce-pr/* esperam). Sem cd_ibge,
  // mostramos so info basica.
  const cdIbge = info.cd_ibge;

  // Tenta tambem buscar diarios oficiais (Querido Diario). Cobertura
  // depende do municipio: para alguns o QD nao tem dados, para outros
  // (Curitiba: 8.942 diarios desde 1993) tem volume bom.
  // Fetch best-effort — se falhar, secao some.
  const [resumoR, fornecedoresR, contratosClusterR, gazettesR] = cdIbge
    ? await Promise.allSettled([
        tcepr.resumo(cdIbge),
        tcepr.fornecedores(cdIbge, 10),
        tcepr.contratosPorCluster(cdIbge, { limit: 50 }),
        qd.gazettes(cdIbge, { size: 5 }),
      ])
    : [null, null, null, null];

  const resumo =
    resumoR && resumoR.status === "fulfilled" ? resumoR.value : null;
  const fornecedores =
    fornecedoresR && fornecedoresR.status === "fulfilled" ? fornecedoresR.value : [];
  const contratosCluster =
    contratosClusterR && contratosClusterR.status === "fulfilled"
      ? contratosClusterR.value
      : [];
  const gazettes =
    gazettesR && gazettesR.status === "fulfilled" ? gazettesR.value.gazettes : [];
  const totalGazettes =
    gazettesR && gazettesR.status === "fulfilled" ? gazettesR.value.total_gazettes : 0;

  const porCluster = new Map<string, ContratoMunicipio[]>();
  for (const row of contratosCluster) {
    const key = row.cluster_id;
    if (!porCluster.has(key)) porCluster.set(key, []);
    porCluster.get(key)!.push(row);
  }

  // Comparacao com cidades pares (so para municipios catalogados em porte)
  const topClusters = Array.from(porCluster.entries())
    .map(([id, rows]) => ({
      id,
      total: rows.reduce((s, r) => s + Number(r.valor_total_periodo), 0),
    }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 5)
    .map((c) => c.id);

  const rankingsR = await Promise.allSettled(
    topClusters.map((cid) =>
      tcepr.rankingMunicipios(cid, {
        porte: info.porte,
        order: "mediana_desc",
        limit: 30,
      }),
    ),
  );
  const comparacoes: { cluster_id: string; rows: RankingMunicipio[] }[] = [];
  topClusters.forEach((cid, i) => {
    const r = rankingsR[i];
    if (r.status === "fulfilled" && r.value.length > 1) {
      comparacoes.push({ cluster_id: cid, rows: r.value });
    }
  });

  const porteLabel = {
    municipio_pr_grande: "porte grande (acima de 250 mil hab.)",
    municipio_pr_medio: "porte médio (50-250 mil hab.)",
    municipio_pr_pequeno: "porte pequeno (até 50 mil hab.)",
  }[info.porte] ?? info.porte;

  return (
    <div className="space-y-12 max-w-3xl">
      <header className="space-y-3">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <p className="text-xs uppercase tracking-wide text-attention font-medium">
          {info.nome} · PR · cd_tce {info.cd_tce}
          {info.cd_ibge && <> · IBGE {info.cd_ibge}</>}
          {!info.catalogado && (
            <span className="text-muted"> · não catalogado em municipio_pr</span>
          )}
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          Compras públicas de {info.nome}
        </h1>
        <p className="text-muted">
          Município paranaense de {porteLabel}. Os números abaixo vêm dos
          arquivos consolidados do{" "}
          <a
            href="https://pit.tce.pr.gov.br/Dados/DadosConsulta/Consolidado"
            target="_blank"
            rel="noreferrer"
          >
            TCE-PR (PIT)
          </a>{" "}
          — atualizados semanal, sem cadastro. Granularidade <strong>por
          contrato</strong> (TCE não publica item-a-item); ver{" "}
          <Link href="/metodologia">metodologia</Link>.
        </p>
      </header>

      {!resumo && (
        <section className="border border-line rounded-md p-4 text-sm text-muted">
          Sem dados TCE-PR ingeridos para este município. Para municípios
          fora dos 35 maiores (não catalogados em <code>analytics.municipio_pr</code>),
          use a chave cd_tce na URL — os contratos aparecem mesmo sem
          cadastro completo.
        </section>
      )}

      {resumo && (
        <section className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <Stat
            label="Contratos analisados"
            value={resumo.n_contratos_total.toLocaleString("pt-BR")}
            hint="ano 2025-2026"
          />
          <Stat
            label="Volume total"
            value={fmtBRLCompact(resumo.valor_total)}
            hint={fmtBRL(resumo.valor_total)}
          />
          <Stat
            label="Cobertura por cluster"
            value={`${(resumo.cobertura_pct * 100).toFixed(0)}%`}
            hint={`${resumo.n_em_cluster} categorizados / ${resumo.n_em_quarentena} sem cluster`}
          />
          <Stat
            label="Fornecedores top"
            value={fornecedores.length >= 10 ? "10+" : String(fornecedores.length)}
          />
        </section>
      )}

      {fornecedores.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-baseline justify-between flex-wrap gap-2">
            <h2 className="text-xl font-semibold">
              Top fornecedores por volume
            </h2>
            <Link
              href={`/buscar?f=&m=${encodeURIComponent(info.nome)}`}
              className="text-xs text-muted no-underline"
            >
              ver todos →
            </Link>
          </div>
          <ol className="space-y-2">
            {fornecedores.map((f, i) => (
              <FornecedorRow key={`${f.fornecedor_cnpj}-${f.fornecedor_nome}`} pos={i + 1} f={f} />
            ))}
          </ol>

          <div className="border border-line rounded-md p-4 mt-4 bg-paper space-y-2">
            <p className="text-sm font-medium">Quem fornece o quê em {info.nome}?</p>
            <p className="text-xs text-muted">
              Atalhos de busca por categoria — abrem a página de comparação
              filtrada pelo cluster selecionado, com {info.nome} pré-selecionada
              e cidades-pares paranaenses do mesmo porte.
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              {[
                { id: "merenda_escolar", nome: "Merenda escolar" },
                { id: "transporte_escolar", nome: "Transporte escolar" },
                { id: "medicamentos", nome: "Medicamentos" },
                { id: "combustivel_servicos", nome: "Combustíveis" },
                { id: "limpeza_higiene", nome: "Limpeza e higiene" },
                { id: "obras_pavimentacao", nome: "Obras de pavimentação" },
              ].map((c) => (
                <Link
                  key={c.id}
                  href={`/comparar?cluster=${c.id}&municipios=${info.cd_tce}`}
                  className="border border-line rounded-md px-3 py-1.5 text-xs no-underline hover:border-ink"
                >
                  {c.nome}
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {porCluster.size > 0 && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Contratos por categoria-piloto</h2>
          {Array.from(porCluster.entries()).map(([clusterId, rows]) => (
            <ClusterCard key={clusterId} clusterId={clusterId} rows={rows} />
          ))}
        </section>
      )}

      {comparacoes.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">
            Como {info.nome} se compara
          </h2>
          <p className="text-sm text-muted">
            Ranking pela mediana de valor de contrato entre cidades-pares
            paranaenses (mesmo porte). {info.nome} aparece destacada.
          </p>
          {comparacoes.map(({ cluster_id, rows }) => (
            <ComparacaoCard
              key={cluster_id}
              clusterId={cluster_id}
              rows={rows}
              cdIbgeCidade={info.cd_ibge}
            />
          ))}
        </section>
      )}

      {gazettes.length > 0 && (
        <section className="border-t border-line pt-8 space-y-4">
          <header className="space-y-1">
            <h2 className="text-xl font-semibold">Diários oficiais</h2>
            <p className="text-sm text-muted">
              Últimos atos publicados pelo município via{" "}
              <a
                href="https://queridodiario.ok.org.br/"
                target="_blank"
                rel="noreferrer"
              >
                Querido Diário
              </a>{" "}
              (OKBR). Cobertura total: {totalGazettes.toLocaleString("pt-BR")}{" "}
              diários indexados.
            </p>
          </header>
          <ol className="space-y-3">
            {gazettes.map((g) => (
              <GazetteRow key={`${g.date}-${g.edition}-${g.url}`} gazette={g} />
            ))}
          </ol>
        </section>
      )}

      <section className="text-sm text-muted border-t border-line pt-6">
        Fonte: TCE-PR PIT (ZIP semanal com 399 municípios). Imprecisões em{" "}
        <Link href="/correcoes">/correcoes</Link>.
      </section>
    </div>
  );
}

function FornecedorRow({ pos, f }: { pos: number; f: FornecedorMunicipio }) {
  const podeLinkar = f.n_contratos >= 5;
  const cnpjEnc = encodeURIComponent(f.fornecedor_cnpj);
  return (
    <li className="flex items-baseline gap-3 border-b border-line/60 py-2 text-sm">
      <span className="w-6 text-right text-muted">{pos}.</span>
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">
          {podeLinkar ? (
            <Link href={`/fornecedor/${cnpjEnc}`} className="no-underline hover:underline">
              {f.fornecedor_nome ?? "—"}
            </Link>
          ) : (
            f.fornecedor_nome ?? "—"
          )}
        </div>
        <div className="text-xs text-muted">
          CNPJ {f.fornecedor_cnpj} · {f.n_contratos} contrato{f.n_contratos === 1 ? "" : "s"}
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
  const sorted = [...rows].sort(
    (a, b) => Number(b.valor_total_periodo) - Number(a.valor_total_periodo),
  );
  const totalContratos = sorted.reduce((s, r) => s + r.n_contratos, 0);
  const totalValor = sorted.reduce((s, r) => s + Number(r.valor_total_periodo), 0);
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

function ComparacaoCard({
  clusterId,
  rows,
  cdIbgeCidade,
}: {
  clusterId: string;
  rows: RankingMunicipio[];
  cdIbgeCidade: string | null;
}) {
  const sorted = [...rows].sort(
    (a, b) => Number(b.mediana_valor_contrato) - Number(a.mediana_valor_contrato),
  );
  const medianas = sorted.map((r) => Number(r.mediana_valor_contrato));
  const medianaGlobal =
    medianas.length === 0 ? 0 : medianas[Math.floor(medianas.length / 2)];

  return (
    <article className="border border-line rounded-md p-4 bg-white">
      <header className="flex items-baseline justify-between mb-3 flex-wrap gap-2">
        <h3 className="text-base font-semibold">{prettyCluster(clusterId)}</h3>
        <span className="text-xs text-muted">
          {sorted.length} cidades · mediana entre pares: <strong>{fmtBRL(medianaGlobal)}</strong>
        </span>
      </header>
      <ol className="text-sm space-y-1">
        {sorted.map((r, idx) => {
          const isCidade = r.cd_ibge === cdIbgeCidade;
          const m = Number(r.mediana_valor_contrato);
          const acima = medianaGlobal > 0 ? (m - medianaGlobal) / medianaGlobal : 0;
          const nomeNode = isCidade ? (
            <>
              {r.municipio}
              <span className="ml-2 text-xs text-attention">← você</span>
            </>
          ) : (
            <Link
              href={`/municipio/${r.cd_tce}`}
              className="no-underline hover:underline"
            >
              {r.municipio}
            </Link>
          );
          return (
            <li
              key={r.cd_ibge}
              className={
                "flex items-baseline gap-3 border-b border-line/60 py-1 " +
                (isCidade ? "bg-attention/5 font-medium" : "")
              }
            >
              <span className="w-6 text-right text-muted">{idx + 1}.</span>
              <span className="flex-1 min-w-0 truncate">{nomeNode}</span>
              <span className="text-xs text-muted w-20 text-right">{r.n_contratos} c.</span>
              <span className="font-mono w-28 text-right">{fmtBRL(m)}</span>
              {Math.abs(acima) > 0.05 && (
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
    </article>
  );
}

function prettyCluster(clusterId: string): string {
  const map: Record<string, string> = {
    merenda_escolar: "Merenda escolar",
    combustivel_servicos: "Combustíveis",
    medicamentos: "Medicamentos",
    material_medico_hospitalar: "Material médico-hospitalar",
    servicos_saude_credenciamento: "Credenciamento de prestadores de saúde",
    papel_escritorio: "Papel e material de escritório",
    limpeza_higiene: "Limpeza e higiene",
    uniformes_epi: "Uniformes e EPI",
    materiais_construcao_eletrico: "Material elétrico",
    materiais_construcao_hidraulico: "Material hidráulico",
    materiais_construcao_geral: "Materiais de construção",
    eletrodomesticos_mobiliario: "Eletrodomésticos e mobiliário",
    materiais_escolares: "Materiais escolares",
    materiais_agricolas: "Materiais e ferramentas agrícolas",
    agricultura_familiar: "Agricultura familiar",
    incentivo_cultura: "Incentivo à cultura",
    transporte_escolar: "Transporte escolar",
    obras_pavimentacao: "Obras de pavimentação",
    obras_edificacao: "Obras de edificação",
  };
  return map[clusterId] ?? clusterId;
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
