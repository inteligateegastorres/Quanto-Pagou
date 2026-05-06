import { ImageResponse } from "next/og";

export const runtime = "nodejs";
export const contentType = "image/png";
export const size = { width: 1200, height: 630 };
export const alt = "Quanto Pagou — Quanto o governo pagou pela mesma coisa?";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#fdfdfb",
          color: "#1a1a1a",
          padding: "70px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div
            style={{
              fontSize: 28,
              color: "#b3580f",
              textTransform: "uppercase",
              letterSpacing: 2,
              fontWeight: 700,
              display: "flex",
            }}
          >
            Quanto Pagou
          </div>
          <div
            style={{
              fontSize: 78,
              lineHeight: 1.05,
              fontWeight: 700,
              maxWidth: 1000,
              display: "flex",
            }}
          >
            Quanto o governo pagou pela mesma coisa?
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 8,
            fontSize: 28,
            color: "#5b5b5b",
            maxWidth: 950,
          }}
        >
          <div style={{ display: "flex" }}>
            Comparações entre órgãos públicos brasileiros · com fonte primária.
          </div>
          <div style={{ display: "flex" }}>
            Mediana e p25–p75 — sem adjetivos, sem média ingênua.
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            color: "#5b5b5b",
            fontSize: 22,
            borderTop: "2px solid #e6e2d8",
            paddingTop: 24,
          }}
        >
          <div style={{ display: "flex" }}>
            Plataforma cívica aberta · AGPL/MIT/ODbL
          </div>
          <div style={{ display: "flex", fontWeight: 600, color: "#1a1a1a" }}>
            quantopagou
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
