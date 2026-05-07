// Cliente para os endpoints TCE-PR da API local. Granularidade
// e por contrato (TCE-PR nao publica item-a-item) — UI deixa isso
// explicito para nao confundir com a comparacao federal CATMAT.

import { jget } from "./api";

export type TcePrSummary = {
  cd_ibge: string;
  municipio: string;
  n_contratos_total: number;
  valor_total: string;
  n_em_cluster: number;
  n_em_quarentena: number;
  cobertura_pct: number;
};

export type ContratoMunicipio = {
  cluster_id: string;
  cluster_version: string;
  cd_ibge: string | null;
  municipio: string | null;
  porte: string;
  orgao_codigo: string;
  orgao_nome: string;
  n_contratos: number;
  valor_total_periodo: string;
  mediana_valor_contrato: string;
  p25_valor: string;
  p75_valor: string;
};

export type FornecedorMunicipio = {
  cd_ibge: string | null;
  municipio: string | null;
  fornecedor_cnpj: string;
  fornecedor_nome: string | null;
  n_contratos: number;
  valor_total_periodo: string;
  n_orgaos_distintos: number;
};

export type RankingMunicipio = {
  cluster_id: string;
  cd_ibge: string;
  municipio: string;
  porte: string;
  n_contratos: number;
  valor_total_periodo: string;
  mediana_valor_contrato: string;
};

export type FornecedorPerfil = {
  fornecedor_cnpj: string;
  fornecedor_nome: string | null;
  n_contratos_total: number;
  valor_total: string;
  n_orgaos_distintos: number;
  n_municipios_distintos: number;
  primeiro_contrato: string | null;
  ultimo_contrato: string | null;
  cnpj_mascarado: boolean;
};

export type FornecedorAgregado = {
  chave: string;
  nome: string | null;
  n_contratos: number;
  valor_total: string;
};

export type FornecedorContrato = {
  contrato_id: string;
  municipio: string | null;
  orgao_nome: string;
  descricao: string;
  valor_total: string;
  contract_date: string | null;
  cluster_id: string | null;
  em_quarentena: boolean;
};

export const fornecedor = {
  perfil: (cnpj: string) =>
    jget<FornecedorPerfil>(`/fornecedor/${encodeURIComponent(cnpj)}`),
  porOrgao: (cnpj: string, limit = 15) =>
    jget<FornecedorAgregado[]>(`/fornecedor/${encodeURIComponent(cnpj)}/por-orgao?limit=${limit}`),
  porMunicipio: (cnpj: string, limit = 15) =>
    jget<FornecedorAgregado[]>(`/fornecedor/${encodeURIComponent(cnpj)}/por-municipio?limit=${limit}`),
  porCategoria: (cnpj: string) =>
    jget<FornecedorAgregado[]>(`/fornecedor/${encodeURIComponent(cnpj)}/por-categoria`),
  contratos: (cnpj: string, limit = 20) =>
    jget<FornecedorContrato[]>(`/fornecedor/${encodeURIComponent(cnpj)}/contratos?limit=${limit}`),
};

export type MunicipioInfo = {
  cd_tce: string;
  cd_ibge: string | null;
  nome: string;
  porte: string;
  catalogado: boolean;
};

export const tcepr = {
  resolveMunicipio: (key: string) =>
    jget<MunicipioInfo>(`/municipio/${encodeURIComponent(key)}/info`),
  resumo: (cdIbge: string) =>
    jget<TcePrSummary>(`/tce-pr/municipio/${cdIbge}/resumo`),
  contratosPorCluster: (cdIbge: string, opts: { cluster_id?: string; limit?: number } = {}) => {
    const qs = new URLSearchParams();
    if (opts.cluster_id) qs.set("cluster_id", opts.cluster_id);
    if (opts.limit != null) qs.set("limit", String(opts.limit));
    const q = qs.toString();
    return jget<ContratoMunicipio[]>(
      `/tce-pr/municipio/${cdIbge}/contratos-por-cluster${q ? "?" + q : ""}`,
    );
  },
  fornecedores: (cdIbge: string, limit = 20) =>
    jget<FornecedorMunicipio[]>(
      `/tce-pr/municipio/${cdIbge}/fornecedores?limit=${limit}`,
    ),
  comparacaoMunicipios: (
    clusterId: string,
    opts: { porte?: string; cluster_version?: string; limit?: number } = {},
  ) => {
    const qs = new URLSearchParams({ cluster_version: opts.cluster_version ?? "v1" });
    if (opts.porte) qs.set("porte", opts.porte);
    if (opts.limit != null) qs.set("limit", String(opts.limit));
    return jget<ContratoMunicipio[]>(
      `/tce-pr/cluster/${encodeURIComponent(clusterId)}/comparacao-municipios?${qs.toString()}`,
    );
  },
  rankingMunicipios: (
    clusterId: string,
    opts: { porte?: string; order?: string; limit?: number } = {},
  ) => {
    const qs = new URLSearchParams();
    if (opts.porte) qs.set("porte", opts.porte);
    if (opts.order) qs.set("order", opts.order);
    if (opts.limit != null) qs.set("limit", String(opts.limit));
    const q = qs.toString();
    return jget<RankingMunicipio[]>(
      `/tce-pr/cluster/${encodeURIComponent(clusterId)}/ranking-municipios${q ? "?" + q : ""}`,
    );
  },
};
