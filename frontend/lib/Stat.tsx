// Card de estatistica reusavel — usado nas paginas /curitiba, /municipio,
// /fornecedor, /contrato, /insight, /cluster e na home.
// Trata overflow: number grande (ex: "R$ 5.118.928.922,33") era truncado
// visualmente vazando para o card adjacente quando colocado em <div grid>.
// Para valores monetarios grandes, prefira fmtBRLCompact (R$ 5,12 bi).

export type StatTone = "ink" | "attention" | "ok";

const TONE_CLASS: Record<StatTone, string> = {
  ink: "text-ink",
  attention: "text-attention",
  ok: "text-ok",
};

export function Stat({
  label,
  value,
  hint,
  tone = "ink",
  highlight,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: StatTone;
  highlight?: boolean;
}) {
  return (
    <div className="border border-line rounded-md p-4 overflow-hidden min-w-0">
      <div className="text-xs text-muted uppercase tracking-wide truncate">
        {label}
      </div>
      <div
        className={
          "font-mono font-semibold whitespace-nowrap overflow-hidden text-ellipsis " +
          (highlight ? "text-2xl " : "text-xl ") +
          TONE_CLASS[tone]
        }
        title={value}
      >
        {value}
      </div>
      {hint && (
        <div
          className="text-xs text-muted mt-1 truncate"
          title={hint}
        >
          {hint}
        </div>
      )}
    </div>
  );
}
