import Link from "next/link";
import type { Metadata } from "next";
import { fmtBRL, fmtBRLCompact } from "@/lib/api";
import { manchetes as manchetesApi, type Manchete } from "@/lib/tcepr";
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

export default async function ManchetesPage() {
  let lista: Manchete[] = [];
  let erro: string | null = null;
  try {
    lista = await manchetesApi.lista();
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
      </header>

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

      <div className="pt-1">
        <Link
          href={drillHref}
          className="text-sm border border-line rounded-md px-3 py-1.5 no-underline hover:border-ink"
        >
          Ver os {m.n_sujeito} contratos →
        </Link>
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
