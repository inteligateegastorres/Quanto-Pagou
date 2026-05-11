// LGPD L.12 — pagina publica de ticket (PLANO §18 L.12).
// noindex/nofollow: ticket especifico nao deve aparecer em busca.

import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import {
  correcoes,
  TIPO_LABEL,
  STATUS_LABEL,
  SLA_LABEL,
  type CorrecaoTicket,
} from "@/lib/correcoes";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ ticket_id: string }>;
}): Promise<Metadata> {
  const { ticket_id } = await params;
  return {
    title: `Ticket ${ticket_id} · Correções · Quanto Pagou`,
    description: "Acompanhamento público de ticket de correção.",
    robots: { index: false, follow: false, nocache: true },
  };
}

export default async function TicketPage({
  params,
}: {
  params: Promise<{ ticket_id: string }>;
}) {
  const { ticket_id } = await params;

  let t: CorrecaoTicket;
  try {
    t = await correcoes.consultar(ticket_id);
  } catch {
    notFound();
  }

  const prazoVencido = (() => {
    if (!t.prazo_iso) return false;
    if (t.resolvido_em) return false;
    return new Date(t.prazo_iso).getTime() < Date.now();
  })();

  return (
    <article className="max-w-2xl space-y-6">
      <Link href="/correcoes" className="text-xs text-muted no-underline">
        ← /correcoes
      </Link>
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-wide text-muted">
          Ticket público · acompanhamento sem cadastro
        </p>
        <h1 className="text-3xl font-semibold tracking-tight font-mono">
          {t.ticket_id}
        </h1>
      </header>

      <section className="border border-line rounded-md p-4 bg-white space-y-3 text-sm">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Field
            label="Status"
            value={STATUS_LABEL[t.status]}
            tone={
              t.status === "aberto" || t.status === "em_analise"
                ? "attention"
                : t.status.startsWith("resolvido")
                  ? "ok"
                  : "muted"
            }
          />
          <Field label="Tipo" value={TIPO_LABEL[t.tipo]} />
          <Field label="SLA" value={SLA_LABEL[t.sla_classe]} />
          <Field
            label="Aberto em"
            value={fmtDataHora(t.criado_em)}
          />
          {t.prazo_iso && (
            <Field
              label="Prazo nominal"
              value={fmtDataHora(t.prazo_iso)}
              tone={prazoVencido ? "attention" : "muted"}
              hint={
                prazoVencido && !t.resolvido_em
                  ? "Prazo vencido — auditoria pública"
                  : undefined
              }
            />
          )}
          {t.resolvido_em && (
            <Field
              label="Resolvido em"
              value={fmtDataHora(t.resolvido_em)}
              tone="ok"
            />
          )}
        </div>
      </section>

      {t.descricao_publica && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">
            {t.status.startsWith("resolvido") || t.status === "rejeitado"
              ? "Descrição original (publicada com autorização)"
              : "Descrição reportada"}
          </h2>
          <div className="border border-line rounded-md p-4 bg-white text-sm leading-relaxed whitespace-pre-wrap">
            {t.descricao_publica}
          </div>
        </section>
      )}

      {!t.descricao_publica && t.status !== "aberto" && (
        <section className="border border-dashed border-line rounded-md p-4 bg-paper text-sm text-muted">
          A descrição original deste ticket não foi autorizada pelo
          reportador para vitrine pública. Apenas a resolução abaixo (se
          houver) e o status são públicos.
        </section>
      )}

      {(t.url_afetada || t.raw_id_afetado || t.fornecedor_cnpj) && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">Referências</h2>
          <ul className="text-sm border border-line rounded-md p-4 bg-white space-y-1">
            {t.url_afetada && (
              <li>
                URL afetada:{" "}
                <a
                  href={t.url_afetada}
                  target="_blank"
                  rel="noreferrer"
                  className="break-all"
                >
                  {t.url_afetada}
                </a>
              </li>
            )}
            {t.raw_id_afetado != null && (
              <li>
                Contrato relacionado:{" "}
                <Link href={`/contrato/${t.raw_id_afetado}`}>
                  /contrato/{t.raw_id_afetado}
                </Link>
              </li>
            )}
            {t.fornecedor_cnpj && (
              <li>
                Fornecedor relacionado:{" "}
                <Link
                  href={`/fornecedor/${encodeURIComponent(t.fornecedor_cnpj)}`}
                >
                  /fornecedor/{t.fornecedor_cnpj}
                </Link>
                <span className="text-muted ml-1">
                  (perfil aberto só para PJ confirmado — ver L.2)
                </span>
              </li>
            )}
          </ul>
        </section>
      )}

      {t.resolucao_publica && (
        <section className="space-y-2">
          <h2 className="text-base font-semibold">Resolução</h2>
          <div className="border border-ok/40 bg-ok/5 rounded-md p-4 text-sm leading-relaxed whitespace-pre-wrap">
            {t.resolucao_publica}
          </div>
        </section>
      )}

      <footer className="text-xs text-muted border-t border-line pt-4 space-y-2">
        <p>
          Atualizações: o status muda conforme avançamos. Recarregue esta
          página a qualquer momento (sem cadastro). Auditoria interna em{" "}
          <code>analytics.audit_log</code> (L.10).
        </p>
        <p>
          Documentos:{" "}
          <Link href="/correcoes">/correcoes</Link>
          {" · "}
          <Link href="/lgpd">Canal LGPD</Link>
          {" · "}
          <Link href="/politica-privacidade">Política de Privacidade</Link>
        </p>
      </footer>
    </article>
  );
}

function Field({
  label,
  value,
  tone = "muted",
  hint,
}: {
  label: string;
  value: string;
  tone?: "ok" | "attention" | "muted";
  hint?: string;
}) {
  const cls =
    tone === "ok"
      ? "text-ok"
      : tone === "attention"
        ? "text-attention"
        : "text-ink";
  return (
    <div className="space-y-0.5">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className={`text-sm font-medium ${cls}`}>{value}</div>
      {hint && <div className="text-xs text-muted">{hint}</div>}
    </div>
  );
}

function fmtDataHora(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
