import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Metodologia · Quanto Pagou",
  description:
    "Como o Quanto Pagou coleta, normaliza e compara preços de contratos públicos. Fontes, resolução de cluster, normalização de unidade, guardrails, política de correção.",
};

export default function MetodologiaPage() {
  return (
    <article className="prose-like max-w-2xl space-y-6 text-sm leading-relaxed">
      <Link href="/" className="text-xs text-muted no-underline">
        ← início
      </Link>
      <h1 className="text-2xl font-semibold tracking-tight">
        Metodologia (v0.2)
      </h1>
      <p className="text-muted">
        Atualizado para refletir o pipeline TCE-PR completo (~156 mil
        contratos reais), o cluster Tier 1.5 por palavra-chave (19
        categorias) e os guardrails que limitam o que entra na vitrine
        pública.
      </p>

      <Section title="Fontes">
        <p>
          Duas esteiras coexistem hoje:
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li>
            <strong>Paraná (real):</strong> ZIP anual público{" "}
            <a
              href="https://pit.tce.pr.gov.br/Arquivos/2025_PIT_TodosArquivos.zip"
              target="_blank"
              rel="noreferrer"
            >
              pit.tce.pr.gov.br/Arquivos/{"{ano}_PIT_TodosArquivos.zip"}
            </a>
            . 397 municípios, granularidade <em>por contrato</em> (TCE
            não publica item-a-item). Atualização semanal via cron
            (GitHub Actions).
          </li>
          <li>
            <strong>Federal (fixture):</strong>{" "}
            <a href="https://dadosabertos.compras.gov.br" target="_blank" rel="noreferrer">
              dadosabertos.compras.gov.br
            </a>{" "}
            — API com falhas intermitentes de backend. Mantemos uma
            fixture sintética para preservar o pipeline downstream;
            ingest real volta quando o upstream estabilizar.
          </li>
        </ul>
        <p>
          Cada coleta gera um <em>snapshot bruto imutável</em> versionado
          por hash SHA-256. O pipeline é uma função pura sobre snapshots
          e pode ser reprocessado sem nova coleta.
        </p>
      </Section>

      <Section title="Resolução de itens (Tier 1 + Tier 1.5)">
        <p>
          Itens entram em <em>clusters</em> com <strong>versão</strong>{" "}
          (hoje <code>v1</code>). Mudança de modelo gera nova versão;
          histórico nunca é reescrito.
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li>
            <strong>Tier 1 (federal):</strong> CATMAT direto contra{" "}
            <em>golden set</em> curado. CATMAT no golden → confiança
            1.00. Fora do golden → cluster sintético (0.85). Sem CATMAT
            → quarentena.
          </li>
          <li>
            <strong>Tier 1.5 (TCE-PR):</strong> palavra-chave em{" "}
            <code>dsObjeto</code> contra 19 categorias em{" "}
            <code>config/cluster_keywords.yaml</code>. Threshold de
            confiança ≥ 0.6. Cobertura atual: ~34% dos 156k contratos.
            O resto fica visível com label "sem cluster" — não some.
          </li>
          <li>
            Tiers 2 (embeddings), 3 (dicionários curados) e 4 (LLM
            resolver) entram em fases posteriores conforme o tráfego e
            o feedback. <em>Progressive correctness</em>: maturidade é
            destino, não ponto de partida.
          </li>
        </ul>
      </Section>

      <Section title="Normalização de unidade">
        <p>
          Antes de comparar preços, descrições como "PACOTE 5KG", "500G",
          "RESMA 500 FOLHAS" são convertidas para uma unidade-base (kg,
          litro, unidade, resma_500) via{" "}
          <code>config/unit_conversion.yaml</code> (versionado). Quando a
          descrição é ambígua, o item entra em quarentena com motivo
          legível.
        </p>
        <p className="text-muted">
          Convenções anti-bug travadas em testes: "S10 LITRO" não vira
          "10 L"; "75G/M²" (gramatura) não vira peso. Ver{" "}
          <code>tests/test_resolution.py</code> (28 casos).
        </p>
      </Section>

      <Section title="Comparação entre pares — IQR, não σ ingênuo">
        <p>
          Para cada cluster, agrupamos itens por (esfera × UF × porte)
          ou (cluster × município × porte) e calculamos{" "}
          <strong>mediana, p25, p75 e IQR</strong>. Nunca usamos
          desvio-padrão ingênuo — distribuições reais de preço público
          têm caudas longas que quebram σ.
        </p>
        <p>
          Mostramos o intervalo p25–p75 explicitamente para tornar a
          incerteza visível. Comparações públicas só consideram itens
          com confiança ≥ 0.75. O badge <code>cluster_version=v1</code>{" "}
          aparece em toda comparação.
        </p>
      </Section>

      <Section title="Guardrail §6.5 — perfis de fornecedor">
        <p>
          Páginas de perfil de fornecedor (<code>/fornecedor/[cnpj]</code>)
          só são publicadas quando o fornecedor tem <strong>≥ 5
          contratos</strong> no histórico. Abaixo disso, o agregado é
          estatisticamente frágil e expõe pessoas/empresas a leitura
          injusta.
        </p>
        <p>
          Adicional: páginas de fornecedor têm{" "}
          <code>noindex, nofollow</code> e modal "como interpretar"
          obrigatório, com decomposição de sub-scores. Nunca usamos a
          palavra "Risco" sem decompor.
        </p>
      </Section>

      <Section title="Quarentena visível">
        <p>
          Item sem CATMAT, sem unidade detectável, com cluster_id
          ambíguo ou abaixo do threshold de confiança entra em{" "}
          <code>analytics.item_canonical.em_quarentena=true</code> com
          motivo legível. <strong>Continua acessível por URL</strong>;
          só não entra em rankings ou comparações.
        </p>
      </Section>

      <Section title="Limites por design">
        <p>
          Algumas perguntas comuns que o site <strong>não responde</strong>{" "}
          — por limitação da fonte, não por escolha:
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li>
            <strong>"Verba destinada à UPA Centro":</strong> o TCE-PR
            não tem esse conceito. O dinheiro vai pro fornecedor; a UPA
            aparece no contrato como local de uso. A página{" "}
            <Link href="/instituicoes">/instituicoes</Link> agrega
            contratos cuja descrição menciona o termo, mas isso{" "}
            <strong>não equivale</strong> a verba total da unidade.
          </li>
          <li>
            <strong>Comparação numérica entre escolas:</strong> a
            extração via regex captura ~0,17% dos contratos (concentrada
            em obras de edificação). Não há base para comparar custo
            por aluno entre escolas. <Link href="/escolas">/escolas</Link>{" "}
            é um <em>catálogo de transparência</em>, não um ranking.
          </li>
          <li>
            <strong>Modalidade do contrato</strong> (pregão, dispensa,
            concorrência) vem de <code>Licitacao.xml</code> +{" "}
            <code>LicitacaoXContrato.xml</code> via JOIN em memória.
            Cobertura ~65% no estado completo.
          </li>
        </ul>
      </Section>

      <Section title="Linguagem">
        <p>
          Não usamos as palavras "suspeito", "irregular" ou "desviado".
          Apresentamos os números, a fonte primária e o intervalo p25–p75.
          Cabe ao leitor — e aos órgãos de controle — interpretar.
        </p>
      </Section>

      <Section title="Política de correção">
        <p>
          Toda correção feita após um relato vai para{" "}
          <Link href="/correcoes">/correcoes</Link>, com data, item
          afetado e delta antes → depois. SLA: 48h para resposta.
          Esteira <strong>editorial</strong> (irregular, dispara
          correção rápida) e esteira <strong>automática</strong>{" "}
          (semanal, agregados refeitos) são separadas.
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
