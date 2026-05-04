import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto"],
      },
      colors: {
        ink: "#1a1a1a",
        paper: "#fdfdfb",
        muted: "#5b5b5b",
        line: "#e6e2d8",
        attention: "#b3580f",
        ok: "#1f6f3b",
      },
    },
  },
  plugins: [],
} satisfies Config;
