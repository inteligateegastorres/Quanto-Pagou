import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
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
        <header className="border-b border-line">
          <div className="max-w-5xl mx-auto px-6 py-4 flex items-baseline justify-between">
            <Link href="/" className="text-lg font-semibold tracking-tight no-underline">
              Quanto Pagou
            </Link>
            <nav className="text-sm text-muted flex gap-6">
              <Link href="/metodologia">Metodologia</Link>
              <Link href="/correcoes">Correções</Link>
              <a
                href="http://127.0.0.1:8000/docs"
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
