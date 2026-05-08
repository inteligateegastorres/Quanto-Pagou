import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
  ),
  title: "Quanto Pagou",
  description:
    "Plataforma cívica para monitorar gastos públicos brasileiros e identificar possíveis desvios.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="font-sans antialiased text-ink">
        <div className="bg-paper border-b border-line text-xs">
          <div className="max-w-5xl mx-auto px-6 py-2 text-muted flex items-baseline gap-4 flex-wrap">
            <span>
              <strong className="text-ok">Paraná:</strong> 156k contratos reais
              de 397 municípios (TCE-PR PIT, semanal).
            </span>
            <span>
              <strong className="text-attention">Federal:</strong> fixture
              metodológica · API Compras.gov.br instável.
            </span>
            <Link href="/metodologia" className="ml-auto no-underline">
              detalhes →
            </Link>
          </div>
        </div>
        <header className="border-b border-line">
          <div className="max-w-5xl mx-auto px-6 py-4 flex items-baseline justify-between">
            <Link href="/" className="text-lg font-semibold tracking-tight no-underline">
              Quanto Pagou
            </Link>
            <nav className="text-sm text-muted flex gap-5 flex-wrap justify-end">
              <Link href="/buscar">Buscar</Link>
              <Link href="/comparar">Comparar</Link>
              <Link href="/dispensas">Dispensas</Link>
              <Link href="/escolas">Escolas</Link>
              <Link href="/manifesto">Manifesto</Link>
              <Link href="/metodologia">Metodologia</Link>
              <Link href="/correcoes">Correções</Link>
              <a
                href="http://127.0.0.1:8001/docs"
                target="_blank"
                rel="noreferrer"
              >
                API
              </a>
            </nav>
          </div>
        </header>
        <main className="max-w-5xl mx-auto px-6 py-10">{children}</main>
        <footer className="border-t border-line mt-20">
          <div className="max-w-5xl mx-auto px-6 py-6 text-xs text-muted">
            Dados: Compras.gov.br · Snapshots versionados ·{" "}
            <Link href="/correcoes">Reportar erro</Link>
          </div>
        </footer>
      </body>
    </html>
  );
}
