import { ImageResponse } from "next/og";

export const runtime = "nodejs";
export const contentType = "image/png";
export const size = { width: 1200, height: 630 };
export const alt =
  "Por que ministérios pagam preços tão diferentes pelo mesmo diesel? · Quanto Pagou";

const API_BASE =
  process.env.QUANTOPAGOU_API_BASE ?? "http://127.0.0.1:8001";

const CLUSTER_ID = "oleo_diesel_s10";

type Pares = {
  mediana: string;
  iqr: string;
  n: number;
};
type RankingOrgao = {
  orgao_nome: string;
  mediana_orgao: string;
  n_compras: number;
};

const fmtBRL = (n: number) =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
  }).format(n);

async function fetchData(): Promise<{
  mediana: number;
  topName: string;
  topVal: number;
  bottomName: string;
  bottomVal: number;
  spreadPct: number;
} | null> {
  try {
    const [paresR, rankR] = await Promise.all([
      fetch(`${API_BASE}/pares?cluster_id=${CLUSTER_ID}`, {
        cache: "no-store",
      }),
      fetch(
        `${API_BASE}/ranking/orgaos?cluster_id=${CLUSTER_ID}&order=mediana_desc&limit=50`,
        { cache: "no-store" },
      ),
    ]);
    if (!paresR.ok || !rankR.ok) return null;
    const pares = ((await paresR.json()) as Pares[])[0];
    const rank = (await rankR.json()) as RankingOrgao[];
    if (!pares || rank.length === 0) return null;
    const mediana = Number(pares.mediana);
    const top = rank[0];
    const bottom = rank[rank.length - 1];
    const topVal = Number(top.mediana_orgao);
    const bottomVal = Number(bottom.mediana_orgao);
    return {
      mediana,
      topName: shorten(top.orgao_nome),
      topVal,
      bottomName: shorten(bottom.orgao_nome),
      bottomVal,
      spreadPct: (topVal - bottomVal) / bottomVal,
    };
  } catch {
    return null;
  }
}

function shorten(full: string): string {
  return full
    .replace(/^MINISTERIO DA /i, "Min. ")
    .replace(/^MINISTERIO DO /i, "Min. ");
}

export default async function Image() {
  const data = await fetchData();
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#fdfdfb",
          color: "#1a1a1a",
          padding: "60px 70px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div
            style={{
              fontSize: 22,
              color: "#b3580f",
              textTransform: "uppercase",
              letterSpacing: 1.5,
              fontWeight: 600,
              display: "flex",
            }}
          >
            Insight · Quanto Pagou
          </div>
          <div
            style={{
              fontSize: 60,
              lineHeight: 1.1,
              fontWeight: 700,
              maxWidth: 1000,
              display: "flex",
            }}
          >
            Por que ministérios pagam preços tão diferentes pelo mesmo
            diesel?
          </div>
        </div>

        {data ? (
          <div
            style={{
              display: "flex",
              gap: 40,
              padding: "30px 0",
              borderTop: "2px solid #e6e2d8",
              borderBottom: "2px solid #e6e2d8",
            }}
          >
            <Box
              label={`mais caro · ${data.topName}`}
              value={fmtBRL(data.topVal)}
              tone="#b3580f"
            />
            <Box
              label="mediana federal"
              value={fmtBRL(data.mediana)}
              tone="#1a1a1a"
            />
            <Box
              label={`mais barato · ${data.bottomName}`}
              value={fmtBRL(data.bottomVal)}
              tone="#1f6f3b"
            />
          </div>
        ) : (
          <div
            style={{
              fontSize: 28,
              color: "#5b5b5b",
              padding: "20px 0",
              display: "flex",
            }}
          >
            Comparação entre órgãos federais · diesel S10
          </div>
        )}

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            color: "#5b5b5b",
            fontSize: 22,
          }}
        >
          <div style={{ display: "flex" }}>
            {data
              ? `Spread de ${(data.spreadPct * 100).toFixed(0)}% entre os dois extremos · mesma esfera, mesmo período`
              : "Spread observado em contratos federais · mesma esfera"}
          </div>
          <div style={{ display: "flex", fontWeight: 600, color: "#1a1a1a" }}>
            quantopagou · /insight/diesel-ministerios
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}

function Box({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
        flex: 1,
      }}
    >
      <div
        style={{
          fontSize: 18,
          color: "#5b5b5b",
          textTransform: "uppercase",
          letterSpacing: 1.2,
          display: "flex",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 56,
          fontWeight: 700,
          color: tone,
          fontFamily: "monospace",
          display: "flex",
        }}
      >
        {value}
      </div>
    </div>
  );
}
