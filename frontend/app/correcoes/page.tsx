import Link from "next/link";
import type { Metadata } from "next";
import {
  correcoes,
  TIPO_LABEL,
  STATUS_LABEL,
  type CorrecaoTicket,
} from "@/lib/correcoes";
import { criarTicketAction } from "./actions";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Correções públicas · Quanto Pagou",
  description:
    "Toda correção feita após um relato é registrada aqui — data, item, delta antes → depois. SLA: 48h (correção factual) ou 15 dias (LGPD art. 19).",
};

export default async function CorrecoesPage() {
  let recentes: CorrecaoTicket[] = [];
  let recentesErr: string | null = null;
  try {
    recentes = await correcoes.recentes(20);
  } catch (e) {
    recentesErr = e instanceof Error ? e.message : "erro";
  }

  return (
    <div className="max-w-2xl space-y-8">
      <Link href="/" className="text-xs text-muted no-underline">
        ← início
      </Link>
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">
          Correções públicas
        </h1>
        <p className="text-muted leading-relaxed">
          Esta página existe porque dados públicos errados são piores que
          dados ausentes. Toda correção feita após um relato é registrada
          aqui — com data, item afetado e delta antes → depois. Tickets
          ativos também aparecem (sem detalhes) para auditoria pública de
          SLA.
        </p>
      </header>

      <section className="border border-line rounded-md p-5 bg-white space-y-3">
        <h2 className="text-base font-semibold">Como funciona</h2>
        <ol className="list-decimal pl-5 space-y-1 text-sm">
          <li>Você reporta no formulário abaixo. Recebe um ticket ID público.</li>
          <li>
            Investigamos. <strong>SLA 48h</strong> para correções
            factuais, <strong>15 dias</strong> para pedidos LGPD (art.
            19).
          </li>
          <li>
            Se confirmado, corrigimos no banco e registramos delta
            antes → depois no ticket público.
          </li>
          <li>
            Você acompanha o status em{" "}
            <code>/correcoes/&#123;ticket_id&#125;</code> a qualquer
            momento — sem cadastro.
          </li>
        </ol>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold">Reportar erro</h2>
        <p className="text-sm text-muted">
          Encontrou um número que parece errado, um cluster mal-classificado,
          uma escola atribuída ao município errado, ou quer exercer um
          direito do art. 18 LGPD? Conte abaixo.
        </p>
        <form
          action={criarTicketAction}
          className="border border-line rounded-md p-4 bg-white space-y-3 text-sm"
        >
          <div className="space-y-1">
            <label
              htmlFor="tipo"
              className="text-xs uppercase tracking-wide text-muted block"
            >
              Tipo do pedido <span className="text-attention">*</span>
            </label>
            <select
              id="tipo"
              name="tipo"
              required
              defaultValue="factual"
              className="w-full border border-line rounded-md px-3 py-2 bg-paper"
            >
              {(
                Object.entries(TIPO_LABEL) as [keyof typeof TIPO_LABEL, string][]
              ).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            <p className="text-xs text-muted">
              Erro factual → SLA 48h. Pedidos LGPD (acesso, correção,
              eliminação) → SLA 15 dias (art. 19).
            </p>
          </div>

          <div className="space-y-1">
            <label
              htmlFor="descricao"
              className="text-xs uppercase tracking-wide text-muted block"
            >
              Descrição <span className="text-attention">*</span>
            </label>
            <textarea
              id="descricao"
              name="descricao"
              required
              minLength={20}
              maxLength={4000}
              rows={5}
              placeholder='ex: "cluster diz medicamentos mas é claramente material hospitalar — ver contrato 279460"'
              className="w-full border border-line rounded-md px-3 py-2 bg-paper"
            />
            <p className="text-xs text-muted">
              Mínimo 20 caracteres. Quanto mais específico, mais rápido a
              gente confirma.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label
                htmlFor="url_afetada"
                className="text-xs uppercase tracking-wide text-muted block"
              >
                URL afetada
              </label>
              <input
                id="url_afetada"
                name="url_afetada"
                maxLength={500}
                placeholder="https://quantopagou.org/contrato/279460"
                className="w-full border border-line rounded-md px-3 py-2 bg-paper"
              />
            </div>

            <div className="space-y-1">
              <label
                htmlFor="raw_id_afetado"
                className="text-xs uppercase tracking-wide text-muted block"
              >
                raw_id do contrato (se souber)
              </label>
              <input
                id="raw_id_afetado"
                name="raw_id_afetado"
                inputMode="numeric"
                pattern="[0-9]*"
                placeholder="ex: 279460"
                className="w-full border border-line rounded-md px-3 py-2 bg-paper"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label
              htmlFor="fornecedor_cnpj"
              className="text-xs uppercase tracking-wide text-muted block"
            >
              CNPJ do fornecedor (se aplicável)
            </label>
            <input
              id="fornecedor_cnpj"
              name="fornecedor_cnpj"
              maxLength={20}
              placeholder="00.000.000/0000-00"
              className="w-full border border-line rounded-md px-3 py-2 bg-paper"
            />
          </div>

          <div className="space-y-1">
            <label
              htmlFor="fonte_correta"
              className="text-xs uppercase tracking-wide text-muted block"
            >
              Fonte primária correta (link/referência, se souber)
            </label>
            <input
              id="fonte_correta"
              name="fonte_correta"
              maxLength={1000}
              placeholder="ex: link pro XML do TCE-PR ou nota fiscal"
              className="w-full border border-line rounded-md px-3 py-2 bg-paper"
            />
          </div>

          <div className="space-y-1">
            <label
              htmlFor="contato_email"
              className="text-xs uppercase tracking-wide text-muted block"
            >
              Seu e-mail (opcional, para receber a resposta)
            </label>
            <input
              id="contato_email"
              name="contato_email"
              type="email"
              maxLength={255}
              placeholder="seu@email.com"
              className="w-full border border-line rounded-md px-3 py-2 bg-paper"
            />
            <p className="text-xs text-muted">
              O e-mail é privado — nunca aparece na vitrine pública.
              Auditável internamente conforme L.10 audit log.
            </p>
          </div>

          <div className="space-y-1">
            <label className="text-xs flex items-start gap-2">
              <input
                type="checkbox"
                name="publicar_descricao"
                className="mt-1"
              />
              <span className="text-muted">
                Aceito que a <strong>descrição</strong> deste relato apareça
                publicamente em <Link href="/correcoes">/correcoes</Link>{" "}
                quando o ticket for resolvido (sem identificação minha).
                Marque se quiser que outras pessoas vejam o que você reportou.
              </span>
            </label>
          </div>

          <button
            type="submit"
            className="border border-ink rounded-md px-4 py-2 no-underline hover:bg-ink hover:text-paper"
          >
            Abrir ticket
          </button>
          <p className="text-xs text-muted">
            Ao enviar, você receberá um ticket público{" "}
            <code>QP-AAAA-XXXX</code> e será redirecionado para a página
            pública do ticket. Acompanhamento sem cadastro.
          </p>
        </form>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold">Histórico recente</h2>
        {recentesErr && (
          <div className="border border-attention/40 bg-attention/5 rounded-md p-3 text-sm text-attention">
            Não foi possível carregar o histórico ({recentesErr}). Tente
            recarregar.
          </div>
        )}
        {!recentesErr && recentes.length === 0 && (
          <div className="border border-dashed border-line rounded-md p-5 text-sm text-muted space-y-2">
            <p>
              <strong className="text-ink">
                Sem correções confirmadas até agora.
              </strong>
            </p>
            <p>
              Não conte isso como &quot;nada acontece&quot; — conte como{" "}
              &quot;ninguém pegou erro grande ainda&quot;. Quando pegar,
              você vai ver aqui antes de ver no PR.
            </p>
          </div>
        )}
        {recentes.length > 0 && (
          <ol className="space-y-2">
            {recentes.map((t) => (
              <TicketRow key={t.ticket_id} t={t} />
            ))}
          </ol>
        )}
      </section>

      <section className="text-xs text-muted border-t border-line pt-4 space-y-2">
        <p>
          Documentos relacionados:{" "}
          <Link href="/politica-privacidade">Política de Privacidade</Link>
          {" · "}
          <Link href="/lgpd">Canal LGPD</Link>
          {" · "}
          <Link href="/termos">Termos de Uso</Link>
        </p>
      </section>
    </div>
  );
}

function TicketRow({ t }: { t: CorrecaoTicket }) {
  return (
    <li className="border border-line rounded-md p-3 bg-white text-sm space-y-1">
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <Link
          href={`/correcoes/${t.ticket_id}`}
          className="font-mono no-underline hover:underline"
        >
          {t.ticket_id}
        </Link>
        <span className="text-xs text-muted">
          {fmtData(t.resolvido_em ?? t.criado_em)}
        </span>
      </div>
      <p className="text-muted text-xs">
        {TIPO_LABEL[t.tipo]} · {STATUS_LABEL[t.status]}
      </p>
      {t.resolucao_publica && (
        <p className="leading-relaxed">{t.resolucao_publica}</p>
      )}
      {!t.resolucao_publica && t.descricao_publica && (
        <p className="text-muted leading-relaxed italic">
          {t.descricao_publica}
        </p>
      )}
    </li>
  );
}

function fmtData(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}
