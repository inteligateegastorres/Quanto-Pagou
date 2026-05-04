import Link from "next/link";

export default function CorrecoesPage() {
  return (
    <div className="max-w-2xl space-y-6">
      <Link href="/" className="text-xs text-muted no-underline">
        ← início
      </Link>
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Correções recentes</h1>
        <p className="text-sm text-muted">
          Toda correção feita após um relato aparece aqui — com data, item
          afetado e delta antes → depois. SLA: 48h.
        </p>
      </header>

      <section className="border border-dashed border-line rounded-md p-6 text-sm text-muted">
        <p>
          <strong>Sem correções até agora.</strong>
        </p>
        <p className="mt-2">
          Esta página existe desde o lançamento. Quando recebermos o primeiro
          relato em <code>🚩 Reportar erro</code>, ele aparecerá aqui — público,
          datado e com a versão de cluster afetada.
        </p>
      </section>
    </div>
  );
}
