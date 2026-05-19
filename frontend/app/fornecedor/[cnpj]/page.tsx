import Link from "next/link";
import type { Metadata } from "next";
import { fmtBRL, fmtBRLCompact } from "@/lib/api";
import { Stat } from "@/lib/Stat";
import { GuardrailFornecedorBadge } from "@/lib/Badge";
import { DisclaimerOrigem } from "@/lib/DisclaimerOrigem";
import { BotaoContestarRanking } from "@/lib/BotaoContestarRanking";
import {
  alertas as alertasApi,
  fornecedor as fornecedorApi,
  type AlertaDispensa,
  type FornecedorPerfil,
  type FornecedorAgregado,
  type FornecedorContrato,
} from "@/lib/tcepr";

export const dynamic = "force-dynamic";

// Guardrail §6.5 do plano: noindex/nofollow na Fase 1; reavaliar com
// revisão jurídica antes de tornar SEO-amigável.
export async function generateMetadata({
  params,
}: {
  params: Promise<{ cnpj: string }>;
}): Promise<Metadata> {
  const { cnpj } = await params;
  return {
    title: `Fornecedor público ${cnpj} · Quanto Pagou`,
    description:
      "Perfil de fornecedor — apresenta dados públicos extraídos de portais oficiais. A presença aqui não implica irregularidade.",
    robots: { index: false, follow: false, nocache: true },
  };
}

export default async function FornecedorPage({
  params,
}: {
  params: Promise<{ cnpj: string }>;
}) {
  const { cnpj } = await params;

  // LGPD L.2.b: API retorna 404 com mensagem distinta para
  //   (a) threshold < 5 contratos
  //   (b) tipo_juridico != 'PJ' (MEI/EI/PF/desconhecido)
  // Em vez de notFound() generico, renderizamos pagina explicativa pra
  // dar gancho de correcao e nao deixar o usuario achar que o site quebrou.
  let perfil: FornecedorPerfil;
  try {
    perfil = await fornecedorApi.perfil(cnpj);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "";
    return <PerfilIndisponivel cnpj={cnpj} motivo={msg} />;
  }

  const [porOrgao, porMunicipio, porCategoria, porModalidade, contratos, alertasDispensaR] =
    await Promise.allSettled([
      fornecedorApi.porOrgao(cnpj, 10),
      fornecedorApi.porMunicipio(cnpj, 10),
      fornecedorApi.porCategoria(cnpj),
      fornecedorApi.porModalidade(cnpj),
      fornecedorApi.contratos(cnpj, 30),
      alertasApi.dispensaRepetida({ cnpj, limit: 20 }),
    ]);

  const orgaos =
    porOrgao.status === "fulfilled" ? porOrgao.value : [];
  const municipios =
    porMunicipio.status === "fulfilled" ? porMunicipio.value : [];
  const categorias =
    porCategoria.status === "fulfilled" ? porCategoria.value : [];
  const modalidades =
    porModalidade.status === "fulfilled" ? porModalidade.value : [];
  const ctos =
    contratos.status === "fulfilled" ? contratos.value : [];
  const alertasDispensa: AlertaDispensa[] =
    alertasDispensaR.status === "fulfilled" ? alertasDispensaR.value : [];

  const concentracaoOrgaoTopPct =
    orgaos.length > 0
      ? Number(orgaos[0].valor_total) / Number(perfil.valor_total)
      : 0;

  return (
    <article className="space-y-10 max-w-3xl">
      <header className="space-y-2">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <p className="text-xs uppercase tracking-wide text-muted">
          Fornecedor público · CNPJ <code>{perfil.fornecedor_cnpj}</code>
          {perfil.cnpj_mascarado && (
            <span className="text-attention"> · mascarado pelo TCE-PR</span>
          )}
        </p>
        <h1 className="text-3xl font-semibold tracking-tight leading-tight">
          {perfil.fornecedor_nome ?? "Fornecedor sem nome registrado"}
        </h1>
        <div className="flex items-baseline gap-2 flex-wrap pt-1">
          <GuardrailFornecedorBadge n_contratos={perfil.n_contratos_total} />
        </div>
      </header>

      <DisclaimerOrigem fonte="tce-pr" />

      {alertasDispensa.length > 0 && (
        <AlertaDispensaBanner rows={alertasDispensa} />
      )}

      <section className="border border-attention/40 bg-attention/5 rounded-md p-4 text-sm space-y-2">
        <p className="font-medium text-attention">
          Como interpretar este perfil
        </p>
        <p className="text-muted leading-relaxed">
          Esta página apresenta dados públicos de contratos firmados entre
          este fornecedor e órgãos públicos brasileiros, extraídos de
          portais oficiais (TCE-PR, Compras.gov.br). A presença aqui{" "}
          <strong>não implica irregularidade</strong> — é apenas o
          registro de quanto e com quem este fornecedor contratou. Volume
          alto não é prova de nada por si só; é ponto de partida para
          investigação por jornalistas e órgãos de controle.
        </p>
        <p className="text-muted leading-relaxed">
          Se algum dado aqui está errado, reporte em{" "}
          <Link href="/correcoes">/correcoes</Link>. SLA: 48h.
        </p>
      </section>

      <section className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <Stat
          label="Contratos registrados"
          value={perfil.n_contratos_total.toLocaleString("pt-BR")}
        />
        <Stat
          label="Volume contratado"
          value={fmtBRLCompact(perfil.valor_total)}
          hint={fmtBRL(perfil.valor_total)}
        />
        <Stat
          label="Órgãos contratantes"
          value={String(perfil.n_orgaos_distintos)}
          hint={
            concentracaoOrgaoTopPct > 0.5
              ? `${(concentracaoOrgaoTopPct * 100).toFixed(0)}% no maior`
              : undefined
          }
        />
        <Stat
          label="Municípios"
          value={String(perfil.n_municipios_distintos)}
        />
      </section>

      {(perfil.primeiro_contrato || perfil.ultimo_contrato) && (
        <section className="text-sm text-muted">
          Janela de contratos:{" "}
          {perfil.primeiro_contrato
            ? fmtDateBR(perfil.primeiro_contrato)
            : "—"}{" "}
          → {perfil.ultimo_contrato ? fmtDateBR(perfil.ultimo_contrato) : "—"}.
        </section>
      )}

      {orgaos.length > 0 && (
        <Block
          titulo="Distribuição por órgão contratante"
          legenda="Volume agregado por órgão. Concentração alta no maior órgão pode ser legítima (especialização) ou ponto de atenção — interpretação depende do contexto."
          linhas={orgaos}
          totalRef={Number(perfil.valor_total)}
          cnpj={cnpj}
          tipo="orgao"
        />
      )}

      <div className="flex justify-end -mt-6">
        <BotaoContestarRanking
          url={`/fornecedor/${encodeURIComponent(cnpj)}`}
          contexto={
            `Contestação de decisão automatizada (LGPD art. 20). ` +
            `Perfil de fornecedor CNPJ ${cnpj}` +
            (perfil.fornecedor_nome ? ` (${perfil.fornecedor_nome})` : "") +
            `. Motivo da contestação: [descreva por que a distribuição agregada ` +
            `apresentada não é representativa / por que este perfil ` +
            `não deveria ser público].`
          }
        />
      </div>


      {municipios.length > 0 && (
        <Block
          titulo="Distribuição por município"
          legenda={`${perfil.n_municipios_distintos} municípios distintos no total; lista exibe os 10 maiores por volume.`}
          linhas={municipios}
          totalRef={Number(perfil.valor_total)}
          cnpj={cnpj}
          tipo="municipio"
        />
      )}

      {categorias.length > 0 && (
        <Block
          titulo="Distribuição por categoria-piloto"
          legenda='Categorias mapeadas pelos clusters keyword (config/cluster_keywords.yaml). "Sem categoria mapeada" = contratos cujo objeto não casa com nenhum cluster atual; ainda visíveis no detalhe.'
          linhas={categorias}
          totalRef={Number(perfil.valor_total)}
          cnpj={cnpj}
          tipo="categoria"
        />
      )}

      {modalidades.length > 0 && (
        <Block
          titulo="Distribuição por modalidade de licitação"
          legenda='Modalidade resolvida via Licitacao.xml + LicitacaoXContrato.xml (TCE-PR). "Sem modalidade resolvida" agrupa contratos onde a ligação licitação-contrato não foi recuperável; presença alta de dispensa/inexigibilidade pode ser legítima ou ponto de atenção, depende do contexto.'
          linhas={modalidades}
          totalRef={Number(perfil.valor_total)}
          cnpj={cnpj}
          tipo="modalidade"
        />
      )}

      {ctos.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl font-semibold">
            Contratos do fornecedor ({ctos.length} mais relevantes)
          </h2>
          <p className="text-sm text-muted">
            Cada linha é clicável e abre o detalhe do contrato com link para a
            fonte primária (ZIP do TCE-PR ou API Compras.gov.br).
          </p>
          <ol className="space-y-2">
            {ctos.map((c) => (
              <ContratoRow key={c.raw_id} c={c} />
            ))}
          </ol>
        </section>
      )}

      <footer className="text-sm text-muted border-t border-line pt-6 space-y-2">
        <p>
          Threshold mínimo de 5 contratos para gerar perfil público —
          fornecedores eventuais não aparecem aqui.{" "}
          <Link href="/manifesto">Por quê</Link>.
        </p>
        <p>
          Página excluída do indexamento de buscas (
          <code>noindex, nofollow</code>) na Fase 1, conforme política
          interna até revisão jurídica.
        </p>
      </footer>
    </article>
  );
}

function AlertaDispensaBanner({ rows }: { rows: AlertaDispensa[] }) {
  const totalDispensas = rows.reduce((s, r) => s + r.n_dispensas_12m, 0);
  const valorTotal = rows.reduce(
    (s, r) => s + Number(r.valor_total_dispensas),
    0,
  );
  const orgaoUnico = rows.length === 1;
  return (
    <section className="border border-attention rounded-md p-4 bg-attention/10 text-sm space-y-3">
      <header className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-attention font-medium">
          Alerta de dispensa repetida · PLANO §19.6
        </p>
        <p className="font-medium">
          Este fornecedor aparece em {rows.length}{" "}
          {orgaoUnico ? "combinação órgão+município" : "combinações órgão+município"}{" "}
          com 3 ou mais dispensas nos últimos 12 meses
          {totalDispensas > rows.length * 3 && (
            <> · {totalDispensas} dispensas no total</>
          )}
          .
        </p>
      </header>
      <p className="text-xs text-muted leading-relaxed">
        <strong>Não implica irregularidade</strong> — calamidade pública,
        especialização técnica ou fracasso de processos anteriores podem
        explicar o uso recorrente da dispensa. A informação está aqui pra
        servir de ponto de partida pra investigação, não conclusão.
        Janela: rolling 12 meses, refresh semanal.
      </p>
      <ol className="space-y-1 text-xs">
        {rows.map((a) => (
          <li
            key={`${a.orgao_codigo}-${a.cd_tce}`}
            className="flex items-baseline gap-3 border-t border-line/60 pt-1.5"
          >
            <span className="flex-1 min-w-0 truncate">
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
            </span>
            <span className="font-mono whitespace-nowrap">
              {a.n_dispensas_12m} disp.
            </span>
            <span className="font-mono whitespace-nowrap w-20 text-right">
              {fmtBRLCompact(a.valor_total_dispensas)}
            </span>
            <span className="text-muted whitespace-nowrap">
              {a.primeira_dispensa === a.ultima_dispensa
                ? `${a.primeira_dispensa} (mesmo dia)`
                : `${a.primeira_dispensa} → ${a.ultima_dispensa}`}
            </span>
          </li>
        ))}
      </ol>
      {rows.length > 1 && (
        <p className="text-xs text-muted">
          Total agregado das dispensas listadas: {fmtBRL(valorTotal)}.
        </p>
      )}
    </section>
  );
}

function Block({
  titulo,
  legenda,
  linhas,
  totalRef,
  cnpj,
  tipo,
}: {
  titulo: string;
  legenda: string;
  linhas: FornecedorAgregado[];
  totalRef: number;
  cnpj: string;
  tipo: "orgao" | "municipio" | "categoria" | "modalidade";
}) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">{titulo}</h2>
      <p className="text-sm text-muted max-w-xl">{legenda}</p>
      <ol className="text-sm space-y-1 border border-line rounded-md p-4 bg-white">
        {linhas.map((l, i) => {
          const pct = totalRef > 0 ? Number(l.valor_total) / totalRef : 0;
          const drillHref = buildBlockDrillHref(tipo, cnpj, l);
          return (
            <li
              key={l.chave}
              className="flex items-baseline gap-3 border-b border-line/60 py-1.5"
            >
              <span className="w-6 text-right text-muted">{i + 1}.</span>
              <span className="flex-1 min-w-0 truncate">
                {l.nome ?? l.chave}
              </span>
              <span className="text-xs text-muted w-16 text-right">
                {l.n_contratos} c.
              </span>
              {drillHref ? (
                <Link
                  href={drillHref}
                  className="font-mono w-28 text-right no-underline hover:underline"
                  title={`Ver ${l.n_contratos} contratos`}
                >
                  {fmtBRL(l.valor_total)}
                </Link>
              ) : (
                <span className="font-mono w-28 text-right">
                  {fmtBRL(l.valor_total)}
                </span>
              )}
              <span className="text-xs text-muted w-12 text-right">
                {(pct * 100).toFixed(0)}%
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function buildBlockDrillHref(
  tipo: "orgao" | "municipio" | "categoria" | "modalidade",
  cnpj: string,
  l: FornecedorAgregado,
): string | null {
  const base = new URLSearchParams({
    fornecedor_cnpj: cnpj,
    fornecedor_nome: "", // será preenchido pelo perfil
  });
  if (tipo === "orgao") {
    base.set("orgao_codigo", l.chave);
    base.set("orgao_nome", l.nome ?? "");
    return `/contratos?${base.toString()}`;
  }
  if (tipo === "municipio") {
    // chave pode ser cd_ibge ou cd_tce; endpoint resolve ambos
    if (l.chave.length === 7) base.set("cd_ibge", l.chave);
    else base.set("cd_tce", l.chave);
    base.set("municipio_nome", l.nome ?? "");
    return `/contratos?${base.toString()}`;
  }
  if (tipo === "categoria") {
    if (l.chave === "_quarentena") {
      base.set("em_quarentena", "true");
    } else {
      base.set("cluster_id", l.chave);
      base.set("cluster_nome", l.nome ?? "");
    }
    return `/contratos?${base.toString()}`;
  }
  if (tipo === "modalidade") {
    base.set("modalidade", l.chave === "sem_modalidade" ? "sem_modalidade" : l.chave);
    return `/contratos?${base.toString()}`;
  }
  return null;
}

function ContratoRow({ c }: { c: FornecedorContrato }) {
  return (
    <li>
      <Link
        href={`/contrato/${c.raw_id}`}
        className="block border border-line rounded-md p-3 bg-white text-sm space-y-1 no-underline hover:border-ink"
      >
        <div className="flex items-baseline justify-between gap-2 flex-wrap">
          <span className="font-medium">
            {c.municipio ? `${c.municipio} · ` : ""}
            {c.orgao_nome}
          </span>
          <span className="font-mono">{fmtBRL(c.valor_total)}</span>
        </div>
        <div className="text-muted text-xs">
          {c.contract_date && <span>{fmtDateBR(c.contract_date)} · </span>}
          contrato {c.contrato_id}
          {c.em_quarentena && (
            <span className="text-attention"> · sem cluster</span>
          )}
          <span className="ml-2 text-attention">→ ver detalhe</span>
        </div>
        <p className="text-muted leading-relaxed">
          {c.descricao.length > 240
            ? c.descricao.slice(0, 240) + "…"
            : c.descricao}
        </p>
      </Link>
    </li>
  );
}

function fmtDateBR(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

function PerfilIndisponivel({
  cnpj,
  motivo,
}: {
  cnpj: string;
  motivo: string;
}) {
  const ePJ = motivo.includes("tipo jurídico");
  const ePoucoContratos = motivo.includes("mínimo");
  return (
    <article className="space-y-6 max-w-2xl">
      <header>
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight pt-2">
          Perfil indisponível
        </h1>
        <p className="text-xs uppercase tracking-wide text-muted pt-2">
          CNPJ <code>{cnpj}</code>
        </p>
      </header>

      <section className="border border-attention/40 bg-attention/5 rounded-md p-4 text-sm space-y-3">
        <p className="font-medium text-attention">
          Este perfil não está disponível publicamente
        </p>
        {ePJ && (
          <p className="leading-relaxed">
            O tipo jurídico deste CNPJ não está confirmado como{" "}
            <strong>pessoa jurídica</strong>. Por defesa em camadas LGPD
            (PLANO §18 L.2), perfis de microempreendedores (MEI), empresários
            individuais (EI) ou pessoas físicas não são publicados por
            padrão — o CNPJ destes tipos está atrelado ao CPF do titular,
            o que muda o regime jurídico do dado.
          </p>
        )}
        {ePoucoContratos && (
          <p className="leading-relaxed">
            Este fornecedor tem menos de 5 contratos públicos registrados em
            nossa base. Por guardrail §6.5 do plano, fornecedores eventuais
            não geram perfil público para reduzir risco de exposição
            injusta.
          </p>
        )}
        {!ePJ && !ePoucoContratos && (
          <p className="leading-relaxed">
            Não foi possível carregar este perfil. Pode ser CNPJ não
            encontrado na base, fornecedor com menos de 5 contratos, ou
            tipo jurídico não confirmado como pessoa jurídica.
          </p>
        )}
        <p className="leading-relaxed text-muted">
          Se você acredita que este perfil <strong>deve</strong> ser
          público — por exemplo, é uma empresa formalmente constituída
          (LTDA, S.A., EIRELI, cooperativa) cujo nome não casou com nossa
          heurística de classificação — solicite verificação em{" "}
          <Link href="/correcoes">/correcoes</Link>. SLA: 15 dias (art. 19
          LGPD) ou 48h para correção factual.
        </p>
      </section>

      <section className="text-sm text-muted space-y-2">
        <p>
          Documentos relacionados:{" "}
          <Link href="/politica-privacidade">Política de Privacidade</Link>
          {" · "}
          <Link href="/lgpd">Canal LGPD</Link>
          {" · "}
          <Link href="/metodologia">Metodologia</Link>
        </p>
      </section>
    </article>
  );
}
