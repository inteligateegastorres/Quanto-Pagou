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
  cd_tce: string;
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
  raw_id: number;
  contrato_id: string;
  municipio: string | null;
  orgao_nome: string;
  descricao: string;
  valor_total: string;
  contract_date: string | null;
  cluster_id: string | null;
  em_quarentena: boolean;
};

export type ContratoDetalhe = {
  raw_id: number;
  source: string;
  source_id: string | null;
  source_url: string | null;
  contract_date: string | null;
  orgao_codigo: string | null;
  orgao_nome: string | null;
  fornecedor_cnpj: string | null;
  fornecedor_nome: string | null;
  descricao: string;
  valor_total: string | null;
  valor_unitario: string | null;
  quantidade: string | null;
  unidade: string | null;
  modalidade: string | null;
  catmat_id: string | null;
  catser_id: string | null;
  raw_payload: Record<string, unknown>;
  cluster_id: string | null;
  cluster_version: string | null;
  cluster_descricao: string | null;
  metodo_resolucao: string | null;
  confianca_resolucao: number | null;
  em_quarentena: boolean;
  motivo_quarentena: string | null;
  snapshot_id: string;
  snapshot_period_start: string | null;
  snapshot_period_end: string | null;
  snapshot_hash_sha256: string | null;
  snapshot_ingested_at: string;
  cd_ibge: string | null;
  municipio_nome: string | null;
};

export const contrato = {
  detalhe: (rawId: number) =>
    jget<ContratoDetalhe>(`/contrato/${rawId}`),
};

export type ContratoSearchItem = {
  raw_id: number;
  source_id: string | null;
  municipio: string | null;
  cd_tce: string | null;
  orgao_nome: string | null;
  fornecedor_cnpj: string | null;
  fornecedor_nome: string | null;
  descricao: string;
  valor_total: string | null;
  contract_date: string | null;
  cluster_id: string | null;
  cluster_descricao: string | null;
  modalidade: string | null;
  em_quarentena: boolean;
};

export type ContratoSearchPage = {
  page: number;
  limit: number;
  total: number;
  valor_total_filtrado: string;
  contratos: ContratoSearchItem[];
};

export type ContratoSearchFilters = {
  cluster_id?: string;
  cd_tce?: string;
  cd_ibge?: string;
  modalidade?: string;
  fornecedor_cnpj?: string;
  orgao_codigo?: string;
  escola_slug?: string;
  source?: string;
  em_quarentena?: boolean;
  q?: string;
  since?: string;
  until?: string;
  page?: number;
  limit?: number;
  order?: string;
};

export type InstituicaoFornecedor = {
  fornecedor_cnpj: string;
  fornecedor_nome: string | null;
  n_contratos: number;
  valor_total: string;
  n_municipios: number;
};

export type InstituicaoOrgao = {
  orgao_codigo: string;
  orgao_nome: string;
  cd_tce: string | null;
  cd_ibge: string | null;
  municipio: string | null;
  n_contratos: number;
  valor_total: string;
};

export type InstituicaoObjeto = {
  cd_tce: string | null;
  cd_ibge: string | null;
  municipio: string | null;
  orgao_codigo: string;
  orgao_nome: string;
  n_contratos: number;
  valor_total: string;
};

export type InstituicaoFornecedorObjeto = {
  fornecedor_cnpj: string;
  fornecedor_nome: string | null;
  n_contratos: number;
  valor_total: string;
  n_municipios: number;
};

export type InstituicoesSearch = {
  q: string;
  fornecedores: InstituicaoFornecedor[];
  orgaos: InstituicaoOrgao[];
  objetos: InstituicaoObjeto[];
  fornecedores_no_objeto: InstituicaoFornecedorObjeto[];
  total_fornecedores: number;
  total_orgaos: number;
  total_objeto_contratos: number;
  total_fornecedores_no_objeto: number;
  valor_total_objeto: string;
};

export const instituicoes = {
  search: (q: string, limit = 20) =>
    jget<InstituicoesSearch>(
      `/instituicoes/search?q=${encodeURIComponent(q)}&limit=${limit}`,
    ),
};

export const contratos = {
  search: (filters: ContratoSearchFilters = {}) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(filters)) {
      if (v !== undefined && v !== null && v !== "") {
        qs.set(k, String(v));
      }
    }
    const q = qs.toString();
    return jget<ContratoSearchPage>(`/contratos/search${q ? "?" + q : ""}`);
  },
};

export type EscolaListItem = {
  escola_slug: string;
  escola_nome: string;
  n_mencoes: number;
  n_municipios: number;
  valor_total: string;
};

export type EscolaContrato = {
  raw_id: number;
  contrato_id: string | null;
  municipio: string | null;
  cd_tce: string | null;
  orgao_nome: string | null;
  descricao: string;
  valor_total: string | null;
  contract_date: string | null;
  cluster_id: string | null;
  padrao: string;
  escola_nome: string;
};

export const escolas = {
  lista: (opts: { search?: string; cd_tce?: string; limit?: number } = {}) => {
    const qs = new URLSearchParams();
    if (opts.search) qs.set("search", opts.search);
    if (opts.cd_tce) qs.set("cd_tce", opts.cd_tce);
    if (opts.limit != null) qs.set("limit", String(opts.limit));
    const q = qs.toString();
    return jget<EscolaListItem[]>(`/escolas${q ? "?" + q : ""}`);
  },
  contratos: (slug: string, limit = 50) =>
    jget<EscolaContrato[]>(
      `/escolas/${encodeURIComponent(slug)}/contratos?limit=${limit}`,
    ),
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
  porModalidade: (cnpj: string) =>
    jget<FornecedorAgregado[]>(`/fornecedor/${encodeURIComponent(cnpj)}/por-modalidade`),
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

export type MunicipioListItem = MunicipioInfo & {
  n_contratos: number;
  valor_total: string;
};

export type FornecedorListItem = {
  fornecedor_cnpj: string;
  fornecedor_nome: string | null;
  n_contratos: number;
  valor_total: string;
  n_municipios_distintos: number;
};

export type StatsPrModalidade = { modalidade: string; n_contratos: number };
export type StatsPrTopCluster = {
  cluster_id: string;
  descricao_canonica: string | null;
  n_contratos: number;
};
export type StatsPr = {
  total_contratos: number;
  total_municipios: number;
  total_fornecedores: number;
  n_em_cluster: number;
  n_em_quarentena: number;
  cobertura_cluster_pct: number;
  valor_total_pr: string | null;
  modalidades: StatsPrModalidade[];
  top_clusters: StatsPrTopCluster[];
  last_snapshot_at: string | null;
  n_escolas_catalogadas: number;
};

export const stats = {
  pr: () => jget<StatsPr>("/stats/pr"),
};

export type DispensaTopFornecedor = {
  fornecedor_cnpj: string;
  fornecedor_nome: string | null;
  n_dispensas: number;
  valor_total_dispensas: string;
  n_municipios: number;
  n_orgaos: number;
  cnpj_mascarado: boolean;
};

export const dispensas = {
  topFornecedores: (opts: { limit?: number; min_contratos?: number; incluir_cpf_mascarado?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (opts.limit != null) qs.set("limit", String(opts.limit));
    if (opts.min_contratos != null) qs.set("min_contratos", String(opts.min_contratos));
    if (opts.incluir_cpf_mascarado) qs.set("incluir_cpf_mascarado", "true");
    const q = qs.toString();
    return jget<DispensaTopFornecedor[]>(
      `/tce-pr/dispensas/top-fornecedores${q ? "?" + q : ""}`,
    );
  },
};

export const buscar = {
  municipios: (opts: { search?: string; limit?: number } = {}) => {
    const qs = new URLSearchParams();
    if (opts.search) qs.set("search", opts.search);
    if (opts.limit != null) qs.set("limit", String(opts.limit));
    const q = qs.toString();
    return jget<MunicipioListItem[]>(`/municipios${q ? "?" + q : ""}`);
  },
  fornecedores: (opts: { search?: string; min_contratos?: number; limit?: number } = {}) => {
    const qs = new URLSearchParams();
    if (opts.search) qs.set("search", opts.search);
    if (opts.min_contratos != null) qs.set("min_contratos", String(opts.min_contratos));
    if (opts.limit != null) qs.set("limit", String(opts.limit));
    const q = qs.toString();
    return jget<FornecedorListItem[]>(`/fornecedores${q ? "?" + q : ""}`);
  },
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
    opts: {
      porte?: string;
      modalidade?: string;
      since?: string;
      until?: string;
      order?: string;
      limit?: number;
    } = {},
  ) => {
    const qs = new URLSearchParams();
    if (opts.porte) qs.set("porte", opts.porte);
    if (opts.modalidade) qs.set("modalidade", opts.modalidade);
    if (opts.since) qs.set("since", opts.since);
    if (opts.until) qs.set("until", opts.until);
    if (opts.order) qs.set("order", opts.order);
    if (opts.limit != null) qs.set("limit", String(opts.limit));
    const q = qs.toString();
    return jget<RankingMunicipio[]>(
      `/tce-pr/cluster/${encodeURIComponent(clusterId)}/ranking-municipios${q ? "?" + q : ""}`,
    );
  },
};

// ----------------------------- Manchetes ------------------------------

export type Manchete = {
  rank_no_dia: number;
  cluster_id: string;
  cluster_version: string;
  cd_tce: string;
  cd_ibge: string | null;
  municipio_nome: string | null;
  porte: string | null;
  populacao: number | null;
  n_sujeito: number;
  valor_total_sujeito: string;
  med_sujeito: string;
  med_cluster: string;
  spread: string;
  iqr_sujeito: string;
  iqr_cluster: string;
  comparab_proxy: string;
  spread_90d: string | null;
  spread_180d: string | null;
  spread_365d: string | null;
  janelas_passadas: number;
  rank_score: string;
  parametros_hash: string;
  refresh_em: string;
};

export type ManchteSaida = {
  saiu_em: string;
  manchete_id: string;
  motivo: string;
  cluster_id: string | null;
  municipio_nome: string | null;
  spread_anterior: string | null;
  parametros_hash: string;
};

export type ManchteCandidatoDiag = {
  cluster_id: string;
  n_sujeito: number;
  spread: string | null;
  iqr_sujeito: string | null;
  comparab_proxy: string | null;
  motivo_falha: string | null;
};

export type ManchteDiagnostico = {
  cd_tce: string;
  municipio_nome: string | null;
  populacao: number | null;
  parametros_hash: string | null;
  ativas: Manchete[];
  candidatos: ManchteCandidatoDiag[];
};

export const manchetes = {
  lista: () => jget<Manchete[]>("/manchetes"),
  saidas: (dias = 90) => jget<ManchteSaida[]>(`/manchetes/saidas?dias=${dias}`),
  diagnostico: (cd_tce: string) =>
    jget<ManchteDiagnostico>(`/manchetes/diagnostico?cd_tce=${encodeURIComponent(cd_tce)}`),
};
