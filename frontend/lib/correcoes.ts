// LGPD L.12 — cliente do endpoint /correcoes (PLANO §18 L.12).

import { jgetLive } from "@/lib/api";

const API_BASE =
  process.env.QUANTOPAGOU_API_BASE ?? "http://127.0.0.1:8001";

export type CorrecaoTipo =
  | "factual"
  | "lgpd_acesso"
  | "lgpd_correcao"
  | "lgpd_eliminacao"
  | "classificacao_pj"
  | "revisao_ranking"
  | "outro";

export type CorrecaoStatus =
  | "aberto"
  | "em_analise"
  | "resolvido_corrigido"
  | "resolvido_sem_correcao"
  | "rejeitado";

export type CorrecaoTicketIn = {
  tipo: CorrecaoTipo;
  descricao: string;
  url_afetada?: string | null;
  raw_id_afetado?: number | null;
  fornecedor_cnpj?: string | null;
  fonte_correta?: string | null;
  publicar_descricao?: boolean;
  contato_email?: string | null;
};

export type CorrecaoTicket = {
  ticket_id: string;
  criado_em: string;
  tipo: CorrecaoTipo;
  sla_classe: "factual_48h" | "lgpd_15d";
  status: CorrecaoStatus;
  descricao_publica: string | null;
  url_afetada: string | null;
  raw_id_afetado: number | null;
  fornecedor_cnpj: string | null;
  resolvido_em: string | null;
  resolucao_publica: string | null;
  prazo_iso: string | null;
};

export const correcoes = {
  async criar(payload: CorrecaoTicketIn): Promise<CorrecaoTicket> {
    const r = await fetch(`${API_BASE}/correcoes/ticket`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
    if (!r.ok) {
      let detail = `API /correcoes/ticket -> ${r.status}`;
      try {
        const body = await r.json();
        if (body?.detail) detail = String(body.detail);
      } catch {
        // ignora — usa default
      }
      throw new Error(detail);
    }
    return (await r.json()) as CorrecaoTicket;
  },
  consultar: (ticket_id: string) =>
    jgetLive<CorrecaoTicket>(
      `/correcoes/ticket/${encodeURIComponent(ticket_id)}`,
    ),
  recentes: (limit = 20) =>
    jgetLive<CorrecaoTicket[]>(`/correcoes/recentes?limit=${limit}`),
};

export const TIPO_LABEL: Record<CorrecaoTipo, string> = {
  factual: "Erro factual (dado errado)",
  lgpd_acesso: "LGPD — acesso aos dados (art. 18 II)",
  lgpd_correcao: "LGPD — correção de dado pessoal (art. 18 III)",
  lgpd_eliminacao: "LGPD — eliminação / tombstone (art. 18 IV)",
  classificacao_pj:
    "Classificação PJ — perfil indevidamente bloqueado ou exposto",
  revisao_ranking:
    "Revisão de decisão automatizada — ranking / manchete (art. 20)",
  outro: "Outro",
};

export const STATUS_LABEL: Record<CorrecaoStatus, string> = {
  aberto: "Aberto · em fila",
  em_analise: "Em análise",
  resolvido_corrigido: "Resolvido · com correção",
  resolvido_sem_correcao: "Resolvido · sem correção necessária",
  rejeitado: "Rejeitado · ver motivo",
};

export const SLA_LABEL: Record<"factual_48h" | "lgpd_15d", string> = {
  factual_48h: "48h (correção factual)",
  lgpd_15d: "15 dias (LGPD art. 19)",
};
