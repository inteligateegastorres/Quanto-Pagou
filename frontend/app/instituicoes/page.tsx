import Link from "next/link";
import type { Metadata } from "next";
import { fmtBRL, fmtBRLCompact } from "@/lib/api";
import { Stat } from "@/lib/Stat";
import {
  instituicoes,
  type InstituicoesSearch,
} from "@/lib/tcepr";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Buscar instituição · Quanto Pagou",
  description:
    "Busca por nome de fornecedor, órgão público ou termo no objeto do contrato (UPA, escola, hospital, etc.) — três contextos numa pesquisa só.",
};

type SearchParams = { q?: string };

export default async function InstituicoesPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const q = (params.q || "").trim();

  let result: InstituicoesSearch | null = null;
  let err: string | null = null;
  if (q.length >= 2) {
    try {
      result = await instituicoes.search(q, 20);
    } catch (e) {
      err = e instanceof Error ? e.message : "erro";
    }
  }

  return (
    <div className="space-y-10 max-w-3xl">
      <header className="space-y-2">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <h1 className="text-3xl font-semibold tracking-tight">
          Buscar instituição
        </h1>
        <p className="text-muted leading-relaxed">
          Pesquise por nome em <strong>três contextos</strong> ao mesmo
          tempo: <strong>fornecedor</strong> (quem recebeu o pagamento),{" "}
          <strong>órgão público</strong> (quem contratou) e{" "}
          <strong>objeto do contrato</strong> (UPA, escola, hospital, posto
          de saúde, biblioteca, etc.). O mesmo termo cobre os três.
        </p>
      </header>

      <form action="/instituicoes" method="get" className="flex gap-2 flex-wrap">
        <input
          name="q"
          defaultValue={q}
          placeholder='ex: "Atlantica" (fornecedor), "FEAS" (órgão), "UPA Centro" (objeto), "Carlos Gomes" (escola)'
          className="flex-1 min-w-0 border border-line rounded-md px-3 py-2 text-sm bg-paper"
          required
          minLength={2}
        />
        <button
          type="submit"
          className="border border-ink rounded-md px-4 py-2 text-sm no-underline hover:bg-ink hover:text-paper"
        >
          Buscar
        </button>
      </form>

      {q.length < 2 && (
        <section className="border border-line rounded-md p-5 bg-white text-sm space-y-2">
          <p className="font-medium">Como funciona</p>
          <ul className="text-muted leading-relaxed list-disc pl-5 space-y-1">
            <li>
              Digite no mínimo 2 caracteres. Substring case-insensitive nos
              três campos.
            </li>
            <li>
              <strong>Fornecedor</strong> — bate em <code>fornecedor_nome</code>.
              Cada resultado linka para o perfil do fornecedor (se ≥ 5 contratos).
            </li>
            <li>
              <strong>Órgão</strong> — bate em <code>orgao_nome</code>. Cada
              resultado linka para o município do órgão.
            </li>
            <li>
              <strong>Objeto</strong> — bate em <code>descricao</code>. Cobre
              menções a UPA, escola, hospital, CMEI, biblioteca, posto de
              saúde — qualquer termo que apareça no objeto. Resultado
              agregado por município + órgão.
            </li>
            <li>
              <strong>Acentos importam</strong> — digite o termo como aparece
              na fonte ("São", "FUNDAÇÃO" etc).
            </li>
            <li>
              Para drill-down em qualquer linha, clique no valor — abre{" "}
              <Link href="/contratos">/contratos</Link> com o filtro aplicado.
            </li>
          </ul>
          <p className="text-muted text-xs pt-2">
            Para busca direta na lista de contratos com mais filtros (data,
            modalidade, etc.), ver{" "}
            <Link href="/contratos">/contratos</Link>.
          </p>
        </section>
      )}

      {err && (
        <p className="text-sm text-attention">Falha ao consultar: {err}</p>
      )}

      {result && (
        <>
          <section className="grid grid-cols-3 gap-3 text-sm">
            <Stat
              label="Fornecedores"
              value={result.total_fornecedores.toLocaleString("pt-BR")}
              hint={`top ${result.fornecedores.length} abaixo`}
            />
            <Stat
              label="Órgãos"
              value={result.total_orgaos.toLocaleString("pt-BR")}
              hint={`top ${result.orgaos.length} abaixo`}
            />
            <Stat
              label="Contratos no objeto"
              value={result.total_objeto_contratos.toLocaleString("pt-BR")}
              hint={fmtBRLCompact(result.valor_total_objeto)}
            />
          </section>

          {result.fornecedores.length > 0 && (
            <section>
              <h2 className="text-xl font-semibold mb-2">
                Fornecedores ({result.total_fornecedores.toLocaleString("pt-BR")})
              </h2>
              <p className="text-xs text-muted mb-3">
                Quem recebeu pagamentos cujo nome contém "{q}". Clique no
                valor para ver os contratos.
              </p>
              <ol className="space-y-1">
                {result.fornecedores.map((f, i) => {
                  const drill = `/contratos?fornecedor_cnpj=${encodeURIComponent(f.fornecedor_cnpj)}&fornecedor_nome=${encodeURIComponent(f.fornecedor_nome ?? "")}`;
                  return (
                    <li
                      key={f.fornecedor_cnpj}
                      className="flex items-baseline gap-3 border-b border-line/60 py-1.5 text-sm"
                    >
                      <span className="w-6 text-right text-muted">{i + 1}.</span>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium truncate">
                          {f.n_contratos >= 5 ? (
                            <Link
                              href={`/fornecedor/${encodeURIComponent(f.fornecedor_cnpj)}`}
                              className="no-underline hover:underline"
                            >
                              {f.fornecedor_nome ?? "—"}
                            </Link>
                          ) : (
                            (f.fornecedor_nome ?? "—")
                          )}
                        </div>
                        <div className="text-xs text-muted">
                          CNPJ {f.fornecedor_cnpj}
                          {f.n_municipios > 1 && ` · ${f.n_municipios} municípios`}
                        </div>
                      </div>
                      <span className="text-xs text-muted whitespace-nowrap">
                        {f.n_contratos} c.
                      </span>
                      <Link
                        href={drill}
                        className="font-mono text-right whitespace-nowrap no-underline hover:underline"
                      >
                        {fmtBRL(f.valor_total)}
                      </Link>
                    </li>
                  );
                })}
              </ol>
            </section>
          )}

          {result.orgaos.length > 0 && (
            <section>
              <h2 className="text-xl font-semibold mb-2">
                Órgãos contratantes ({result.total_orgaos.toLocaleString("pt-BR")})
              </h2>
              <p className="text-xs text-muted mb-3">
                Órgãos cujo nome contém "{q}". Por município. Clique no
                valor para ver os contratos.
              </p>
              <ol className="space-y-1">
                {result.orgaos.map((o, i) => {
                  const drill = `/contratos?orgao_codigo=${encodeURIComponent(o.orgao_codigo)}&orgao_nome=${encodeURIComponent(o.orgao_nome)}${o.cd_tce ? `&cd_tce=${o.cd_tce}` : ""}${o.municipio ? `&municipio_nome=${encodeURIComponent(o.municipio)}` : ""}`;
                  return (
                    <li
                      key={`${o.orgao_codigo}-${o.cd_tce}`}
                      className="flex items-baseline gap-3 border-b border-line/60 py-1.5 text-sm"
                    >
                      <span className="w-6 text-right text-muted">{i + 1}.</span>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium truncate">
                          {o.orgao_nome}
                        </div>
                        <div className="text-xs text-muted">
                          {o.cd_tce ? (
                            <Link href={`/municipio/${o.cd_tce}`} className="no-underline hover:underline">
                              {o.municipio ?? `cd_tce ${o.cd_tce}`}
                            </Link>
                          ) : (
                            (o.municipio ?? "—")
                          )}
                          {" · "}código {o.orgao_codigo}
                        </div>
                      </div>
                      <span className="text-xs text-muted whitespace-nowrap">
                        {o.n_contratos} c.
                      </span>
                      <Link
                        href={drill}
                        className="font-mono text-right whitespace-nowrap no-underline hover:underline"
                      >
                        {fmtBRL(o.valor_total)}
                      </Link>
                    </li>
                  );
                })}
              </ol>
            </section>
          )}

          {result.objetos.length > 0 && (
            <section>
              <h2 className="text-xl font-semibold mb-2">
                Menções no objeto do contrato ({result.total_objeto_contratos.toLocaleString("pt-BR")})
              </h2>
              <p className="text-xs text-muted mb-3">
                Contratos cuja descrição contém "{q}", agrupados por
                município + órgão. Útil pra encontrar UPAs, escolas, postos
                de saúde, etc. Clique no valor para ver os contratos.
              </p>
              <ol className="space-y-1">
                {result.objetos.map((o, i) => {
                  const drill = `/contratos?q=${encodeURIComponent(q)}&orgao_codigo=${encodeURIComponent(o.orgao_codigo)}&orgao_nome=${encodeURIComponent(o.orgao_nome)}${o.cd_tce ? `&cd_tce=${o.cd_tce}` : ""}${o.municipio ? `&municipio_nome=${encodeURIComponent(o.municipio)}` : ""}`;
                  return (
                    <li
                      key={`${o.orgao_codigo}-${o.cd_tce}`}
                      className="flex items-baseline gap-3 border-b border-line/60 py-1.5 text-sm"
                    >
                      <span className="w-6 text-right text-muted">{i + 1}.</span>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium truncate">
                          {o.cd_tce ? (
                            <Link href={`/municipio/${o.cd_tce}`} className="no-underline hover:underline">
                              {o.municipio ?? "—"}
                            </Link>
                          ) : (
                            (o.municipio ?? "—")
                          )}
                        </div>
                        <div className="text-xs text-muted truncate">
                          {o.orgao_nome}
                        </div>
                      </div>
                      <span className="text-xs text-muted whitespace-nowrap">
                        {o.n_contratos} c.
                      </span>
                      <Link
                        href={drill}
                        className="font-mono text-right whitespace-nowrap no-underline hover:underline"
                      >
                        {fmtBRL(o.valor_total)}
                      </Link>
                    </li>
                  );
                })}
              </ol>
            </section>
          )}

          {result.fornecedores.length === 0 &&
            result.orgaos.length === 0 &&
            result.objetos.length === 0 && (
              <p className="text-sm text-muted py-6">
                Sem resultados para "{q}" em nenhum dos 3 contextos. Tente
                outro termo, ou variantes (ex: com/sem acento).
              </p>
            )}
        </>
      )}

      <section className="text-sm text-muted border-t border-line pt-6">
        <p>
          Página voltada para descoberta. Para drill-down com mais filtros
          (data, modalidade, ordenação), use{" "}
          <Link href="/contratos">/contratos</Link>. Para perfil completo de
          fornecedor (≥ 5 contratos), abra{" "}
          <Link href="/buscar">/buscar</Link>.
        </p>
      </section>
    </div>
  );
}
