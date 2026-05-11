// LGPD L.13 — botão que abre /correcoes pré-preenchido para contestar
// uma decisão automatizada (LGPD art. 20). Reusa o pipeline de L.12 com
// tipo `revisao_ranking` (SLA 15d).

import Link from "next/link";

export function BotaoContestarRanking({
  url,
  contexto,
  rotulo = "Contestar este ranking",
}: {
  /** URL afetada que será pré-preenchida (ex: /manchetes ou /cluster/X). */
  url: string;
  /** Texto pré-preenchido no campo "descrição" — descreve qual ranking
   *  está sendo contestado. Deve ter >= 20 caracteres senão o submit falha. */
  contexto: string;
  rotulo?: string;
}) {
  const params = new URLSearchParams({
    tipo: "revisao_ranking",
    url,
    descricao: contexto,
  });
  return (
    <Link
      href={`/correcoes?${params.toString()}#form`}
      className="text-xs text-muted no-underline hover:underline"
      prefetch={false}
    >
      {rotulo}
    </Link>
  );
}
