// Cliente da API do Quanto Pagou. Server Components fazem fetch direto.

const API_BASE =
  process.env.QUANTOPAGOU_API_BASE ?? "http://127.0.0.1:8001";

export type Cluster = {
  cluster_id: string;
  cluster_version: string;
  descricao_canonica: string;
  categoria: string;
  n_itens: number;
};

export type Pares = {
  cluster_id: string;
  cluster_version: string;
  ente_nivel: string;
  uf: string;
  porte: string;
  n: number;
  minimo: string;
  p25: string;
  mediana: string;
  p75: string;
  maximo: string;
  iqr: string;
};

export type RankingOrgao = {
  cluster_id: string;
  cluster_version: string;
  orgao_codigo: string;
  orgao_nome: string;
  n_compras: number;
  mediana_orgao: string;
  valor_total_periodo: string;
};

export type Item = {
  raw_id: number;
  cluster_id: string | null;
  cluster_version: string | null;
  metodo_resolucao: string;
  confianca_resolucao: number;
  descricao_original: string;
  catmat_id: string | null;
  orgao_codigo: string | null;
  orgao_nome: string | null;
  fornecedor_cnpj: string | null;
  fornecedor_nome: string | null;
  contract_date: string | null;
  valor_unitario: string | null;
  valor_unitario_normalizado: string | null;
  unidade_base: string | null;
  fator_conversao: string | null;
  em_quarentena: boolean;
  motivo_quarentena: string | null;
  pares: Pares | null;
};

// TTL default pra fetches agregados (clusters, /pares, /stats/pr, /manchetes,
// perfis, etc). Ingestao real e cron weekly, entao 30min nao desfasa nada.
// Buscas interativas com query do usuario chamam `jgetLive` (no-store).
const REVALIDATE_DEFAULT_S = 1800;

export async function jget<T>(path: string): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    next: { revalidate: REVALIDATE_DEFAULT_S },
  });
  if (!r.ok) throw new Error(`API ${path} -> ${r.status}`);
  return (await r.json()) as T;
}

/** Sem cache. Use em buscas interativas com query string viva
 * (ex: /contratos/search?q=..., /instituicoes/search?q=...). */
export async function jgetLive<T>(path: string): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`API ${path} -> ${r.status}`);
  return (await r.json()) as T;
}

export const api = {
  clusters: () => jget<Cluster[]>("/clusters"),
  paresFor: (cluster_id: string) =>
    jget<Pares[]>(`/pares?cluster_id=${encodeURIComponent(cluster_id)}`),
  rankingOrgaos: (cluster_id: string, order = "mediana_desc", limit = 10) =>
    jget<RankingOrgao[]>(
      `/ranking/orgaos?cluster_id=${encodeURIComponent(cluster_id)}&order=${order}&limit=${limit}`,
    ),
  item: (raw_id: number) => jget<Item>(`/item/${raw_id}`),
};

// Helpers de formatacao em PT-BR.
export const fmtBRL = (n: number | string | null | undefined) =>
  n == null
    ? "-"
    : new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
        Number(n),
      );

export const fmtPct = (n: number) =>
  new Intl.NumberFormat("pt-BR", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(n);

export const fmtNum = (n: number | string, dec = 2) =>
  new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: dec,
    maximumFractionDigits: dec,
  }).format(Number(n));

// Formato compacto pra valores grandes — usado em stat cards onde
// o numero completo transborda. Mantem precisao razoavel:
//   >= 1 bi -> "R$ 5,12 bi"
//   >= 1 mi -> "R$ 234,5 mi"
//   >= 1 mil -> "R$ 234,5 mil"
//   else  -> fmtBRL completo (R$ 1.234,56)
// Para listagens detalhadas (linha de contrato, ranking pequeno) usar
// fmtBRL; para cards de resumo no topo de pagina, usar fmtBRLCompact.
export const fmtBRLCompact = (n: number | string | null | undefined): string => {
  if (n == null) return "-";
  const v = Number(n);
  if (!Number.isFinite(v)) return "-";
  const abs = Math.abs(v);
  const sign = v < 0 ? "-" : "";
  if (abs >= 1e9) return `${sign}R$ ${(v / 1e9).toFixed(2).replace(".", ",")} bi`;
  if (abs >= 1e6) return `${sign}R$ ${(v / 1e6).toFixed(1).replace(".", ",")} mi`;
  if (abs >= 1e3) return `${sign}R$ ${(v / 1e3).toFixed(1).replace(".", ",")} mil`;
  return fmtBRL(v);
};
