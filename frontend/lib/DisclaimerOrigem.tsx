// LGPD L.11 — disclaimer de origem reusavel (PLANO §18 L.11).
//
// Aparece em paginas que mostram dados extraidos de portais publicos
// (TCE-PR, Compras.gov.br). Reduz risco de leitura como "dado original
// nosso" e da gancho explicito pro canal de correcoes.

import Link from "next/link";

type Fonte = "tce-pr" | "compras-gov-br" | "mista";

const FONTE_LABEL: Record<Fonte, string> = {
  "tce-pr": "TCE-PR (PIT semanal)",
  "compras-gov-br": "Compras.gov.br",
  mista: "TCE-PR + Compras.gov.br",
};

export function DisclaimerOrigem({
  fonte = "tce-pr",
  atualizado_em,
}: {
  fonte?: Fonte;
  atualizado_em?: string | null;
}) {
  const data = atualizado_em ? fmtDataCurta(atualizado_em) : "última semana";
  return (
    <aside
      className="border border-line bg-paper rounded-md px-3 py-2 text-xs text-muted leading-relaxed"
      role="note"
    >
      Dados extraídos de <strong>{FONTE_LABEL[fonte]}</strong> em {data}.
      Possíveis erros — <Link href="/correcoes">reportar correção</Link>.
      Presença aqui não implica irregularidade. Saiba mais em{" "}
      <Link href="/metodologia">/metodologia</Link>.
    </aside>
  );
}

function fmtDataCurta(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}
