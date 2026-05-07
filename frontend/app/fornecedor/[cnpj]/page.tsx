import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { fmtBRL } from "@/lib/api";
import {
  fornecedor as fornecedorApi,
  type FornecedorPerfil,
  type FornecedorAgregado,
  type FornecedorContrato,
} from "@/lib/tcepr";

export const dynamic = "force-dynamic";

// Guardrail §6.5 do plano: noindex/nofollow na Fase 1; reavaliar com
// revisão jurídica antes de tornar SEO-amigável.
export async function generateMetadata({
  params,
}: {
  params: Promise<{ cnpj: string }>;
}): Promise<Metadata> {
  const { cnpj } = await params;
  return {
    title: `Fornecedor público ${cnpj} · Quanto Pagou`,
    description:
      "Perfil de fornecedor — apresenta dados públicos extraídos de portais oficiais. A presença aqui não implica irregularidade.",
    robots: { index: false, follow: false, nocache: true },
  };
}

export default async function FornecedorPage({
  params,
}: {
  params: Promise<{ cnpj: string }>;
}) {
  const { cnpj } = await params;

  let perfil: FornecedorPerfil;
  try {
    perfil = await fornecedorApi.perfil(cnpj);
  } catch {
    notFound();
  }

  const [porOrgao, porMunicipio, porCategoria, contratos] =
    await Promise.allSettled([
      fornecedorApi.porOrgao(cnpj, 10),
      fornecedorApi.porMunicipio(cnpj, 10),
      fornecedorApi.porCategoria(cnpj),
      fornecedorApi.contratos(cnpj, 10),
    ]);

  const orgaos =
    porOrgao.status === "fulfilled" ? porOrgao.value : [];
  const municipios =
    porMunicipio.status === "fulfilled" ? porMunicipio.value : [];
  const categorias =
    porCategoria.status === "fulfilled" ? porCategoria.value : [];
  const ctos =
    contratos.status === "fulfilled" ? contratos.value : [];

  const concentracaoOrgaoTopPct =
    orgaos.length > 0
      ? Number(orgaos[0].valor_total) / Number(perfil.valor_total)
      : 0;

  return (
    <article className="space-y-10 max-w-3xl">
      <header className="space-y-2">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <p className="text-xs uppercase tracking-wide text-muted">
          Fornecedor público · CNPJ <code>{perfil.fornecedor_cnpj}</code>
          {perfil.cnpj_mascarado && (
            <span className="text-attention"> · mascarado pelo TCE-PR</span>
          )}
        </p>
        <h1 className="text-3xl font-semibold tracking-tight leading-tight">
          {perfil.fornecedor_nome ?? "Fornecedor sem nome registrado"}
        </h1>
      </header>

      <section className="border border-attention/40 bg-attention/5 rounded-md p-4 text-sm space-y-2">
        <p className="font-medium text-attention">
          Como interpretar este perfil
        </p>
        <p className="text-muted leading-relaxed">
          Esta página apresenta dados públicos de contratos firmados entre
          este fornecedor e órgãos públicos brasileiros, extraídos de
          portais oficiais (TCE-PR, Compras.gov.br). A presença aqui{" "}
          <strong>não implica irregularidade</strong> — é apenas o
          registro de quanto e com quem este fornecedor contratou. Volume
          alto não é prova de nada por si só; é ponto de partida para
          investigação por jornalistas e órgãos de controle.
        </p>
        <p className="text-muted leading-relaxed">
          Se algum dado aqui está errado, reporte em{" "}
          <Link href="/correcoes">/correcoes</Link>. SLA: 48h.
        </p>
      </section>

      <section className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <Stat
          label="Contratos registrados"
          value={perfil.n_contratos_total.toLocaleString("pt-BR")}
        />
        <Stat label="Volume contratado" value={fmtBRL(perfil.valor_total)} />
        <Stat
          label="Órgãos contratantes"
          value={String(perfil.n_orgaos_distintos)}
          hint={
            concentracaoOrgaoTopPct > 0.5
              ? `${(concentracaoOrgaoTopPct * 100).toFixed(0)}% no maior`
              : undefined
          }
        />
        <Stat
          label="Municípios"
          value={String(perfil.n_municipios_distintos)}
        />
      </section>

      {(perfil.primeiro_contrato || perfil.ultimo_contrato) && (
        <section className="text-sm text-muted">
          Janela de contratos:{" "}
          {perfil.primeiro_contrato
            ? fmtDateBR(perfil.primeiro_contrato)
            : "—"}{" "}
          → {perfil.ultimo_contrato ? fmtDateBR(perfil.ultimo_contrato) : "—"}.
        </section>
      )}

      {orgaos.length > 0 && (
        <Block
          titulo="Distribuição por órgão contratante"
          legenda="Volume agregado por órgão. Concentração alta no maior órgão pode ser legítima (especialização) ou ponto de atenção — interpretação depende do contexto."
          linhas={orgaos}
          totalRef={Number(perfil.valor_total)}
        />
      )}

      {municipios.length > 0 && (
        <Block
          titulo="Distribuição por município"
          legenda={`${perfil.n_municipios_distintos} municípios distintos no total; lista exibe os 10 maiores por volume.`}
          linhas={municipios}
          totalRef={Number(perfil.valor_total)}
        />
      )}

      {categorias.length > 0 && (
        <Block
          titulo="Distribuição por categoria-piloto"
          legenda='Categorias mapeadas pelos clusters keyword (config/cluster_keywords.yaml). "Sem categoria mapeada" = contratos cujo objeto não casa com nenhum cluster atual; ainda visíveis no detalhe.'
          linhas={categorias}
          totalRef={Number(perfil.valor_total)}
        />
      )}

      {ctos.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl font-semibold">Top contratos por valor</h2>
          <ol className="space-y-2">
            {ctos.map((c) => (
              <ContratoRow key={c.contrato_id} c={c} />
            ))}
          </ol>
        </section>
      )}

      <footer className="text-sm text-muted border-t border-line pt-6 space-y-2">
        <p>
          Threshold mínimo de 5 contratos para gerar perfil público —
          fornecedores eventuais não aparecem aqui.{" "}
          <Link href="/manifesto">Por quê</Link>.
        </p>
        <p>
          Página excluída do indexamento de buscas (
          <code>noindex, nofollow</code>) na Fase 1, conforme política
          interna até revisão jurídica.
        </p>
      </footer>
    </article>
  );
}

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="border border-line rounded-md p-4">
      <div className="text-xs text-muted uppercase tracking-wide">{label}</div>
      <div className="text-xl font-mono font-semibold">{value}</div>
      {hint && <div className="text-xs text-muted mt-1">{hint}</div>}
    </div>
  );
}

function Block({
  titulo,
  legenda,
  linhas,
  totalRef,
}: {
  titulo: string;
  legenda: string;
  linhas: FornecedorAgregado[];
  totalRef: number;
}) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">{titulo}</h2>
      <p className="text-sm text-muted max-w-xl">{legenda}</p>
      <ol className="text-sm space-y-1 border border-line rounded-md p-4 bg-white">
        {linhas.map((l, i) => {
          const pct = totalRef > 0 ? Number(l.valor_total) / totalRef : 0;
          return (
            <li
              key={l.chave}
              className="flex items-baseline gap-3 border-b border-line/60 py-1.5"
            >
              <span className="w-6 text-right text-muted">{i + 1}.</span>
              <span className="flex-1 min-w-0 truncate">
                {l.nome ?? l.chave}
              </span>
              <span className="text-xs text-muted w-16 text-right">
                {l.n_contratos} c.
              </span>
              <span className="font-mono w-28 text-right">
                {fmtBRL(l.valor_total)}
              </span>
              <span className="text-xs text-muted w-12 text-right">
                {(pct * 100).toFixed(0)}%
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function ContratoRow({ c }: { c: FornecedorContrato }) {
  return (
    <li className="border border-line rounded-md p-3 bg-white text-sm space-y-1">
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <span className="font-medium">
          {c.municipio ? `${c.municipio} · ` : ""}
          {c.orgao_nome}
        </span>
        <span className="font-mono">{fmtBRL(c.valor_total)}</span>
      </div>
      <div className="text-muted text-xs">
        {c.contract_date && (
          <span>{fmtDateBR(c.contract_date)} · </span>
        )}
        contrato {c.contrato_id}
        {c.em_quarentena && (
          <span className="text-attention"> · sem cluster</span>
        )}
      </div>
      <p className="text-muted leading-relaxed">
        {c.descricao.length > 240
          ? c.descricao.slice(0, 240) + "…"
          : c.descricao}
      </p>
    </li>
  );
}

function fmtDateBR(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}
