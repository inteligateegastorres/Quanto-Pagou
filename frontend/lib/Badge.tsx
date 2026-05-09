// Familia de badges de confianca/proveniencia (PLANO §13.6).
//
// Padrao visual: pill pequena, monospace, uppercase, com border colorida e
// tooltip explicativo. Mesma gramatica em todas as paginas.
//
// Hierarquia em conflito (PLANO §13.6): se confianca e baixa E valor esta
// fora da banda, confianca vem primeiro (mais a esquerda) — confianca baixa
// ja e por si so o sinal, nao chamar atencao para valor.

export type BadgeTone = "ok" | "attention" | "muted" | "ink";

const TONE_CLASS: Record<BadgeTone, string> = {
  ok: "border-ok/50 bg-ok/5 text-ok",
  attention: "border-attention/50 bg-attention/5 text-attention",
  muted: "border-line bg-paper text-muted",
  ink: "border-line bg-paper text-ink",
};

export function Badge({
  label,
  tone = "muted",
  tooltip,
  href,
}: {
  label: string;
  tone?: BadgeTone;
  tooltip?: string;
  href?: string;
}) {
  const cls =
    "inline-block border rounded px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide whitespace-nowrap " +
    TONE_CLASS[tone];
  if (href) {
    return (
      <a href={href} target="_blank" rel="noreferrer" className={cls + " no-underline hover:underline"} title={tooltip}>
        {label}
      </a>
    );
  }
  return (
    <span className={cls} title={tooltip}>
      {label}
    </span>
  );
}

// ---------- Helpers ---------------------------------------------------------

/**
 * Badge de confianca a partir do score [0..1] do item canonical.
 *
 * Thresholds: PLANO §13.6.
 * - >= 0.85 -> alta (verde)
 * -  0.6 ~ 0.85 -> media (amarelo/atencao)
 * -  < 0.6 -> baixa (cinza com borda atencao)
 */
export function ConfiancaBadge({ confianca }: { confianca: number | null | undefined }) {
  if (confianca == null) {
    return (
      <Badge
        label="confiança ?"
        tone="muted"
        tooltip="Sem score de confianca disponivel para este item."
      />
    );
  }
  if (confianca >= 0.85) {
    return (
      <Badge
        label="confiança alta"
        tone="ok"
        tooltip={`Cluster confirmado por CATMAT (Tier 1) ou keyword forte. score=${confianca.toFixed(2)}.`}
      />
    );
  }
  if (confianca >= 0.6) {
    return (
      <Badge
        label="confiança média"
        tone="attention"
        tooltip={`Keyword no objeto — pode haver itens fora do cluster. score=${confianca.toFixed(2)}.`}
      />
    );
  }
  return (
    <Badge
      label="confiança baixa"
      tone="muted"
      tooltip={`Item pode estar mal classificado. Nao entra em rankings. score=${confianca.toFixed(2)}.`}
    />
  );
}

/** Badge para item sem cluster ou em quarentena. */
export function SemClusterBadge({ motivo }: { motivo?: string | null }) {
  return (
    <Badge
      label="sem cluster"
      tone="attention"
      tooltip={
        motivo
          ? `Item sem categoria — visivel mas nao entra em rankings. Motivo: ${motivo}.`
          : "Item sem categoria — visivel mas nao entra em rankings ou comparacoes."
      }
    />
  );
}

/** Link clicavel para a fonte primaria (XML do TCE-PR ou similar). */
export function FontePrimariaBadge({ url }: { url: string | null | undefined }) {
  if (!url) return null;
  return (
    <Badge
      label="fonte primária"
      tone="ink"
      tooltip="Abre o XML/JSON original na fonte oficial."
      href={url}
    />
  );
}

/** "Atualizado em X" — para listas e cards. */
export function AtualizadoBadge({ iso }: { iso: string | null | undefined }) {
  if (!iso) return null;
  const data = iso.slice(0, 10);
  return (
    <Badge
      label={`atualizado ${fmtDateBR(data)}`}
      tone="muted"
      tooltip={`Snapshot mais recente: ${data}.`}
    />
  );
}

/** Versao do modelo de cluster (toda comparacao). */
export function ClusterVersionBadge({ version = "v1" }: { version?: string }) {
  return (
    <Badge
      label={`cluster_version=${version}`}
      tone="muted"
      tooltip="Versao do modelo de cluster usada nesta comparacao. Mudancas geram nova versao; historico nunca e reescrito."
    />
  );
}

/** Guardrail §6.5 — perfil de fornecedor com >= N contratos. */
export function GuardrailFornecedorBadge({ n_contratos }: { n_contratos: number }) {
  return (
    <Badge
      label={`guardrail §6.5 · ${n_contratos} contratos`}
      tone="muted"
      tooltip="Perfil so e publicado para fornecedores com >= 5 contratos. Reduz exposicao injusta de fornecedores eventuais."
    />
  );
}

function fmtDateBR(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}
