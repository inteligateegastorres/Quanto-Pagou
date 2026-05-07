import Link from "next/link";
import type { Metadata } from "next";
import { fmtBRL } from "@/lib/api";
import { tcepr, buscar, type RankingMunicipio } from "@/lib/tcepr";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Comparar municípios · Quanto Pagou",
  description:
    "Compare lado a lado o gasto público de municípios paranaenses para uma mesma categoria-piloto (merenda escolar, combustíveis, medicamentos etc.). Granularidade por contrato, fonte TCE-PR.",
};

// Lista hardcoded dos clusters com mapping para descricao_canonica.
// Mantida em sincronia com config/cluster_keywords.yaml (19 clusters).
const CLUSTERS_TCE: { id: string; nome: string }[] = [
  { id: "merenda_escolar", nome: "Merenda escolar" },
  { id: "combustivel_servicos", nome: "Combustíveis" },
  { id: "medicamentos", nome: "Medicamentos" },
  { id: "material_medico_hospitalar", nome: "Material médico-hospitalar" },
  { id: "servicos_saude_credenciamento", nome: "Credenciamento de saúde" },
  { id: "papel_escritorio", nome: "Papel e expediente" },
  { id: "limpeza_higiene", nome: "Limpeza e higiene" },
  { id: "uniformes_epi", nome: "Uniformes e EPI" },
  { id: "materiais_construcao_eletrico", nome: "Material elétrico" },
  { id: "materiais_construcao_hidraulico", nome: "Material hidráulico" },
  { id: "materiais_construcao_geral", nome: "Materiais de construção" },
  { id: "eletrodomesticos_mobiliario", nome: "Eletrodomésticos e mobiliário" },
  { id: "materiais_escolares", nome: "Materiais escolares" },
  { id: "materiais_agricolas", nome: "Ferramentas agrícolas" },
  { id: "agricultura_familiar", nome: "Agricultura familiar (PNAE)" },
  { id: "incentivo_cultura", nome: "Incentivo à cultura" },
  { id: "transporte_escolar", nome: "Transporte escolar" },
  { id: "obras_pavimentacao", nome: "Obras de pavimentação" },
  { id: "obras_edificacao", nome: "Obras de edificação" },
];

const DEFAULT_CLUSTER = "merenda_escolar";
const DEFAULT_MUNICIPIOS = "410690,412770"; // Curitiba + Toledo

type SearchParams = {
  cluster?: string;
  municipios?: string;
};

export default async function CompararPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const clusterId = params.cluster?.trim() || DEFAULT_CLUSTER;
  const cdTcesRaw = params.municipios?.trim() || DEFAULT_MUNICIPIOS;
  const cdTces = cdTcesRaw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => /^\d{6,7}$/.test(s));

  // (1) Lista de municípios catalogados para popular os <select>.
  // (2) Ranking do cluster (todos municípios PR com dados, sem filtro porte).
  const [listaMunR, rankingR] = await Promise.allSettled([
    buscar.municipios({ limit: 50 }),
    tcepr.rankingMunicipios(clusterId, { limit: 200 }),
  ]);
  const lista = listaMunR.status === "fulfilled" ? listaMunR.value : [];
  const ranking = rankingR.status === "fulfilled" ? rankingR.value : [];

  // Filtra ranking pelos cd_tce solicitados, preservando a ordem do usuário.
  // Para cd_tce sem dados no ranking (município com 0 contratos no cluster),
  // ainda assim mostramos a linha vazia.
  const selecionados: (RankingMunicipio & { encontrado: boolean })[] = [];
  for (const cd of cdTces) {
    const found = ranking.find((r) => r.cd_tce === cd);
    if (found) {
      selecionados.push({ ...found, encontrado: true });
    } else {
      // Tenta achar o nome via lista catalogada
      const m = lista.find((mp) => mp.cd_tce === cd);
      selecionados.push({
        cluster_id: clusterId,
        cd_tce: cd,
        cd_ibge: m?.cd_ibge ?? "",
        municipio: m?.nome ?? `cd_tce ${cd}`,
        porte: m?.porte ?? "—",
        n_contratos: 0,
        valor_total_periodo: "0",
        mediana_valor_contrato: "0",
        encontrado: false,
      });
    }
  }

  // Mediana entre os selecionados (referência para % de spread)
  const medianasSel = selecionados
    .filter((r) => r.encontrado)
    .map((r) => Number(r.mediana_valor_contrato));
  const medianaRef =
    medianasSel.length === 0
      ? 0
      : medianasSel.sort((a, b) => a - b)[Math.floor(medianasSel.length / 2)];

  const clusterNome =
    CLUSTERS_TCE.find((c) => c.id === clusterId)?.nome ?? clusterId;

  return (
    <div className="space-y-10 max-w-4xl">
      <header className="space-y-2">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <h1 className="text-3xl font-semibold tracking-tight">
          Comparar municípios
        </h1>
        <p className="text-muted">
          Lado a lado: o que dois ou mais municípios paranaenses pagaram em
          contratos de uma mesma categoria-piloto. Granularidade por contrato
          (TCE-PR não publica item-a-item — ver{" "}
          <Link href="/metodologia">metodologia</Link>). Comparação fica útil
          quando os municípios têm porte parecido; entre portes diferentes,
          interpretar com cuidado.
        </p>
      </header>

      <form action="/comparar" method="get" className="space-y-3 border border-line rounded-md p-4 bg-white">
        <div className="space-y-1">
          <label className="text-xs uppercase tracking-wide text-muted block">
            Categoria
          </label>
          <select
            name="cluster"
            defaultValue={clusterId}
            className="w-full border border-line rounded-md px-3 py-2 text-sm bg-paper"
          >
            {CLUSTERS_TCE.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <label className="text-xs uppercase tracking-wide text-muted block">
            Municípios (até 6) — escolha pelo menos 2
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {Array.from({ length: 6 }).map((_, i) => {
              const selectedCd = cdTces[i] ?? "";
              return (
                <select
                  key={i}
                  name={`m_${i}`}
                  defaultValue={selectedCd}
                  className="border border-line rounded-md px-2 py-1.5 text-sm bg-paper"
                >
                  <option value="">— vazio —</option>
                  {lista.map((mp) => (
                    <option key={mp.cd_tce} value={mp.cd_tce}>
                      {mp.nome}
                    </option>
                  ))}
                </select>
              );
            })}
          </div>
          <p className="text-xs text-muted pt-1">
            A lista mostra os 50 municípios catalogados em <code>analytics.municipio_pr</code>.
            Para municípios não catalogados (~365 demais do PR), use a URL
            direta: <code>/comparar?cluster=...&municipios=cd_tce_1,cd_tce_2</code>.
          </p>
        </div>

        {/* Hidden field que reune os selects em CSV antes de submit (via JS no submit) */}
        <noscript>
          <p className="text-xs text-attention">
            Sem JavaScript: copie os valores manualmente para o campo abaixo.
          </p>
          <input
            name="municipios"
            defaultValue={cdTcesRaw}
            className="w-full border border-line rounded-md px-3 py-2 text-sm bg-paper font-mono"
          />
        </noscript>

        <button
          type="submit"
          className="border border-ink rounded-md px-4 py-2 text-sm no-underline hover:bg-ink hover:text-paper"
        >
          Comparar
        </button>

        {/* Script inline mínimo: junta os m_i em municipios=csv antes de submit */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function(){
                const f = document.currentScript.closest('form');
                f.addEventListener('submit', (e) => {
                  const sels = f.querySelectorAll('select[name^="m_"]');
                  const vals = Array.from(sels).map(s => s.value).filter(Boolean);
                  if (vals.length < 1) return; // deixa default
                  // remove os m_i para a URL ficar limpa
                  sels.forEach(s => s.removeAttribute('name'));
                  // injeta hidden municipios=csv
                  let h = f.querySelector('input[name="municipios"]');
                  if (!h) {
                    h = document.createElement('input');
                    h.type = 'hidden';
                    h.name = 'municipios';
                    f.appendChild(h);
                  }
                  h.value = vals.join(',');
                });
              })();
            `,
          }}
        />
      </form>

      <section>
        <h2 className="text-xl font-semibold mb-3">
          {clusterNome} — comparação entre {selecionados.length} municípios
        </h2>
        {selecionados.length < 2 && (
          <p className="text-sm text-attention">
            Selecione ao menos 2 municípios para comparar.
          </p>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b-2 border-line">
                <th className="text-left py-2 pr-3 font-medium">Município</th>
                <th className="text-left py-2 px-3 font-medium text-xs text-muted">Porte</th>
                <th className="text-right py-2 px-3 font-medium">Contratos</th>
                <th className="text-right py-2 px-3 font-medium">Volume total</th>
                <th className="text-right py-2 px-3 font-medium">Mediana / contrato</th>
                <th className="text-right py-2 pl-3 font-medium text-xs text-muted">vs mediana</th>
              </tr>
            </thead>
            <tbody>
              {selecionados.map((r) => {
                const m = Number(r.mediana_valor_contrato);
                const acima = medianaRef > 0 ? (m - medianaRef) / medianaRef : 0;
                const cor =
                  Math.abs(acima) <= 0.05
                    ? "text-muted"
                    : acima > 0
                      ? "text-attention"
                      : "text-ok";
                return (
                  <tr
                    key={r.cd_tce}
                    className="border-b border-line/60"
                  >
                    <td className="py-2 pr-3">
                      {r.encontrado ? (
                        <Link
                          href={`/municipio/${r.cd_tce}`}
                          className="no-underline hover:underline font-medium"
                        >
                          {r.municipio}
                        </Link>
                      ) : (
                        <span className="text-muted">{r.municipio}</span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-xs text-muted">
                      {r.porte.replace("municipio_pr_", "")}
                    </td>
                    <td className="py-2 px-3 text-right font-mono">
                      {r.encontrado ? r.n_contratos.toLocaleString("pt-BR") : "—"}
                    </td>
                    <td className="py-2 px-3 text-right font-mono">
                      {r.encontrado ? fmtBRL(r.valor_total_periodo) : "—"}
                    </td>
                    <td className="py-2 px-3 text-right font-mono font-medium">
                      {r.encontrado ? fmtBRL(m) : (
                        <span className="text-xs text-muted">sem contratos no cluster</span>
                      )}
                    </td>
                    <td className={"py-2 pl-3 text-right text-xs " + cor}>
                      {r.encontrado && Math.abs(acima) > 0.05
                        ? `${acima > 0 ? "+" : ""}${(acima * 100).toFixed(0)}%`
                        : ""}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={6} className="text-xs text-muted pt-2">
                  Mediana de referência (entre os selecionados):{" "}
                  <strong>{fmtBRL(medianaRef)}</strong>. Diferenças{" "}
                  &lt;5% omitidas.
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>

      <section className="text-sm text-muted border-t border-line pt-6 space-y-2">
        <p>
          <strong>Como ler.</strong> Mediana alta indica contratos
          individualmente maiores — pode refletir economia de escala (1 grande
          contrato em vez de muitos pequenos), especialização, ou simplesmente
          modelo de gestão diferente. Não é prova de irregularidade. Para
          contexto, abra o município e veja órgãos contratantes + fornecedores.
        </p>
        <p>
          <strong>Sem dados no cluster?</strong> O município pode ter 0
          contratos cuja descrição bate com a categoria-piloto, ou os
          contratos dele estão em quarentena (cobertura keyword no estado é
          ~33%). Tente outra categoria ou abra a página do município pra ver
          contratos disponíveis.
        </p>
      </section>
    </div>
  );
}
