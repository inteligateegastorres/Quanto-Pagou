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
  since?: string;
  until?: string;
  em_quarentena?: string;
  q?: string;
  page?: string;
  order?: string;
};

const ORDER_LABEL: Record<string, string> = {
  valor_desc: "maior valor primeiro",
  valor_asc: "menor valor primeiro",
  data_desc: "mais recente primeiro",
  data_asc: "mais antigo primeiro",
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

  // Validacao de data: catch antes de chamar a API. since/until precisam
  // ser AAAA-MM-DD validos (mes 1-12, dia consistente). Se invalido,
  // mostramos mensagem amigavel e nao chamamos o backend (que hoje 500).
  const dateErrors: { campo: string; valor: string }[] = [];
  for (const campo of ["since", "until"] as const) {
    const v = params[campo];
    if (!v) continue;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(v) || Number.isNaN(Date.parse(v + "T00:00:00Z"))) {
      dateErrors.push({ campo, valor: v });
    }
  }

  const filters: ContratoSearchFilters = {
    cluster_id: params.cluster_id,
    cd_tce: params.cd_tce,
    cd_ibge: params.cd_ibge,
    modalidade: params.modalidade,
    fornecedor_cnpj: params.fornecedor_cnpj,
    orgao_codigo: params.orgao_codigo,
    escola_slug: params.escola_slug,
    q: params.q,
    since: params.since,
    until: params.until,
    em_quarentena: params.em_quarentena === "true" ? true : undefined,
    page,
    limit: 50,
    order,
  };

  let result: ContratoSearchPage | null = null;
  let err: string | null = null;
  if (dateErrors.length > 0) {
    err = `Data inválida em ${dateErrors
      .map((d) => `${d.campo}="${d.valor}"`)
      .join(" e ")}. Use o formato AAAA-MM-DD (ex: 2024-12-31).`;
  } else {
    try {
      result = await contratosApi.search(filters);
    } catch (e) {
      err = e instanceof Error ? e.message : "erro";
    }
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
  if (params.since || params.until) {
    const inicio = params.since ? fmtDateBR(params.since) : "—";
    const fim = params.until ? fmtDateBR(params.until) : "—";
    labels.push({ tipo: "período", valor: `${inicio} a ${fim}` });
  }
  if (params.q) {
    labels.push({ tipo: "busca", valor: `"${params.q}"` });
  }
  if (params.em_quarentena === "true") {
    labels.push({ tipo: "filtro", valor: "em quarentena" });
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

      {/* Form de ordenacao + filtros editaveis. Preserva os IDs imutaveis
          (cluster_id, fornecedor_cnpj, etc) via hidden inputs. */}
      <form
        action="/contratos"
        method="get"
        className="border border-line rounded-md p-4 bg-white space-y-3"
      >
        {/* Hidden: identificadores que nao queremos editar via form */}
        {params.cluster_id && (
          <input type="hidden" name="cluster_id" value={params.cluster_id} />
        )}
        {params.cluster_nome && (
          <input type="hidden" name="cluster_nome" value={params.cluster_nome} />
        )}
        {params.cd_tce && <input type="hidden" name="cd_tce" value={params.cd_tce} />}
        {params.cd_ibge && <input type="hidden" name="cd_ibge" value={params.cd_ibge} />}
        {params.municipio_nome && (
          <input type="hidden" name="municipio_nome" value={params.municipio_nome} />
        )}
        {params.fornecedor_cnpj && (
          <input
            type="hidden"
            name="fornecedor_cnpj"
            value={params.fornecedor_cnpj}
          />
        )}
        {params.fornecedor_nome && (
          <input
            type="hidden"
            name="fornecedor_nome"
            value={params.fornecedor_nome}
          />
        )}
        {params.orgao_codigo && (
          <input type="hidden" name="orgao_codigo" value={params.orgao_codigo} />
        )}
        {params.orgao_nome && (
          <input type="hidden" name="orgao_nome" value={params.orgao_nome} />
        )}
        {params.escola_slug && (
          <input type="hidden" name="escola_slug" value={params.escola_slug} />
        )}

        <div className="space-y-1">
          <label className="text-xs uppercase tracking-wide text-muted block">
            Busca textual (objeto, fornecedor ou órgão)
          </label>
          <input
            name="q"
            defaultValue={params.q ?? ""}
            placeholder='ex: "Atlantica Construcoes" (fornecedor), "UPA Centro" (objeto), "Fundacao Estatal de Saude" (órgão), "Escola Carlos Gomes"'
            className="w-full border border-line rounded-md px-3 py-2 text-sm bg-paper"
          />
          <p className="text-xs text-muted">
            Substring case-insensitive em <strong>3 campos</strong>:
            descrição do objeto, nome do fornecedor que recebeu o pagamento,
            nome do órgão contratante. Acentos importam (digite como
            aparece na fonte; "Sao" ≠ "São").
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="space-y-1">
            <label className="text-xs uppercase tracking-wide text-muted block">
              Ordenação
            </label>
            <select
              name="order"
              defaultValue={order}
              className="w-full border border-line rounded-md px-2 py-1.5 text-sm bg-paper"
            >
              <option value="valor_desc">Maior valor primeiro</option>
              <option value="valor_asc">Menor valor primeiro</option>
              <option value="data_desc">Mais recente primeiro</option>
              <option value="data_asc">Mais antigo primeiro</option>
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-xs uppercase tracking-wide text-muted block">
              Modalidade
            </label>
            <select
              name="modalidade"
              defaultValue={params.modalidade ?? ""}
              className="w-full border border-line rounded-md px-2 py-1.5 text-sm bg-paper"
            >
              <option value="">todas</option>
              <option value="pregao">pregão</option>
              <option value="dispensa">dispensa</option>
              <option value="concorrencia">concorrência</option>
              <option value="tomada_precos">tomada de preços</option>
              <option value="convite">convite</option>
              <option value="inexigibilidade">inexigibilidade</option>
              <option value="credenciamento">credenciamento</option>
              <option value="chamamento_publico">chamamento público</option>
              <option value="sem_modalidade">sem modalidade resolvida</option>
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-xs uppercase tracking-wide text-muted block">
              Data inicial
            </label>
            <input
              type="date"
              name="since"
              defaultValue={params.since ?? ""}
              className="w-full border border-line rounded-md px-2 py-1.5 text-sm bg-paper"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs uppercase tracking-wide text-muted block">
              Data final
            </label>
            <input
              type="date"
              name="until"
              defaultValue={params.until ?? ""}
              className="w-full border border-line rounded-md px-2 py-1.5 text-sm bg-paper"
            />
          </div>
        </div>

        <div className="flex items-baseline justify-between flex-wrap gap-3">
          <label className="text-xs text-muted flex items-baseline gap-2">
            <input
              type="checkbox"
              name="em_quarentena"
              value="true"
              defaultChecked={params.em_quarentena === "true"}
            />
            Apenas contratos em quarentena (sem cluster identificado)
          </label>
          <button
            type="submit"
            className="border border-ink rounded-md px-4 py-1.5 text-sm no-underline hover:bg-ink hover:text-paper"
          >
            Aplicar
          </button>
        </div>
      </form>

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
            hint={`${result.limit} por página · ${ORDER_LABEL[order] ?? order}`}
          />
        </section>
      )}

      {err && (
        <div className="border border-attention/40 bg-attention/5 rounded-md p-4 text-sm">
          <p className="font-semibold text-attention mb-1">
            {dateErrors.length > 0 ? "Filtro inválido" : "Falha ao consultar"}
          </p>
          <p className="text-muted">{err}</p>
          {dateErrors.length > 0 && (
            <p className="text-xs text-muted mt-2">
              Ajuste o filtro acima e clique em &quot;Aplicar&quot;, ou{" "}
              <Link href="/contratos">limpe os filtros</Link>.
            </p>
          )}
        </div>
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
