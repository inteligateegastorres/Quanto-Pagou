// Cliente da API do Quanto Pagou. Server Components fazem fetch direto.

const API_BASE =
  process.env.QUANTOPAGOU_API_BASE ?? "http://127.0.0.1:8000";

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

async function jget<T>(path: string): Promise<T> {
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
