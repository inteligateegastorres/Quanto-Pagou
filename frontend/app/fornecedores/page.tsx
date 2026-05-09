import Link from "next/link";
import type { Metadata } from "next";
import { fmtBRL } from "@/lib/api";
import {
  buscar,
  type FornecedorListItem,
} from "@/lib/tcepr";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Fornecedores · Quanto Pagou",
  description:
    "Pesquise pelo nome ou CNPJ do fornecedor (empresa que recebeu o pagamento) e abra seu perfil agregado.",
};

type SearchParams = {
  q?: string;
  min?: string;
};

export default async function FornecedoresPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const q = (params.q || "").trim();
  const minContratos = params.min ? Number(params.min) : 5;
  const minSafe = Number.isFinite(minContratos) && minContratos >= 1 ? minContratos : 5;

  let fornecedores: FornecedorListItem[] = [];
  let err: string | null = null;
  try {
    fornecedores = await buscar.fornecedores({
      search: q || undefined,
      min_contratos: minSafe,
      limit: 50,
    });
  } catch (e) {
    err = e instanceof Error ? e.message : "erro";
  }

  return (
    <div className="space-y-10 max-w-3xl">
      <header className="space-y-2">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <p className="text-xs uppercase tracking-wide text-ok font-medium">
          Fornecedor · empresa que recebeu o pagamento
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          Quem foi pago?
        </h1>
        <p className="text-muted leading-relaxed">
          Pesquise pelo <strong>nome</strong> ou <strong>CNPJ</strong> da
          empresa contratada. A busca casa por substring (parte do nome ou
          parte do CNPJ). Cada linha abre o perfil agregado do fornecedor —
          contratos, municípios em que opera, modalidades, evolução temporal.
        </p>
      </header>

      <form action="/fornecedores" method="get" className="flex gap-2 flex-wrap">
        <input
          name="q"
          defaultValue={q}
          placeholder='ex: "atlantica", "copel", CNPJ "00844138"...'
          className="flex-1 min-w-0 border border-line rounded-md px-3 py-2 text-sm bg-paper"
        />
        <input
          name="min"
          defaultValue={String(minSafe)}
          type="number"
          min={1}
          max={500}
          title="Mínimo de contratos"
          className="w-24 border border-line rounded-md px-2 py-2 text-sm bg-paper"
        />
        <button
          type="submit"
          className="border border-ink rounded-md px-4 py-2 text-sm no-underline hover:bg-ink hover:text-paper"
        >
          Buscar
        </button>
      </form>

      <p className="text-xs text-muted">
        {q
          ? `${fornecedores.length} fornecedor(es) para "${q}"`
          : `Top ${fornecedores.length} fornecedores por volume contratado`}
        {" · "}filtro: ≥ {minSafe} contrato(s){" "}
        {minSafe < 5 && (
          <span className="text-attention">
            (atenção: abaixo de 5 sai do guardrail §6.5 — perfis com poucos
            contratos não devem ser publicados como prova)
          </span>
        )}
      </p>

      {err && (
        <p className="text-sm text-attention">Falha ao consultar: {err}</p>
      )}

      <ol className="space-y-1">
        {fornecedores.map((f, i) => (
          <li
            key={f.fornecedor_cnpj}
            className="flex items-baseline gap-3 border-b border-line/60 py-2 text-sm"
          >
            <span className="w-6 text-right text-muted">{i + 1}.</span>
            <div className="flex-1 min-w-0">
              <Link
                href={`/fornecedor/${encodeURIComponent(f.fornecedor_cnpj)}`}
                className="font-medium no-underline hover:underline truncate block"
              >
                {f.fornecedor_nome ?? "—"}
              </Link>
              <div className="text-xs text-muted">
                CNPJ {f.fornecedor_cnpj}
                {f.n_municipios_distintos > 1 &&
                  ` · ${f.n_municipios_distintos} municípios`}
              </div>
            </div>
            <span className="text-xs text-muted w-16 text-right whitespace-nowrap">
              {f.n_contratos} c.
            </span>
            <Link
              href={`/contratos?fornecedor_cnpj=${encodeURIComponent(f.fornecedor_cnpj)}&fornecedor_nome=${encodeURIComponent(f.fornecedor_nome ?? "")}`}
              className="font-mono w-32 text-right whitespace-nowrap no-underline hover:underline"
            >
              {fmtBRL(f.valor_total)}
            </Link>
          </li>
        ))}
        {fornecedores.length === 0 && (
          <li className="text-sm text-muted py-3">
            Sem resultados. Tente outro termo, parte do CNPJ, ou diminua o
            mínimo de contratos.
          </li>
        )}
      </ol>

      <section className="border border-line rounded-md p-4 text-xs text-muted space-y-2">
        <p className="font-medium text-ink">O que esta página NÃO responde</p>
        <ul className="list-disc pl-5 space-y-1">
          <li>
            <strong>"Quem foi pago por entregar à UPA Centro":</strong> use{" "}
            <Link href="/instituicoes">/instituicoes</Link>. Aqui buscamos
            por nome do fornecedor; lá buscamos por instituição
            destinatária (que aparece no objeto do contrato).
          </li>
          <li>
            <strong>Comparação de preços entre fornecedores:</strong> use{" "}
            <Link href="/comparar">/comparar</Link> com um cluster de produto
            específico.
          </li>
          <li>
            <strong>Lista de contratos com filtros avançados:</strong> use{" "}
            <Link href="/contratos">/contratos</Link>.
          </li>
        </ul>
      </section>

      <section className="text-sm text-muted border-t border-line pt-6">
        <p>
          URL canônica do perfil: <code>/fornecedor/{"{cnpj}"}</code>.
          Guardrail §6.5: só publicamos perfis com ≥ 5 contratos no
          histórico — abaixo disso o agregado é estatisticamente frágil.
        </p>
      </section>
    </div>
  );
}
