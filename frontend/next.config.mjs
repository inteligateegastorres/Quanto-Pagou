/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Desliga cache em dev para sempre buscar do FastAPI local
  experimental: { staleTimes: { dynamic: 0, static: 30 } },
  // /curitiba era pagina hardcoded antes da /municipio generica existir.
  // Mantemos o slug como atalho com redirect 308 (permanente, preserva
  // metodo HTTP) para nao quebrar links externos eventualmente
  // compartilhados antes do refactor.
  async redirects() {
    return [
      {
        source: "/curitiba",
        destination: "/municipio/410690",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
