import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { fmtBRL } from "@/lib/api";
import { Stat } from "@/lib/Stat";
import {
  AtualizadoBadge,
  ConfiancaBadge,
  FontePrimariaBadge,
  SemClusterBadge,
} from "@/lib/Badge";
import { contrato as contratoApi, type ContratoDetalhe } from "@/lib/tcepr";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  return {
    title: `Contrato #${id} · Quanto Pagou`,
    description: "Detalhe de contrato público com link para a fonte primária.",
    robots: { index: false, follow: false }, // alinhado com guardrail §6.5 da pagina de fornecedor
  };
}

export default async function ContratoPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const rawId = Number.parseInt(id, 10);
  if (!Number.isFinite(rawId) || rawId <= 0) notFound();

  let c: ContratoDetalhe;
  try {
    c = await contratoApi.detalhe(rawId);
  } catch {
    notFound();
  }

  const isTcePr = c.source.startsWith("tce_pr/");
  const isCompras = c.source.startsWith("compras_gov_br/");

  // Fonte primaria: monta o link mais util por tipo de fonte.
  // TCE-PR: ZIP anual publico (mesmo do snapshot). Inclui ano para o
  // usuario achar facil descompactando.
  // Compras.gov.br: o snapshot e JSON.gz local; o usuario pode bater
  // no proprio compras.gov.br buscando pelo numeroControlePNCP do payload.
  const ano =
    c.contract_date?.slice(0, 4) ??
    c.snapshot_period_start?.slice(0, 4) ??
    null;
  const linkTceZip = ano
    ? `https://pit.tce.pr.gov.br/Arquivos/${ano}_PIT_TodosArquivos.zip`
    : null;

  const numeroPncp = (c.raw_payload as Record<string, unknown>)[
    "numeroControlePncpContrato"
  ] as string | undefined;
  const linkPncp = numeroPncp
    ? `https://pncp.gov.br/app/contratos/${encodeURIComponent(numeroPncp)}`
    : null;

  return (
    <article className="space-y-10 max-w-3xl">
      <header className="space-y-2">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <p className="text-xs uppercase tracking-wide text-muted">
          Contrato {c.source_id ?? `#${c.raw_id}`} · fonte: <code>{c.source}</code>
        </p>
        <h1 className="text-2xl font-semibold tracking-tight leading-snug">
          {c.descricao.length > 200
            ? c.descricao.slice(0, 200) + "…"
            : c.descricao}
        </h1>
        <div className="flex items-baseline gap-2 flex-wrap pt-1">
          {c.em_quarentena ? (
            <SemClusterBadge motivo={c.motivo_quarentena} />
          ) : (
            <ConfiancaBadge confianca={c.confianca_resolucao} />
          )}
          <FontePrimariaBadge url={c.source_url} />
          <AtualizadoBadge iso={c.snapshot_ingested_at} />
        </div>
      </header>

      <section className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <Stat label="Valor total" value={fmtBRL(c.valor_total)} />
        <Stat
          label="Data assinatura"
          value={c.contract_date ? fmtDateBR(c.contract_date) : "—"}
        />
        <Stat
          label="Modalidade"
          value={c.modalidade ?? "—"}
          hint={c.modalidade ? undefined : "não resolvida"}
        />
        <Stat
          label="Confiança cluster"
          value={
            c.confianca_resolucao != null
              ? c.confianca_resolucao.toFixed(2)
              : "—"
          }
          hint={c.metodo_resolucao ?? undefined}
        />
      </section>

      <section className="space-y-3 border border-line rounded-md p-5 bg-white">
        <h2 className="text-base font-semibold">Partes</h2>
        <Field label="Órgão contratante">
          {c.orgao_nome ?? "—"}
          {c.orgao_codigo && (
            <span className="text-xs text-muted"> (código {c.orgao_codigo})</span>
          )}
          {c.municipio_nome && isTcePr && (
            <>
              {" · "}
              {c.cd_ibge ? (
                <Link
                  href={`/municipio/${(c.raw_payload as Record<string, string>).cd_tce}`}
                  className="no-underline hover:underline"
                >
                  {c.municipio_nome}/PR
                </Link>
              ) : (
                <span>{c.municipio_nome}/PR</span>
              )}
            </>
          )}
        </Field>
        <Field label="Fornecedor">
          {c.fornecedor_cnpj ? (
            <Link
              href={`/fornecedor/${encodeURIComponent(c.fornecedor_cnpj)}`}
              className="no-underline hover:underline font-medium"
            >
              {c.fornecedor_nome ?? "—"}
            </Link>
          ) : (
            c.fornecedor_nome ?? "—"
          )}
          {c.fornecedor_cnpj && (
            <span className="text-xs text-muted"> · CNPJ {c.fornecedor_cnpj}</span>
          )}
        </Field>
        {c.cluster_descricao && (
          <Field label="Categoria">
            {c.cluster_descricao}
            <span className="text-xs text-muted">
              {" "}
              ({c.cluster_id} · {c.metodo_resolucao})
            </span>
          </Field>
        )}
        {c.em_quarentena && c.motivo_quarentena && (
          <Field label="Motivo da quarentena">
            <span className="text-attention text-sm">{c.motivo_quarentena}</span>
          </Field>
        )}
      </section>

      <section className="space-y-3 border border-line rounded-md p-5 bg-white">
        <h2 className="text-base font-semibold">Objeto do contrato</h2>
        <p className="text-sm leading-relaxed">{c.descricao}</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2 text-xs text-muted">
          {c.quantidade != null && (
            <Field small label="Quantidade">
              {c.quantidade} {c.unidade ?? ""}
            </Field>
          )}
          {c.valor_unitario != null && (
            <Field small label="Valor unitário">
              {fmtBRL(c.valor_unitario)}
            </Field>
          )}
          {c.catmat_id && (
            <Field small label="CATMAT">
              {c.catmat_id}
            </Field>
          )}
          {c.catser_id && (
            <Field small label="CATSER">
              {c.catser_id}
            </Field>
          )}
        </div>
      </section>

      <section className="space-y-3 border border-attention/40 bg-attention/5 rounded-md p-5">
        <h2 className="text-base font-semibold text-attention">
          Fonte primária
        </h2>
        {isTcePr && (
          <div className="text-sm text-muted space-y-2">
            <p>
              Este contrato vem do <strong>arquivo consolidado público</strong>{" "}
              que o TCE-PR publica semanalmente na Plataforma de Informação
              para Todos (PIT). O arquivo é um ZIP anual contendo um sub-zip
              por (município × tema), com XMLs auditáveis. Não é necessário
              cadastro.
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>idContrato no XML:</strong>{" "}
                <code>{c.source_id}</code>
              </li>
              {linkTceZip && (
                <li>
                  <strong>ZIP do ano:</strong>{" "}
                  <a href={linkTceZip} target="_blank" rel="noreferrer">
                    {linkTceZip}
                  </a>
                </li>
              )}
              <li>
                <strong>Caminho dentro do ZIP:</strong>{" "}
                <code>
                  {ano ?? "{ano}"}_
                  {(c.raw_payload as Record<string, string>).cd_tce ?? "{cd_tce}"}_Contrato.zip
                  {" → "}
                  {ano ?? "{ano}"}_
                  {(c.raw_payload as Record<string, string>).cd_tce ?? "{cd_tce}"}_Contrato.xml
                </code>
              </li>
              <li>
                <strong>Página de download oficial:</strong>{" "}
                <a
                  href="https://pit.tce.pr.gov.br/Dados/DadosConsulta/Consolidado"
                  target="_blank"
                  rel="noreferrer"
                >
                  pit.tce.pr.gov.br/Dados/DadosConsulta/Consolidado
                </a>
              </li>
            </ul>
          </div>
        )}
        {isCompras && (
          <div className="text-sm text-muted space-y-2">
            <p>
              Este contrato vem da <strong>API pública Compras.gov.br</strong>{" "}
              (Dados Abertos), endpoint{" "}
              <code>/modulo-contratos/2_consultarContratosItem</code>.
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>source_id:</strong> <code>{c.source_id}</code>
              </li>
              {linkPncp && (
                <li>
                  <strong>PNCP (Lei 14.133):</strong>{" "}
                  <a href={linkPncp} target="_blank" rel="noreferrer">
                    {linkPncp}
                  </a>
                </li>
              )}
              <li>
                <strong>API base:</strong>{" "}
                <a
                  href="https://dadosabertos.compras.gov.br"
                  target="_blank"
                  rel="noreferrer"
                >
                  dadosabertos.compras.gov.br
                </a>
              </li>
            </ul>
          </div>
        )}
        <details className="text-xs text-muted">
          <summary className="cursor-pointer">
            Snapshot interno (camada de durabilidade)
          </summary>
          <dl className="grid grid-cols-2 gap-2 pt-2">
            <dt>snapshot_id</dt>
            <dd className="font-mono text-xs">{c.snapshot_id}</dd>
            <dt>período</dt>
            <dd>
              {c.snapshot_period_start} → {c.snapshot_period_end}
            </dd>
            <dt>SHA-256</dt>
            <dd className="font-mono text-xs break-all">
              {c.snapshot_hash_sha256 || "—"}
            </dd>
            <dt>ingerido em</dt>
            <dd>{c.snapshot_ingested_at}</dd>
          </dl>
          <p className="pt-2">
            O pipeline preserva o payload bruto; toda canonicalização é uma
            função pura sobre snapshots e pode ser reprocessada.
          </p>
        </details>
      </section>

      <section className="space-y-2">
        <details className="text-xs">
          <summary className="cursor-pointer text-muted">
            Payload bruto (auditoria)
          </summary>
          <pre className="bg-paper border border-line rounded-md p-3 mt-2 overflow-x-auto text-xs">
{JSON.stringify(c.raw_payload, null, 2)}
          </pre>
        </details>
      </section>

      <section className="text-sm text-muted border-t border-line pt-6">
        <p>
          Encontrou erro neste contrato?{" "}
          <Link href="/correcoes">Reportar</Link> — SLA 48h. Linguagem e
          guardrails seguem o{" "}
          <Link href="/manifesto">manifesto</Link>.
        </p>
      </section>
    </article>
  );
}

function Field({
  label,
  small,
  children,
}: {
  label: string;
  small?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={small ? "" : "space-y-1"}>
      <div
        className={
          "uppercase tracking-wide text-muted " +
          (small ? "text-[0.65rem]" : "text-xs")
        }
      >
        {label}
      </div>
      <div className={small ? "text-xs" : "text-sm"}>{children}</div>
    </div>
  );
}

function fmtDateBR(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}
