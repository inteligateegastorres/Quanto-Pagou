/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Desliga cache em dev para sempre buscar do FastAPI local
  experimental: { staleTimes: { dynamic: 0, static: 30 } },
};

export default nextConfig;
