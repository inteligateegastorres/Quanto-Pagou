import Link from "next/link";
import type { Metadata } from "next";
import { API_BASE, fmtBRL, fmtBRLCompact } from "@/lib/api";
import { DisclaimerOrigem } from "@/lib/DisclaimerOrigem";
import { BotaoContestarRanking } from "@/lib/BotaoContestarRanking";
import {
  alertas as alertasApi,
  manchetes as manchetesApi,
  type AlertaDispensa,
  type Manchete,
  type ManchteDiagnostico,
  type ManchteSaida,
} from "@/lib/tcepr";
import {
  Badge,
  ClusterVersionBadge,
  AtualizadoBadge,
} from "@/lib/Badge";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Manchetes · Quanto Pagou",
  description:
    "Discrepâncias entre municípios paranaenses selecionadas por algoritmo. Sem curadoria humana — parâmetros versionados em config/manchete_v*.yaml.",
};

const CLUSTER_LABEL: Record<string, string> = {
  merenda_escolar: "Merenda escolar",
  combustivel_servicos: "Combustíveis",
  medicamentos: "Medicamentos",
  material_medico_hospitalar: "Material médico-hospitalar",
  servicos_saude_credenciamento: "Credenciamento de saúde",
  papel_escritorio: "Papel e expediente",
  limpeza_higiene: "Limpeza e higiene",
  uniformes_epi: "Uniformes e EPI",
  materiais_construcao_eletrico: "Material elétrico",
  materiais_construcao_hidraulico: "Material hidráulico",
  materiais_construcao_geral: "Materiais de construção",
  eletrodomesticos_mobiliario: "Eletrodomésticos e mobiliário",
  materiais_escolares: "Materiais escolares",
  materiais_agricolas: "Ferramentas agrícolas",
  agricultura_familiar: "Agricultura familiar (PNAE)",
  incentivo_cultura: "Incentivo à cultura",
  transporte_escolar: "Transporte escolar",
  obras_pavimentacao: "Obras de pavimentação",
  obras_edificacao: "Obras de edificação",
};

export default async function ManchetesPage({
  searchParams,
}: {
  searchParams: Promise<{ cd_tce?: string }>;
}) {
  const sp = await searchParams;
  const cdTceQuery = sp.cd_tce?.trim();

  let lista: Manchete[] = [];
  let saidas: ManchteSaida[] = [];
  let alertasDispensa: AlertaDispensa[] = [];
  let diagnostico: ManchteDiagnostico | null = null;
  let erro: string | null = null;
  try {
    [lista, saidas, alertasDispensa] = await Promise.all([
      manchetesApi.lista(),
      manchetesApi.saidas(90).catch(() => [] as ManchteSaida[]),
      alertasApi
        .dispensaRepetida({ limit: 10, order: "n_desc" })
        .catch(() => [] as AlertaDispensa[]),
    ]);
    if (cdTceQuery && /^\d{6,7}$/.test(cdTceQuery)) {
      diagnostico = await manchetesApi.diagnostico(cdTceQuery).catch(() => null);
    }
  } catch (e) {
    erro = e instanceof Error ? e.message : "erro";
  }

  const refreshEm = lista[0]?.refresh_em ?? null;
  const parametrosHash = lista[0]?.parametros_hash ?? null;

  return (
    <div className="space-y-10 max-w-3xl">
      <Link href="/" className="text-xs text-muted no-underline">
        ← início
      </Link>

      <header className="space-y-2">
        <p className="text-xs uppercase tracking-wide text-attention font-medium">
          Selecionadas por algoritmo · sem curadoria humana
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">Manchetes</h1>
        <p className="text-muted leading-relaxed">
          Municípios paranaenses cuja mediana de contrato em uma categoria
          ficou significativamente acima da mediana de pares no estado.
          Os critérios estão em <code>config/manchete_v1.yaml</code> e cada
          manchete carrega o hash da configuração que a colocou aqui — para
          auditoria pública.
        </p>
        <p className="text-xs text-muted pt-1">
          <a
            href={`${API_BASE}/manchetes/feed.xml`}
            className="no-underline hover:underline"
          >
            RSS / Atom feed
          </a>
          {" · "}
          <a
            href={`${API_BASE}/manchetes.csv`}
            className="no-underline hover:underline"
          >
            Exportar CSV
          </a>
          {" · "}
          <a
            href={`${API_BASE}/alertas/progressivos.csv`}
            className="no-underline hover:underline"
          >
            Alertas progressivos (CSV)
          </a>
          {" · "}
          <a
            href={`${API_BASE}/alertas/dispensa-repetida.csv`}
            className="no-underline hover:underline"
          >
            Dispensa repetida (CSV)
          </a>
        </p>
      </header>

      <DisclaimerOrigem fonte="tce-pr" />

      {/* Busca reversa: "minha cidade ta aqui? se nao, por que nao?" */}
      <section className="border border-line rounded-md p-4 bg-paper text-sm space-y-3">
        <p className="font-medium">Onde está sua cidade?</p>
        <form action="/manchetes" method="get" className="flex gap-2 flex-wrap">
          <input
            type="text"
            name="cd_tce"
            inputMode="numeric"
            pattern="[0-9]{6,7}"
            defaultValue={cdTceQuery ?? ""}
            placeholder="cd_tce (6-7 dígitos, ex: 410690)"
            className="flex-1 min-w-0 border border-line rounded-md px-3 py-1.5 text-sm bg-paper"
          />
          <button
            type="submit"
            className="border border-ink rounded-md px-4 py-1.5 text-sm no-underline hover:bg-ink hover:text-paper"
          >
            Diagnosticar
          </button>
        </form>
        <p className="text-xs text-muted">
          Mostra manchetes ativas do município E os outros clusters
          avaliados com motivo de não terem virado manchete (passou ou
          falhou em qual threshold). &quot;Vela apagada também é
          informação.&quot; Cd_tce no header de qualquer página de
          município.
        </p>
        {diagnostico && <DiagnosticoBox d={diagnostico} />}
      </section>

      <section className="border border-line rounded-md p-4 bg-paper text-sm space-y-2">
        <p className="font-medium">Como ler</p>
        <ul className="list-disc pl-5 space-y-1 text-muted">
          <li>
            <strong>Spread</strong> = mediana de contrato do município ÷ mediana
            do cluster no estado todo. Spread 5× = município teve mediana 5
            vezes maior que pares.
          </li>
          <li>
            <strong>Não é prova de irregularidade.</strong> Pode refletir
            economia de escala, especialização, ou modelo de gestão diferente.
            Use como ponto de partida para investigação, não como conclusão.
          </li>
          <li>
            <strong>Linguagem factual.</strong> Não usamos &quot;suspeito&quot;
            ou &quot;irregular&quot;. Mostramos os números, a fonte primária e
            o contexto — ver <Link href="/metodologia">metodologia</Link>.
          </li>
        </ul>
      </section>

      {parametrosHash && (
        <section className="text-xs text-muted flex flex-wrap items-baseline gap-2 border-t border-line pt-3">
          <span>Configuração ativa:</span>
          <Badge
            label={`hash=${parametrosHash}`}
            tone="muted"
            tooltip="Hash do YAML de parametros que selecionou estas manchetes. Editar o YAML e re-rodar refresh muda este hash."
          />
          <ClusterVersionBadge version={lista[0]?.cluster_version} />
          <AtualizadoBadge iso={refreshEm} />
        </section>
      )}

      {erro && (
        <p className="text-sm text-attention">Falha ao carregar: {erro}</p>
      )}

      {!erro && lista.length === 0 && (
        <p className="text-sm text-muted">
          Nenhuma manchete ativa no momento. Os parâmetros atuais
          (config/manchete_v1.yaml) podem estar conservadores demais para o
          snapshot vigente, ou o pipeline pode não ter sido refrescado ainda.
        </p>
      )}

      <ol className="space-y-4">
        {lista.map((m) => (
          <ManchteCard key={m.rank_no_dia} m={m} />
        ))}
      </ol>

      {alertasDispensa.length > 0 && (
        <AlertaDispensaSection rows={alertasDispensa} />
      )}

      {saidas.length > 0 && (
        <section className="space-y-3 border-t border-line pt-6">
          <h2 className="text-base font-semibold">
            Recém-saídas <span className="text-xs text-muted font-normal">(últimos 90 dias · vela apagada também é informação)</span>
          </h2>
          <ul className="space-y-2 text-sm">
            {saidas.map((s) => (
              <li
                key={`${s.saiu_em}__${s.manchete_id}`}
                className="border border-line rounded-md p-3 bg-paper"
              >
                <div className="flex items-baseline justify-between gap-2 flex-wrap">
                  <span className="font-medium">
                    {(s.cluster_id && CLUSTER_LABEL[s.cluster_id]) ?? s.cluster_id ?? "—"}
                    {" · "}
                    {s.municipio_nome ?? "—"}
                  </span>
                  <span className="text-xs text-muted">
                    saiu em {s.saiu_em.slice(0, 10)}
                  </span>
                </div>
                <p className="text-muted text-xs pt-1">
                  <strong>Motivo:</strong> {s.motivo}
                  {s.spread_anterior && (
                    <span className="ml-2">
                      (spread anterior:{" "}
                      <span className="font-mono">{Number(s.spread_anterior).toFixed(1)}×</span>)
                    </span>
                  )}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="text-xs text-muted border-t border-line pt-6 space-y-2">
        <p>
          <strong>Por que esse algoritmo, não curadoria.</strong> Curadoria
          humana de manchetes vira ranking político mesmo quando bem
          intencionada. O algoritmo é estúpido de propósito: aplica critérios
          versionados em <code>config/manchete_v1.yaml</code> e nada mais.
          Discordou da seleção? PR no YAML, com dados.
        </p>
        <p>
          Achou erro em alguma manchete?{" "}
          <Link href="/correcoes">Reportar em /correcoes</Link>. SLA 48h.
        </p>
      </section>
    </div>
  );
}

function AlertaDispensaSection({ rows }: { rows: AlertaDispensa[] }) {
  return (
    <section className="space-y-3 border-t border-line pt-6">
      <header className="space-y-1">
        <h2 className="text-base font-semibold">
          Dispensa emergencial repetida{" "}
          <span className="text-xs text-muted font-normal">
            (top {rows.length} · PLANO §19.6)
          </span>
        </h2>
        <p className="text-xs text-muted leading-relaxed">
          Combinações <strong>(fornecedor PJ + órgão + município)</strong>{" "}
          com 3 ou mais contratos em <em>modalidade dispensa</em> nos
          últimos 12 meses. <strong>Não implica irregularidade</strong> —
          calamidade pública, especialização técnica ou fracasso de
          processos anteriores podem explicar; mas a frequência merece
          investigação. A janela é rolling — refresh semanal atualiza.
        </p>
      </header>
      <ol className="space-y-2">
        {rows.map((a) => (
          <li
            key={`${a.fornecedor_cnpj}-${a.orgao_codigo}-${a.cd_tce}`}
            className="border border-line rounded-md p-3 bg-paper text-sm"
          >
            <div className="flex items-baseline justify-between gap-2 flex-wrap">
              <div className="flex-1 min-w-0">
                <Link
                  href={`/fornecedor/${encodeURIComponent(a.fornecedor_cnpj)}`}
                  className="font-medium no-underline hover:underline"
                >
                  {a.fornecedor_nome ?? a.fornecedor_cnpj}
                </Link>
                <div className="text-xs text-muted mt-0.5">
                  {a.orgao_nome ?? `órgão ${a.orgao_codigo}`}
                  {a.cd_tce && (
                    <>
                      {" · "}
                      <Link
                        href={`/municipio/${a.cd_tce}`}
                        className="no-underline hover:underline"
                      >
                        cd_tce {a.cd_tce}
                      </Link>
                    </>
                  )}
                </div>
              </div>
              <div className="text-right">
                <div className="font-mono text-base font-medium">
                  {a.n_dispensas_12m}{" "}
                  <span className="text-xs text-muted font-normal">dispensas</span>
                </div>
                <div className="text-xs text-muted">
                  Total: {fmtBRLCompact(a.valor_total_dispensas)}
                </div>
              </div>
            </div>
            <div className="text-xs text-muted mt-2">
              Mediana por contrato: {fmtBRL(a.mediana_valor_dispensa)}
              {" · "}
              Período: {a.primeira_dispensa} → {a.ultima_dispensa}
              {a.primeira_dispensa === a.ultima_dispensa && (
                <span className="text-attention">
                  {" "}· todas no mesmo dia
                </span>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function ManchteCard({ m }: { m: Manchete }) {
  const clusterLabel = CLUSTER_LABEL[m.cluster_id] ?? m.cluster_id;
  const spread = Number(m.spread);
  const medSuj = Number(m.med_sujeito);
  const medCl = Number(m.med_cluster);
  const comparab = Number(m.comparab_proxy);

  const drillHref = `/contratos?${new URLSearchParams({
    cluster_id: m.cluster_id,
    cluster_nome: clusterLabel,
    cd_tce: m.cd_tce,
    municipio_nome: m.municipio_nome ?? "",
    order: "valor_desc",
  }).toString()}`;

  return (
    <li className="border border-line rounded-md p-5 bg-white space-y-3">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <span className="text-xs uppercase tracking-wide text-muted">
          #{m.rank_no_dia} · {clusterLabel}
        </span>
        <Badge
          label={`spread ${spread.toFixed(1)}×`}
          tone={spread >= 8 ? "attention" : "muted"}
          tooltip="Mediana do municipio dividida pela mediana do cluster no estado"
        />
      </div>

      <h2 className="text-lg font-semibold leading-snug">
        Em <Link href={`/municipio/${m.cd_tce}`} className="no-underline hover:underline">
          {m.municipio_nome ?? m.cd_tce}
        </Link>{" "}
        ({m.porte?.replace("municipio_pr_", "") ?? "—"}), a mediana de
        contrato em <strong>{clusterLabel.toLowerCase()}</strong> foi{" "}
        <span className="text-attention">{spread.toFixed(1)}× superior</span>{" "}
        à mediana dos pares no Paraná.
      </h2>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm pt-1">
        <Cell label="Mediana município" value={fmtBRL(medSuj)} />
        <Cell label="Mediana cluster PR" value={fmtBRL(medCl)} muted />
        <Cell
          label="Contratos no cluster"
          value={m.n_sujeito.toLocaleString("pt-BR")}
        />
        <Cell label="Volume" value={fmtBRLCompact(m.valor_total_sujeito)} />
      </div>

      <div className="flex items-baseline gap-2 flex-wrap text-xs pt-1">
        <Badge
          label={`persistente em ${m.janelas_passadas}/3 janelas`}
          tone={m.janelas_passadas === 3 ? "ok" : "muted"}
          tooltip={
            `Spread acima do limiar em ${m.janelas_passadas} de 3 janelas (90d, 180d, 365d). ` +
            `90d=${m.spread_90d ? Number(m.spread_90d).toFixed(1) + "x" : "sem dados"}, ` +
            `180d=${m.spread_180d ? Number(m.spread_180d).toFixed(1) + "x" : "sem dados"}, ` +
            `365d=${m.spread_365d ? Number(m.spread_365d).toFixed(1) + "x" : "sem dados"}.`
          }
        />
        <Badge
          label={`IQR sujeito ${Number(m.iqr_sujeito).toFixed(1)} · cluster ${Number(m.iqr_cluster).toFixed(1)}`}
          tone="muted"
          tooltip="Variacao interna (p75/p25). Filtro relativo: IQR sujeito <= 2x IQR cluster."
        />
        <Badge
          label={`comparabilidade ${comparab.toFixed(2)}`}
          tone={comparab >= 0.8 ? "ok" : "muted"}
          tooltip="Proxy v1 (media geometrica): HHI modalidade, 1 - HHI fornecedor, spread temporal. >=0.65 passa."
        />
        {m.populacao && (
          <Badge
            label={`pop ${m.populacao.toLocaleString("pt-BR")}`}
            tone="muted"
            tooltip="Populacao IBGE Censo 2022"
          />
        )}
      </div>

      <div className="pt-1 flex items-baseline gap-4 flex-wrap">
        <Link
          href={drillHref}
          className="text-sm border border-line rounded-md px-3 py-1.5 no-underline hover:border-ink"
        >
          Ver os {m.n_sujeito} contratos →
        </Link>
        <BotaoContestarRanking
          url={`/manchetes#${m.cluster_id}-${m.cd_tce}`}
          contexto={
            `Contestação de decisão automatizada (LGPD art. 20). ` +
            `Manchete: ${clusterLabel} em ` +
            `${m.municipio_nome ?? m.cd_tce} (cd_tce ${m.cd_tce}, ` +
            `cluster ${m.cluster_id}). ` +
            `Spread ${spread.toFixed(1)}× a mediana do cluster no PR. ` +
            `Motivo da contestação: [descreva por que o ranking não deveria incluir este caso].`
          }
        />
      </div>
    </li>
  );
}

function Cell({
  label,
  value,
  muted,
}: {
  label: string;
  value: string;
  muted?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-muted uppercase tracking-wide">{label}</p>
      <p
        className={
          "font-mono " + (muted ? "text-muted" : "font-semibold text-ink")
        }
      >
        {value}
      </p>
    </div>
  );
}

function DiagnosticoBox({ d }: { d: ManchteDiagnostico }) {
  if (!d.municipio_nome) {
    return (
      <p className="text-sm text-attention pt-2">
        Município <code>{d.cd_tce}</code> não catalogado em{" "}
        <code>analytics.municipio_pr</code> — sem dados de população.
      </p>
    );
  }
  return (
    <div className="border-t border-line pt-3 mt-2 space-y-3">
      <p className="text-sm">
        <Link href={`/municipio/${d.cd_tce}`} className="no-underline hover:underline">
          <strong>{d.municipio_nome}</strong>
        </Link>{" "}
        <span className="text-xs text-muted">
          (cd_tce {d.cd_tce} · pop {d.populacao?.toLocaleString("pt-BR") ?? "?"})
        </span>
      </p>

      {d.ativas.length > 0 ? (
        <div>
          <p className="text-sm font-medium text-attention">
            ✓ Aparece em {d.ativas.length} manchete{d.ativas.length === 1 ? "" : "s"} ativa{d.ativas.length === 1 ? "" : "s"}:
          </p>
          <ul className="list-disc pl-5 text-sm">
            {d.ativas.map((m) => (
              <li key={m.cluster_id}>
                <strong>#{m.rank_no_dia}</strong>{" "}
                {CLUSTER_LABEL[m.cluster_id] ?? m.cluster_id} · spread{" "}
                {Number(m.spread).toFixed(1)}× · {m.janelas_passadas}/3 janelas
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-sm text-muted">
          Não aparece em nenhuma manchete ativa.
        </p>
      )}

      {d.candidatos.length > 0 && (
        <details>
          <summary className="cursor-pointer text-sm">
            {d.candidatos.length} outros clusters avaliados (motivo de não-publicação)
          </summary>
          <ul className="text-xs space-y-1 pt-2 max-h-80 overflow-y-auto">
            {d.candidatos
              .filter((c) => c.motivo_falha)
              .slice(0, 30)
              .map((c) => (
                <li key={c.cluster_id} className="border-l-2 border-line pl-2">
                  <strong>{CLUSTER_LABEL[c.cluster_id] ?? c.cluster_id}</strong>
                  {c.spread && (
                    <span className="text-muted"> · spread {Number(c.spread).toFixed(1)}×</span>
                  )}
                  <span className="text-muted"> · {c.n_sujeito} contratos</span>
                  <p className="text-muted italic pl-2">{c.motivo_falha}</p>
                </li>
              ))}
          </ul>
        </details>
      )}

      {d.parametros_hash && (
        <p className="text-xs text-muted">
          Diagnóstico contra config atual ({" "}
          <code>{d.parametros_hash}</code>).
        </p>
      )}
    </div>
  );
}
