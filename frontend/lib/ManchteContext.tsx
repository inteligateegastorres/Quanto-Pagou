// Componente reusavel: lista manchetes ativas filtradas por contexto
// (cluster_id ou cd_tce). Renderiza so se houver matches.
//
// Uso em /cluster/[id] e /municipio/[cd_tce].

import Link from "next/link";
import { manchetes as manchetesApi, type Manchete } from "@/lib/tcepr";
import { Badge } from "@/lib/Badge";

const CLUSTER_LABEL: Record<string, string> = {
  merenda_escolar: "merenda escolar",
  combustivel_servicos: "combustíveis",
  medicamentos: "medicamentos",
  material_medico_hospitalar: "material médico-hospitalar",
  servicos_saude_credenciamento: "credenciamento de saúde",
  papel_escritorio: "papel e expediente",
  limpeza_higiene: "limpeza e higiene",
  uniformes_epi: "uniformes e EPI",
  materiais_construcao_eletrico: "material elétrico",
  materiais_construcao_hidraulico: "material hidráulico",
  materiais_construcao_geral: "materiais de construção",
  eletrodomesticos_mobiliario: "eletrodomésticos e mobiliário",
  materiais_escolares: "materiais escolares",
  materiais_agricolas: "ferramentas agrícolas",
  agricultura_familiar: "agricultura familiar",
  incentivo_cultura: "incentivo à cultura",
  transporte_escolar: "transporte escolar",
  obras_pavimentacao: "obras de pavimentação",
  obras_edificacao: "obras de edificação",
};

export async function ManchteContextBox({
  cluster_id,
  cd_tce,
}: {
  cluster_id?: string;
  cd_tce?: string;
}) {
  let lista: Manchete[] = [];
  try {
    lista = await manchetesApi.lista();
  } catch {
    return null; // Falha silenciosa: contexto opcional, nao bloqueia pagina
  }

  // Filtra pelo contexto
  const filtradas = lista.filter((m) => {
    if (cluster_id && m.cluster_id !== cluster_id) return false;
    if (cd_tce && m.cd_tce !== cd_tce) return false;
    return true;
  });

  if (filtradas.length === 0) return null;

  const titulo = cluster_id
    ? "Manchetes deste cluster"
    : cd_tce
      ? "Manchetes onde este município aparece"
      : "Manchetes";

  return (
    <section className="border border-attention/30 bg-attention/5 rounded-md p-4 text-sm space-y-3">
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <p className="font-semibold text-attention uppercase tracking-wide text-xs">
          {titulo}
        </p>
        <Link
          href="/manchetes"
          className="text-xs text-muted no-underline hover:underline"
        >
          ver todas →
        </Link>
      </div>
      <ul className="space-y-2">
        {filtradas.map((m) => (
          <li
            key={`${m.cluster_id}__${m.cd_tce}`}
            className="border-l-2 border-attention/40 pl-3"
          >
            <Link
              href={`/manchetes#manchete-${m.rank_no_dia}`}
              className="no-underline hover:underline text-ink"
            >
              {/* Cluster page: mostra municipio. Municipio page: mostra cluster. */}
              {cluster_id ? (
                <strong>{m.municipio_nome ?? m.cd_tce}</strong>
              ) : (
                <strong>{CLUSTER_LABEL[m.cluster_id] ?? m.cluster_id}</strong>
              )}
              {" · "}
              <span className="text-attention">
                {Number(m.spread).toFixed(1)}× a mediana de pares
              </span>
              <span className="text-xs text-muted ml-2">
                (#{m.rank_no_dia} · {m.n_sujeito} contratos)
              </span>
            </Link>
            <div className="pt-1">
              <Badge
                label={`${m.janelas_passadas}/3 janelas`}
                tone={m.janelas_passadas === 3 ? "ok" : "muted"}
                tooltip="Spread acima do limiar em quantas das 3 janelas (90/180/365d)"
              />
            </div>
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted">
        Selecionadas por algoritmo (config{" "}
        <code>config/manchete_v1.yaml</code>). Nao e curadoria.
      </p>
    </section>
  );
}
