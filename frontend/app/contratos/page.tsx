import Link from "next/link";
import type { Metadata } from "next";
import { fmtBRL, fmtBRLCompact } from "@/lib/api";
import { Stat } from "@/lib/Stat";
import {
  contratos as contratosApi,
  type ContratoSearchFilters,
  type ContratoSearchItem,
  type ContratoSearchPage,
} from "@/lib/tcepr";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Contratos · drill-down · Quanto Pagou",
  description:
    "Lista de contratos públicos filtrada — drill-down dos agregados que aparecem nas páginas de comparação, fornecedor, município e dispensas.",
  robots: { index: false, follow: false },
};

type SearchParams = {
  cluster_id?: string;
  cd_tce?: string;
  cd_ibge?: string;
  modalidade?: string;
  fornecedor_cnpj?: string;
  orgao_codigo?: string;
  orgao_nome?: string; // só para label, não vai pro endpoint
  escola_slug?: string;
  fornecedor_nome?: string; // só para label
  municipio_nome?: string; // só para label
  cluster_nome?: string;   // só para label
  page?: string;
  order?: string;
};

const CLUSTER_LABEL: Record<string, string> = {
  merenda_escolar: "Merenda escolar",
  combustivel_servicos: "Combustíveis",
  medicamentos: "Medicamentos",
  material_medico_hospitalar: "Material médico-hospitalar",
  servicos_saude_credenciamento: "Credenciamento de saúde",
  papel_escritorio: "Papel e expediente",
  limpeza_higiene: "Limpeza e higiene",
  uniformes_epi: "Uniformes e EPI",
  materiais_construcao_eletrico: "Material elétrico",
  materiais_construcao_hidraulico: "Material hidráulico",
  materiais_construcao_geral: "Materiais de construção",
  eletrodomesticos_mobiliario: "Eletrodomésticos e mobiliário",
  materiais_escolares: "Materiais escolares",
  materiais_agricolas: "Ferramentas agrícolas",
  agricultura_familiar: "Agricultura familiar",
  incentivo_cultura: "Incentivo à cultura",
  transporte_escolar: "Transporte escolar",
  obras_pavimentacao: "Obras de pavimentação",
  obras_edificacao: "Obras de edificação",
};

export default async function ContratosPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const page = Math.max(1, parseInt(params.page || "1", 10) || 1);
  const order = params.order || "valor_desc";

  const filters: ContratoSearchFilters = {
    cluster_id: params.cluster_id,
    cd_tce: params.cd_tce,
    cd_ibge: params.cd_ibge,
    modalidade: params.modalidade,
    fornecedor_cnpj: params.fornecedor_cnpj,
    orgao_codigo: params.orgao_codigo,
    escola_slug: params.escola_slug,
    page,
    limit: 50,
    order,
  };

  let result: ContratoSearchPage | null = null;
  let err: string | null = null;
  try {
    result = await contratosApi.search(filters);
  } catch (e) {
    err = e instanceof Error ? e.message : "erro";
  }

  // Labels — pra header dinamico
  const labels: { tipo: string; valor: string; href?: string }[] = [];
  if (params.cluster_id) {
    labels.push({
      tipo: "categoria",
      valor: params.cluster_nome || CLUSTER_LABEL[params.cluster_id] || params.cluster_id,
    });
  }
  if (params.cd_tce || params.cd_ibge) {
    const cd = params.cd_tce || params.cd_ibge!;
    labels.push({
      tipo: "município",
      valor: params.municipio_nome || `cd_tce ${cd}`,
      href: `/municipio/${params.cd_tce || cd}`,
    });
  }
  if (params.modalidade) {
    labels.push({
      tipo: "modalidade",
      valor: params.modalidade.replace(/_/g, " "),
    });
  }
  if (params.fornecedor_cnpj) {
    labels.push({
      tipo: "fornecedor",
      valor: params.fornecedor_nome || params.fornecedor_cnpj,
      href: `/fornecedor/${encodeURIComponent(params.fornecedor_cnpj)}`,
    });
  }
  if (params.orgao_codigo) {
    labels.push({
      tipo: "órgão",
      valor: params.orgao_nome || params.orgao_codigo,
    });
  }
  if (params.escola_slug) {
    labels.push({
      tipo: "escola",
      valor: params.escola_slug.replace(/-/g, " "),
      href: `/escolas/${params.escola_slug}`,
    });
  }

  const totalPages = result ? Math.ceil(result.total / result.limit) : 0;

  // Helper pra preservar filtros ao trocar de página
  const buildPageHref = (newPage: number): string => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== "" && k !== "page") qs.set(k, v);
    }
    qs.set("page", String(newPage));
    return `/contratos?${qs.toString()}`;
  };

  return (
    <div className="space-y-8 max-w-3xl">
      <header className="space-y-2">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight">
          Contratos · drill-down
        </h1>
        {labels.length > 0 ? (
          <p className="text-sm text-muted">
            Filtros:
            {labels.map((l, i) => (
              <span key={i} className="ml-2 inline-flex items-baseline gap-1">
                <span className="text-xs uppercase tracking-wide">{l.tipo}:</span>
                {l.href ? (
                  <Link href={l.href} className="font-medium no-underline hover:underline">
                    {l.valor}
                  </Link>
                ) : (
                  <strong>{l.valor}</strong>
                )}
              </span>
            ))}
          </p>
        ) : (
          <p className="text-sm text-muted">
            Sem filtros — mostrando todos os contratos do banco.
          </p>
        )}
      </header>

      {result && (
        <section className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
          <Stat
            label="Contratos no filtro"
            value={result.total.toLocaleString("pt-BR")}
          />
          <Stat
            label="Volume agregado"
            value={fmtBRLCompact(result.valor_total_filtrado)}
            hint={fmtBRL(result.valor_total_filtrado)}
          />
          <Stat
            label="Página"
            value={`${result.page} / ${totalPages || 1}`}
            hint={`${result.limit} por página`}
          />
        </section>
      )}

      {err && (
        <p className="text-sm text-attention">
          Falha ao consultar: {err}
        </p>
      )}

      {result && result.contratos.length === 0 && !err && (
        <p className="text-sm text-muted py-4">
          Sem contratos que casem com esses filtros.
        </p>
      )}

      <section className="space-y-2">
        <ol className="space-y-2">
          {(result?.contratos ?? []).map((c) => (
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
                  {c.fornecedor_nome ?? "fornecedor —"}
                  {c.modalidade && (
                    <span className="ml-2">
                      · <code>{c.modalidade}</code>
                    </span>
                  )}
                  {c.cluster_id && (
                    <span className="ml-2">
                      · {CLUSTER_LABEL[c.cluster_id] ?? c.cluster_id}
                    </span>
                  )}
                  {c.em_quarentena && (
                    <span className="ml-2 text-attention">· sem cluster</span>
                  )}
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

      {result && totalPages > 1 && (
        <nav className="flex items-baseline gap-3 justify-between border-t border-line pt-4 text-sm">
          {result.page > 1 ? (
            <Link href={buildPageHref(result.page - 1)} className="no-underline">
              ← anterior
            </Link>
          ) : (
            <span className="text-muted">← anterior</span>
          )}
          <span className="text-xs text-muted">
            página {result.page} de {totalPages}
          </span>
          {result.page < totalPages ? (
            <Link href={buildPageHref(result.page + 1)} className="no-underline">
              próxima →
            </Link>
          ) : (
            <span className="text-muted">próxima →</span>
          )}
        </nav>
      )}

      <section className="text-sm text-muted border-t border-line pt-6">
        <p>
          A soma do "Volume agregado" é da query inteira (todas as páginas),
          não só da exibida. Cada linha leva ao detalhe do contrato com
          link para a fonte primária. Página excluída do indexamento de
          buscas (<code>noindex,nofollow</code>) na Fase 1.
        </p>
      </section>
    </div>
  );
}

function fmtDateBR(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}
