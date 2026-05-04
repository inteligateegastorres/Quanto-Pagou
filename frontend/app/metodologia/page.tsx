import Link from "next/link";

export default function MetodologiaPage() {
  return (
    <article className="prose-like max-w-2xl space-y-6 text-sm leading-relaxed">
      <Link href="/" className="text-xs text-muted no-underline">
        ← início
      </Link>
      <h1 className="text-2xl font-semibold tracking-tight">Metodologia (v0.1)</h1>

      <Section title="Fontes">
        <p>
          Fase 0.5 utiliza a API pública{" "}
          <a href="https://dadosabertos.compras.gov.br" target="_blank">
            dadosabertos.compras.gov.br
          </a>{" "}
          (módulo Contratos · endpoint <code>2_consultarContratosItem</code>).
          Cada coleta gera um <em>snapshot bruto imutável</em> versionado por
          hash SHA-256 — o pipeline é uma função pura sobre snapshots e pode
          ser reprocessado a qualquer momento.
        </p>
      </Section>

      <Section title="Resolução de itens (Tier 1)">
        <p>
          Itens são agrupados em <em>clusters</em> com <em>versão</em>. Hoje
          usamos apenas Tier 1 (CATMAT direto): se o código CATMAT do item está
          no <em>golden set</em> curado, ele entra no cluster com confiança
          1.00. CATMAT fora do golden gera cluster sintético (confiança 0.85).
          Itens sem CATMAT entram em <strong>quarentena</strong> e ficam
          visíveis, mas não entram em rankings ou comparações.
        </p>
        <p className="text-muted">
          Tiers 2 (embeddings), 3 (dicionários curados) e 4 (LLM resolver)
          entram em fases posteriores conforme o tráfego e o feedback.
        </p>
      </Section>

      <Section title="Normalização de unidade">
        <p>
          Antes de comparar preços, descrições como “PACOTE 5KG”, “500G”,
          “RESMA 500 FOLHAS” são convertidas para uma unidade-base (kg, litro,
          unidade, resma_500). Quando a descrição é ambígua, o item entra em
          quarentena com motivo legível.
        </p>
      </Section>

      <Section title="Comparação entre pares">
        <p>
          Para cada cluster, agrupamos itens por (esfera × UF × porte) e
          calculamos mediana, p25 e p75. Mostramos o intervalo p25–p75
          explicitamente para tornar a incerteza visível. Comparações públicas
          só consideram itens com confiança ≥ 0.75.
        </p>
      </Section>

      <Section title="Linguagem">
        <p>
          Não usamos as palavras “suspeito”, “irregular” ou “desviado”.
          Apresentamos os números e a fonte primária. Cabe ao leitor — e aos
          órgãos de controle — interpretar.
        </p>
      </Section>

      <Section title="Política de correção">
        <p>
          Toda correção feita após um relato vai para a página{" "}
          <Link href="/correcoes">/correcoes</Link>, com data, item afetado e
          delta antes → depois. SLA: 48h para resposta.
        </p>
      </Section>
    </article>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-2">
      <h2 className="text-base font-semibold">{title}</h2>
      <div className="space-y-2">{children}</div>
    </section>
  );
}
