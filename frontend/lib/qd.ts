// Cliente da API publica do Querido Diario (OKBR).
// Doc: https://api.queridodiario.ok.org.br/docs
// Sem auth, sem rate-limit publicado. Usado direto do server component.

const QD_BASE =
  process.env.QUERIDO_DIARIO_API_BASE ?? "https://api.queridodiario.ok.org.br";

export type Gazette = {
  territory_id: string;
  territory_name: string;
  state_code: string;
  date: string; // YYYY-MM-DD
  edition: string | null;
  is_extra_edition: boolean;
  url: string; // PDF
  txt_url: string | null;
  scraped_at: string;
  excerpts: string[];
};

export type GazettesResponse = {
  gazettes: Gazette[];
  total_gazettes: number;
};

async function jget<T>(path: string, params: Record<string, string | number>): Promise<T> {
  const qs = new URLSearchParams(
    Object.entries(params).map(([k, v]) => [k, String(v)]),
  );
  const url = `${QD_BASE}${path}?${qs.toString()}`;
  const r = await fetch(url, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!r.ok) {
    throw new Error(`QD ${path} -> ${r.status}`);
  }
  return (await r.json()) as T;
}

export const qd = {
  // Lista diarios com filtro opcional de query textual.
  gazettes: (
    territoryId: string,
    opts: {
      since?: string; // YYYY-MM-DD
      until?: string;
      querystring?: string;
      size?: number;
      page?: number;
    } = {},
  ) => {
    const params: Record<string, string | number> = {
      territory_ids: territoryId,
      size: opts.size ?? 10,
      page: opts.page ?? 1,
      sort_by: "descending_date",
    };
    if (opts.since) params.since = opts.since;
    if (opts.until) params.until = opts.until;
    if (opts.querystring) params.querystring = opts.querystring;
    return jget<GazettesResponse>("/gazettes", params);
  },

  // Pega o diario mais antigo disponivel (sort ascending) — usado para
  // descobrir desde quando ha cobertura.
  gazettesAscending: (territoryId: string) =>
    jget<GazettesResponse>("/gazettes", {
      territory_ids: territoryId,
      size: 1,
      page: 1,
      sort_by: "ascending_date",
    }),
};

// Helper de formato de data PT-BR.
export function fmtDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}
