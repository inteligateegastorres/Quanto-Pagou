import Link from "next/link";
import type { Metadata } from "next";
import { fmtBRL } from "@/lib/api";
import {
  buscar,
  type FornecedorListItem,
  type MunicipioListItem,
} from "@/lib/tcepr";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Buscar município ou fornecedor · Quanto Pagou",
  description:
    "Procure pelo nome do município paranaense ou pelo nome/CNPJ do fornecedor para abrir o perfil correspondente.",
};

type SearchParams = {
  m?: string; // search municipio
  f?: string; // search fornecedor
};

export default async function BuscarPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const qMun = (params.m || "").trim();
  const qForn = (params.f || "").trim();

  const [munR, fornR] = await Promise.allSettled([
    buscar.municipios({ search: qMun || undefined, limit: 30 }),
    buscar.fornecedores({ search: qForn || undefined, min_contratos: 5, limit: 30 }),
  ]);

  const municipios = munR.status === "fulfilled" ? munR.value : [];
  const fornecedores = fornR.status === "fulfilled" ? fornR.value : [];

  return (
    <div className="space-y-12 max-w-3xl">
      <header className="space-y-2">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <h1 className="text-3xl font-semibold tracking-tight">Buscar</h1>
        <p className="text-muted">
          Procure por <strong>município paranaense</strong> ou{" "}
          <strong>fornecedor</strong> (nome ou CNPJ). Cliques abrem o perfil
          correspondente. Fornecedores precisam ter pelo menos 5 contratos
          para aparecer (guardrail do plano §6.5).
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Municípios PR</h2>
        <form action="/buscar" method="get" className="flex gap-2 flex-wrap">
          <input
            name="m"
            defaultValue={qMun}
            placeholder="ex: curitiba, ponta grossa, foz..."
            className="flex-1 min-w-0 border border-line rounded-md px-3 py-2 text-sm bg-paper"
          />
          {qForn && <input type="hidden" name="f" value={qForn} />}
          <button
            type="submit"
            className="border border-ink rounded-md px-4 py-2 text-sm no-underline hover:bg-ink hover:text-paper"
          >
            Buscar
          </button>
        </form>
        <p className="text-xs text-muted">
          {qMun
            ? `${municipios.length} municípios para "${qMun}"`
            : `Top ${municipios.length} municípios por volume de contratos`}
        </p>
        <ol className="space-y-1">
          {municipios.map((m, i) => (
            <MunicipioRow key={m.cd_tce} pos={i + 1} m={m} />
          ))}
          {municipios.length === 0 && (
            <li className="text-sm text-muted py-3">
              Sem resultados. Tente outro termo.
            </li>
          )}
        </ol>
      </section>

      <section className="space-y-3 border-t border-line pt-8">
        <h2 className="text-xl font-semibold">Fornecedores</h2>
        <form action="/buscar" method="get" className="flex gap-2 flex-wrap">
          <input
            name="f"
            defaultValue={qForn}
            placeholder="ex: atlantica, copel, CNPJ 00844138..."
            className="flex-1 min-w-0 border border-line rounded-md px-3 py-2 text-sm bg-paper"
          />
          {qMun && <input type="hidden" name="m" value={qMun} />}
          <button
            type="submit"
            className="border border-ink rounded-md px-4 py-2 text-sm no-underline hover:bg-ink hover:text-paper"
          >
            Buscar
          </button>
        </form>
        <p className="text-xs text-muted">
          {qForn
            ? `${fornecedores.length} fornecedores para "${qForn}"`
            : `Top ${fornecedores.length} fornecedores por volume contratado`}
          {" · "}só fornecedores com ≥ 5 contratos
        </p>
        <ol className="space-y-1">
          {fornecedores.map((f, i) => (
            <FornecedorRow key={f.fornecedor_cnpj} pos={i + 1} f={f} />
          ))}
          {fornecedores.length === 0 && (
            <li className="text-sm text-muted py-3">
              Sem resultados (ou nenhum fornecedor com ≥ 5 contratos casa o
              termo).
            </li>
          )}
        </ol>
      </section>

      <section className="text-sm text-muted border-t border-line pt-6">
        <p>
          A lista de fornecedores acima também filtra por CNPJ (substring).
          Para abrir um perfil específico sem buscar, a URL canônica é{" "}
          <code>/fornecedor/{"{cnpj}"}</code>; para um município,{" "}
          <code>/municipio/{"{cd_tce}"}</code>.
        </p>
      </section>
    </div>
  );
}

function MunicipioRow({ pos, m }: { pos: number; m: MunicipioListItem }) {
  return (
    <li className="flex items-baseline gap-3 border-b border-line/60 py-2 text-sm">
      <span className="w-6 text-right text-muted">{pos}.</span>
      <Link
        href={`/municipio/${m.cd_tce}`}
        className="flex-1 min-w-0 truncate font-medium no-underline hover:underline"
      >
        {m.nome}
      </Link>
      <span className="text-xs text-muted whitespace-nowrap">
        {m.porte.replace("municipio_pr_", "")}
        {!m.catalogado && " · não catalogado"}
      </span>
      <span className="text-xs text-muted w-20 text-right">
        {m.n_contratos.toLocaleString("pt-BR")} c.
      </span>
      <span className="font-mono w-32 text-right whitespace-nowrap">
        {fmtBRL(m.valor_total)}
      </span>
    </li>
  );
}

function FornecedorRow({ pos, f }: { pos: number; f: FornecedorListItem }) {
  return (
    <li className="flex items-baseline gap-3 border-b border-line/60 py-2 text-sm">
      <span className="w-6 text-right text-muted">{pos}.</span>
      <div className="flex-1 min-w-0">
        <Link
          href={`/fornecedor/${encodeURIComponent(f.fornecedor_cnpj)}`}
          className="font-medium no-underline hover:underline truncate block"
        >
          {f.fornecedor_nome ?? "—"}
        </Link>
        <div className="text-xs text-muted">
          CNPJ {f.fornecedor_cnpj}
          {f.n_municipios_distintos > 1 && ` · ${f.n_municipios_distintos} municípios`}
        </div>
      </div>
      <span className="text-xs text-muted w-16 text-right whitespace-nowrap">
        {f.n_contratos} c.
      </span>
      <span className="font-mono w-32 text-right whitespace-nowrap">
        {fmtBRL(f.valor_total)}
      </span>
    </li>
  );
}
