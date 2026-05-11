"use server";

// LGPD L.12 — Server Action: cria ticket + redireciona pra pagina publica.

import { redirect } from "next/navigation";
import { correcoes, type CorrecaoTipo } from "@/lib/correcoes";

const TIPOS_VALIDOS: CorrecaoTipo[] = [
  "factual",
  "lgpd_acesso",
  "lgpd_correcao",
  "lgpd_eliminacao",
  "classificacao_pj",
  "outro",
];

function strOrNull(fd: FormData, key: string): string | null {
  const v = fd.get(key);
  if (typeof v !== "string") return null;
  const t = v.trim();
  return t === "" ? null : t;
}

export async function criarTicketAction(fd: FormData): Promise<void> {
  const tipoRaw = fd.get("tipo");
  if (typeof tipoRaw !== "string" || !TIPOS_VALIDOS.includes(tipoRaw as CorrecaoTipo)) {
    throw new Error("tipo inválido");
  }
  const descricao = strOrNull(fd, "descricao");
  if (!descricao || descricao.length < 20) {
    throw new Error("descrição precisa de ao menos 20 caracteres");
  }
  const rawIdStr = strOrNull(fd, "raw_id_afetado");
  const rawId = rawIdStr ? Number(rawIdStr) : null;
  if (rawIdStr && !Number.isFinite(rawId)) {
    throw new Error("raw_id_afetado deve ser número");
  }

  const ticket = await correcoes.criar({
    tipo: tipoRaw as CorrecaoTipo,
    descricao,
    url_afetada: strOrNull(fd, "url_afetada"),
    raw_id_afetado: rawId,
    fornecedor_cnpj: strOrNull(fd, "fornecedor_cnpj"),
    fonte_correta: strOrNull(fd, "fonte_correta"),
    publicar_descricao: fd.get("publicar_descricao") === "on",
    contato_email: strOrNull(fd, "contato_email"),
  });
  redirect(`/correcoes/${ticket.ticket_id}`);
}
