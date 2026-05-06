import Link from "next/link";
import type { Metadata } from "next";
import { qd, fmtDate, type Gazette } from "@/lib/qd";

export const dynamic = "force-dynamic";

const CURITIBA_TERRITORY_ID = "4106902";

export const metadata: Metadata = {
  title: "Curitiba — diários oficiais e busca textual · Quanto Pagou",
  description:
    "Busque atos oficiais publicados pela Prefeitura de Curitiba desde 2017. Texto extraído de PDF, link para a fonte primária. Comparação de preços virá quando o TCE-PR autorizar nosso acesso.",
};

type SearchParams = { q?: string; since?: string };

export default async function CuritibaPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const query = (params.q || "").trim();
  const since =
    params.since ||
    new Date(Date.now() - 90 * 24 * 60 * 60 * 1000)
      .toISOString()
      .slice(0, 10); // últimos 90 dias por padrão

  // 3 fetches em paralelo: (1) busca filtrada da pagina,
  // (2) total absoluto + diario mais recente, (3) diario mais antigo (range).
  const [resultR, totalR, oldestR] = await Promise.allSettled([
    qd.gazettes(CURITIBA_TERRITORY_ID, {
      since,
      size: 15,
      ...(query ? { querystring: query } : {}),
    }),
    qd.gazettes(CURITIBA_TERRITORY_ID, { size: 1 }),
    qd.gazettesAscending(CURITIBA_TERRITORY_ID),
  ]);

  const result =
    resultR.status === "fulfilled" ? resultR.value : null;
  const error =
    resultR.status === "rejected"
      ? resultR.reason instanceof Error
        ? resultR.reason.message
        : "erro desconhecido"
      : null;
  const totalAbs =
    totalR.status === "fulfilled" ? totalR.value.total_gazettes : 0;
  const primeiroDate =
    oldestR.status === "fulfilled" && oldestR.value.gazettes[0]
      ? oldestR.value.gazettes[0].date
      : null;
  const cobertura =
    totalAbs > 0 || primeiroDate
      ? { total: totalAbs, primeiro: primeiroDate }
      : null;

  return (
    <div className="space-y-10 max-w-3xl">
      <header className="space-y-3">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <p className="text-xs uppercase tracking-wide text-attention font-medium">
          Curitiba · PR · território IBGE 4106902
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          Diários oficiais e busca textual
        </h1>
        <p className="text-muted">
          Atos oficiais publicados pela Prefeitura de Curitiba desde
          {cobertura?.primeiro ? ` ${fmtDate(cobertura.primeiro)}` : " 2017"}, indexados
          pelo{" "}
          <a
            href="https://queridodiario.ok.org.br/"
            target="_blank"
            rel="noreferrer"
          >
            Querido Diário
          </a>{" "}
          (OKBR). Cada resultado leva ao PDF original. Use a busca para
          localizar contratos, licitações, nomes de fornecedores ou tópicos
          específicos.
        </p>
      </header>

      <section className="border border-attention/40 bg-attention/5 rounded-md p-4 text-sm">
        <p className="font-medium text-attention mb-1">
          Por que esta página não compara preços ainda
        </p>
        <p className="text-muted leading-relaxed">
          Para comparar preço-por-item entre Curitiba e cidades pares,
          precisamos extrair contratos item-a-item de forma estruturada. O
          Querido Diário entrega o texto cru dos PDFs, mas a extração de
          contratos exige acesso ao TCE-PR (em fila de credenciamento) ou
          um resolver via LLM (Fase 3+ do nosso plano). Enquanto isso, esta
          página oferece busca textual, fonte primária e auditoria visível —
          o ranking comparativo entra assim que uma das duas condições for
          atendida. Ver{" "}
          <Link href="/manifesto">manifesto</Link>.
        </p>
      </section>

      <section className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
        <Stat
          label="Diários indexados"
          value={cobertura ? cobertura.total.toLocaleString("pt-BR") : "—"}
        />
        <Stat
          label="Cobertura desde"
          value={cobertura?.primeiro ? fmtDate(cobertura.primeiro) : "—"}
        />
        <Stat
          label="Janela exibida"
          value={`desde ${fmtDate(since)}`}
          hint="default: últimos 90 dias"
        />
      </section>

      <section className="border border-line rounded-md p-5 bg-white space-y-3">
        <h2 className="text-base font-semibold">Buscar nos diários</h2>
        <form className="flex gap-2 flex-wrap" action="/curitiba" method="get">
          <input
            name="q"
            defaultValue={query}
            placeholder='ex: "merenda escolar", "iluminação pública", CNPJ...'
            className="flex-1 min-w-0 border border-line rounded-md px-3 py-2 text-sm bg-paper"
          />
          <input
            type="date"
            name="since"
            defaultValue={since}
            className="border border-line rounded-md px-3 py-2 text-sm bg-paper"
          />
          <button
            type="submit"
            className="border border-ink rounded-md px-4 py-2 text-sm no-underline hover:bg-ink hover:text-paper"
          >
            Buscar
          </button>
        </form>
        <p className="text-xs text-muted">
          A busca é textual sobre o conteúdo extraído dos PDFs. Termos com
          aspas funcionam como frase exata. Datas aceitam o formato do
          calendário do navegador.
        </p>
      </section>

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold">
            {query ? `Resultados para "${query}"` : "Diários mais recentes"}
          </h2>
          {result && (
            <span className="text-xs text-muted">
              {result.total_gazettes.toLocaleString("pt-BR")} no total ·
              exibindo {result.gazettes.length}
            </span>
          )}
        </div>

        {error && (
          <p className="text-sm text-attention">
            Falha ao consultar Querido Diário ({error}). Tente recarregar.
          </p>
        )}

        {result && result.gazettes.length === 0 && (
          <p className="text-sm text-muted">
            Sem resultados nessa janela. Tente ampliar a janela ou outro
            termo.
          </p>
        )}

        <ol className="space-y-3">
          {(result?.gazettes ?? []).map((g) => (
            <GazetteRow key={`${g.date}-${g.edition}-${g.url}`} gazette={g} />
          ))}
        </ol>
      </section>

      <section className="text-sm text-muted border-t border-line pt-6 space-y-2">
        <p>
          <strong>Fonte:</strong>{" "}
          <a
            href="https://queridodiario.ok.org.br/"
            target="_blank"
            rel="noreferrer"
          >
            Querido Diário
          </a>{" "}
          — projeto da Open Knowledge Brasil (OKBR), MIT, dados sob CC-BY.
          Esta página consome a API pública sem cache local; quaisquer
          imprecisões na extração do PDF aparecem no texto e devem ser
          atribuídas ao processo upstream — mas você pode reportar via{" "}
          <Link href="/correcoes">correções</Link>.
        </p>
        <p>
          O Querido Diário cobre os <em>diários oficiais</em>, que contêm
          contratos firmados mas misturados a inúmeros outros atos
          (legislativos, RH, normativos). Não é o mesmo que ter os contratos
          estruturados — é o material bruto.
        </p>
      </section>
    </div>
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

function GazetteRow({ gazette }: { gazette: Gazette }) {
  return (
    <li className="border border-line rounded-md p-4 bg-white space-y-2">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div className="text-sm">
          <strong>{fmtDate(gazette.date)}</strong>
          {gazette.edition && (
            <span className="text-muted"> · edição {gazette.edition}</span>
          )}
          {gazette.is_extra_edition && (
            <span className="text-attention"> · extra</span>
          )}
        </div>
        <a
          href={gazette.url}
          target="_blank"
          rel="noreferrer"
          className="text-xs"
        >
          PDF original →
        </a>
      </div>
      {gazette.excerpts && gazette.excerpts.length > 0 && (
        <div className="text-sm leading-relaxed text-muted space-y-1">
          {gazette.excerpts.slice(0, 2).map((excerpt, i) => (
            <p key={i} className="border-l-2 border-attention/30 pl-3">
              {excerpt.length > 320
                ? excerpt.slice(0, 320) + "…"
                : excerpt}
            </p>
          ))}
        </div>
      )}
      {gazette.txt_url && (
        <a
          href={gazette.txt_url}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-muted"
        >
          texto extraído (TXT) →
        </a>
      )}
    </li>
  );
}
