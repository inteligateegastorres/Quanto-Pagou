import Link from "next/link";
import type { Metadata } from "next";
import { fmtBRL, fmtBRLCompact } from "@/lib/api";
import { Stat } from "@/lib/Stat";
import { dispensas, type DispensaTopFornecedor } from "@/lib/tcepr";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Top fornecedores em dispensas — Paraná · Quanto Pagou",
  description:
    "Listagem auditável de fornecedores com mais contratos por dispensa de licitação no Paraná (TCE-PR). Dispensa não implica irregularidade — Lei 14.133/2021 prevê casos legítimos.",
  robots: { index: false, follow: false }, // mesmo guardrail das paginas de fornecedor §6.5
};

type SearchParams = { incluir_pf?: string };

export default async function DispensasPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const incluirPf = params.incluir_pf === "1";

  let lista: DispensaTopFornecedor[] = [];
  let err: string | null = null;
  try {
    lista = await dispensas.topFornecedores({
      limit: 50,
      min_contratos: 2,
      incluir_cpf_mascarado: incluirPf,
    });
  } catch (e) {
    err = e instanceof Error ? e.message : "erro";
  }

  const totalContratos = lista.reduce((s, f) => s + f.n_dispensas, 0);
  const totalValor = lista.reduce(
    (s, f) => s + Number(f.valor_total_dispensas),
    0,
  );
  const top3Pct =
    totalValor > 0
      ? lista
          .slice(0, 3)
          .reduce((s, f) => s + Number(f.valor_total_dispensas), 0) /
        totalValor
      : 0;

  return (
    <div className="space-y-10 max-w-3xl">
      <header className="space-y-2">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <p className="text-xs uppercase tracking-wide text-attention font-medium">
          Catálogo · TCE-PR · modalidade dispensa
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          Quem mais contrata por dispensa de licitação no Paraná
        </h1>
        <p className="text-muted leading-relaxed">
          Fornecedores ordenados pelo valor acumulado em contratos cuja
          modalidade resolvida é <code>dispensa</code>. Dados extraídos
          do TCE-PR PIT.
        </p>
      </header>

      <section className="border border-attention/40 bg-attention/5 rounded-md p-4 text-sm space-y-2">
        <p className="font-medium text-attention">
          Como interpretar — guardrails legais
        </p>
        <ul className="text-muted leading-relaxed list-disc pl-5 space-y-1">
          <li>
            <strong>Dispensa não implica irregularidade.</strong> A Lei
            14.133/2021 prevê dispensa de licitação para casos específicos:
            emergência, valor abaixo do limite legal, fornecedor exclusivo,
            obras de pequena monta, calamidade, entre outros. Presença alta
            aqui é ponto de partida para investigação, não prova de nada.
          </li>
          <li>
            <strong>Linguagem factual.</strong> A lista não é "ranking dos
            piores". É a soma de contratos de uma modalidade específica
            durante a janela coberta. Volume alto pode ser legítimo (ex:
            empresa de manutenção contratada repetidamente em emergências
            elétricas) ou ponto de atenção — depende do contexto.
          </li>
          <li>
            <strong>Cobertura parcial.</strong> Modalidade só foi resolvida
            para 65% dos contratos do banco (via JOIN
            Licitacao + LicitacaoXContrato no adapter). Os 35% restantes
            podem incluir dispensas adicionais que não aparecem aqui.
          </li>
          <li>
            <strong>CPFs mascarados</strong> pelo TCE-PR (
            <code>***.123.***-**</code>) são pessoas físicas distintas que
            colidem no mesmo CNPJ-mascarado. Por padrão estão ocultos para
            evitar agregar contratos de pessoas diferentes. Para incluir,{" "}
            {incluirPf ? (
              <Link href="/dispensas">recolher</Link>
            ) : (
              <Link href="/dispensas?incluir_pf=1">expandir</Link>
            )}{" "}
            (resultados ficam menos confiáveis).
          </li>
        </ul>
      </section>

      <section className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <Stat
          label="Fornecedores listados"
          value={String(lista.length)}
          hint="≥ 2 dispensas"
        />
        <Stat
          label="Volume agregado"
          value={fmtBRLCompact(totalValor)}
          hint={fmtBRL(totalValor.toFixed(2))}
        />
        <Stat
          label="Contratos cobertos"
          value={totalContratos.toLocaleString("pt-BR")}
        />
        <Stat
          label="Concentração top 3"
          value={`${(top3Pct * 100).toFixed(0)}%`}
          hint="do volume desta página"
        />
      </section>

      {err && (
        <p className="text-sm text-attention">Falha ao consultar: {err}</p>
      )}

      <section className="space-y-2">
        <h2 className="text-xl font-semibold">Lista</h2>
        <p className="text-xs text-muted">
          Cada nome é clicável (perfil tem threshold ≥ 5 contratos). Cor
          atenção quando o fornecedor opera em só 1 município (concentração
          local) — sinal mais forte que volume sozinho.
        </p>
        <ol className="space-y-1">
          {lista.map((f, i) => (
            <Linha key={`${f.fornecedor_cnpj}-${f.fornecedor_nome}`} pos={i + 1} f={f} />
          ))}
          {lista.length === 0 && !err && (
            <li className="text-sm text-muted py-3">
              Sem resultados (banco pode estar vazio ou modalidade não
              resolvida ainda).
            </li>
          )}
        </ol>
      </section>

      <section className="text-sm text-muted border-t border-line pt-6 space-y-2">
        <p>
          <strong>Como verificamos.</strong> Modalidade vem de{" "}
          <code>Licitacao.xml</code> + <code>LicitacaoXContrato.xml</code>{" "}
          do ZIP semanal do TCE-PR (campo <code>dsModalidadeLicitacao</code>{" "}
          normalizado para snake_case). Adapter em{" "}
          <code>src/ingest/tce_pr.py</code> faz o JOIN em memória.
        </p>
        <p>
          Encontrou erro?{" "}
          <Link href="/correcoes">Reportar</Link>. Página excluída do
          indexamento de buscas (<code>noindex,nofollow</code>) na Fase 1
          conforme política interna até revisão jurídica.
        </p>
      </section>
    </div>
  );
}

function Linha({ pos, f }: { pos: number; f: DispensaTopFornecedor }) {
  const podeLinkar = f.n_dispensas >= 5 && !f.cnpj_mascarado;
  const cnpjEnc = encodeURIComponent(f.fornecedor_cnpj);
  const concentrado = f.n_municipios === 1; // 1 só município

  return (
    <li className="flex items-baseline gap-3 border-b border-line/60 py-2 text-sm">
      <span className="w-6 text-right text-muted">{pos}.</span>
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">
          {podeLinkar ? (
            <Link
              href={`/fornecedor/${cnpjEnc}`}
              className="no-underline hover:underline"
            >
              {f.fornecedor_nome ?? "—"}
            </Link>
          ) : (
            <span>{f.fornecedor_nome ?? "—"}</span>
          )}
          {f.cnpj_mascarado && (
            <span className="ml-2 text-xs text-attention">(CPF mascarado)</span>
          )}
        </div>
        <div className="text-xs text-muted">
          CNPJ {f.fornecedor_cnpj} · {f.n_dispensas} dispensas
          {" · "}
          <span className={concentrado ? "text-attention" : ""}>
            {f.n_municipios} município{f.n_municipios === 1 ? "" : "s"}
          </span>
          {" · "}
          {f.n_orgaos} órgão{f.n_orgaos === 1 ? "" : "s"}
        </div>
      </div>
      <span className="font-mono text-right whitespace-nowrap">
        {fmtBRLCompact(f.valor_total_dispensas)}
      </span>
    </li>
  );
}
