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
  title: "Instituição destinatária · Quanto Pagou",
  description:
    "Pesquise pelo nome da instituição que recebeu o produto ou serviço (UPA, escola, hospital, posto de saúde, biblioteca, CRAS) e veja quem foi pago.",
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
      result = await instituicoes.search(q, 30);
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
        <p className="text-xs uppercase tracking-wide text-attention font-medium">
          Destinatário · termo no objeto do contrato
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          Quem entregou para esta instituição?
        </h1>
        <p className="text-muted leading-relaxed">
          Procure pelo nome da instituição que <strong>recebeu o produto ou
          serviço</strong> — UPA, escola, hospital, posto de saúde, CRAS,
          biblioteca, ginásio, etc. Mostramos os contratos cuja descrição
          menciona o termo, agrupados por <strong>quem foi pago</strong> e
          por <strong>município + órgão contratante</strong>.
        </p>
      </header>

      <form action="/instituicoes" method="get" className="flex gap-2 flex-wrap">
        <input
          name="q"
          defaultValue={q}
          placeholder='ex: "UPA Centro", "Hospital Municipal", "Escola Carlos Gomes", "CRAS"'
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
        <section className="border border-attention/40 bg-attention/5 rounded-md p-5 text-sm space-y-3">
          <p className="font-medium text-attention">
            Limites desta busca — leia antes de interpretar
          </p>
          <ul className="text-muted leading-relaxed list-disc pl-5 space-y-1">
            <li>
              <strong>Granularidade da fonte:</strong> o TCE-PR não tem o
              conceito "verba destinada a esta unidade". O dinheiro vai pro
              fornecedor (empresa contratada). Sua UPA aparece no contrato
              como <em>local de uso</em>, não como entidade que recebe
              pagamento.
            </li>
            <li>
              <strong>Cobertura é parcial:</strong> só capturamos contratos
              cuja descrição literalmente menciona o termo. Verbas que vão
              pra rede municipal de saúde, fundação que opera várias UPAs,
              terceirização "para todas as unidades" — nada disso aparece
              aqui.
            </li>
            <li>
              <strong>Não use como "verba real da unidade".</strong> Use
              como ponto de partida: "estas empresas foram contratadas para
              entregar coisas à UPA Centro". Para verba total de saúde do
              município, abra a página do município.
            </li>
            <li>
              <strong>Acentos importam.</strong> Digite o termo como aparece
              na fonte ("São", "FUNDAÇÃO" etc).
            </li>
          </ul>
          <p className="text-muted text-xs pt-2">
            Para buscar fornecedor por nome/CNPJ, use{" "}
            <Link href="/fornecedores">/fornecedores</Link>. Para drill-down
            com mais filtros, ver{" "}
            <Link href="/contratos">/contratos</Link>.
          </p>
        </section>
      )}

      {err && (
        <p className="text-sm text-attention">Falha ao consultar: {err}</p>
      )}

      {result && (
        <>
          <section className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
            <Stat
              label="Contratos com o termo"
              value={result.total_objeto_contratos.toLocaleString("pt-BR")}
              hint='objeto contém o termo'
            />
            <Stat
              label="Volume agregado"
              value={fmtBRLCompact(result.valor_total_objeto)}
              hint={fmtBRL(result.valor_total_objeto)}
            />
            <Stat
              label="Fornecedores únicos"
              value={result.total_fornecedores_no_objeto.toLocaleString("pt-BR")}
              hint="quem foi pago"
              tone="attention"
            />
          </section>

          <section className="border border-attention/40 bg-attention/5 rounded-md p-3 text-xs text-muted">
            <strong className="text-attention">Atenção:</strong> os números
            acima somam contratos cuja descrição menciona "{q}". Não é
            equivalente a "verba total da instituição" — outros contratos
            podem servir a essa unidade sem mencionar o nome dela.
          </section>

          {result.fornecedores_no_objeto.length > 0 && (
            <section>
              <h2 className="text-xl font-semibold mb-2">
                Quem foi pago em contratos com "{q}" no objeto
              </h2>
              <p className="text-xs text-muted mb-3">
                Soma por fornecedor. Resposta a "qual empresa recebeu
                pagamento por entregar serviço/produto a esta instituição".
                Clique no valor para ver os contratos.
              </p>
              <ol className="space-y-1">
                {result.fornecedores_no_objeto.map((f, i) => {
                  const drill = `/contratos?q=${encodeURIComponent(q)}&fornecedor_cnpj=${encodeURIComponent(f.fornecedor_cnpj)}&fornecedor_nome=${encodeURIComponent(f.fornecedor_nome ?? "")}`;
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

          {result.objetos.length > 0 && (
            <section>
              <h2 className="text-xl font-semibold mb-2">
                Por município e órgão contratante
              </h2>
              <p className="text-xs text-muted mb-3">
                Quem comprou. Soma de contratos por (município, órgão). Útil
                pra ver quais cidades têm mais contratos mencionando o termo.
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

          {result.objetos.length === 0 &&
            result.fornecedores_no_objeto.length === 0 && (
              <p className="text-sm text-muted py-6">
                Sem contratos com "{q}" no objeto. Tente outro termo,
                variantes (ex: com/sem acento), ou busque por fornecedor em{" "}
                <Link href="/fornecedores">/fornecedores</Link>.
              </p>
            )}
        </>
      )}

      <section className="text-sm text-muted border-t border-line pt-6">
        <p>
          Para pesquisa por nome/CNPJ de empresa, use{" "}
          <Link href="/fornecedores">/fornecedores</Link>. Para drill-down
          com mais filtros (data, modalidade, ordenação) use{" "}
          <Link href="/contratos">/contratos</Link>.
        </p>
      </section>
    </div>
  );
}
