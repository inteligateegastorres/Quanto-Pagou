import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Manifesto · Quanto Pagou",
  description:
    "Por que existe o Quanto Pagou: sucessor cívico do Painel de Preços, plataforma aberta para comparar preços que o setor público pagou pela mesma coisa.",
};

export default function ManifestoPage() {
  return (
    <article className="prose-like max-w-2xl space-y-6 text-base leading-relaxed">
      <Link href="/" className="text-xs text-muted no-underline">
        ← início
      </Link>

      <header className="space-y-2 border-b border-line pb-6">
        <p className="text-xs uppercase tracking-wide text-attention font-medium">
          Manifesto · v0.1 · 06 de maio de 2026
        </p>
        <h1 className="text-3xl font-semibold tracking-tight leading-tight">
          O preço público é uma das poucas coisas que o cidadão consegue
          conferir sozinho.
        </h1>
        <p className="text-muted text-base">
          E ficou mais difícil de conferir desde julho de 2025.
        </p>
      </header>

      <Section title="O que aconteceu">
        <p>
          Em 4 de julho de 2025, o <strong>Painel de Preços</strong>, sistema
          oficial do Ministério da Gestão e Inovação que permitia comparar
          quanto diferentes órgãos federais pagaram pela mesma compra, parou
          de receber atualizações. Nunca foi formalmente descontinuado;
          simplesmente congelou. As bases ainda estão online, com dados
          desatualizados há quase um ano.
        </p>
        <p>
          Para um país que destina cerca de R$ 700 bilhões anuais a contratos
          públicos, ficar sem o instrumento mais simples de comparação de
          preços não é um detalhe técnico. É uma parada na engrenagem básica
          do controle social.
        </p>
      </Section>

      <Section title="Por que o preço importa mais do que parece">
        <p>
          Preço de commodity é uma das métricas mais auditáveis que existem.
          Diesel S10 tem especificação fixa, definida pela ANP — é o mesmo
          combustível em todo o país. Arroz tipo 1 longo fino é o mesmo
          arroz. Caneta esferográfica azul é caneta esferográfica azul.
          Quando dois órgãos pagam preços muito diferentes pelo mesmo item,
          em janelas próximas e na mesma região, a diferença não vem da
          natureza do produto. Vem de algum outro lugar — modalidade,
          fornecedor, prazo, escala, atenção do gestor.
        </p>
        <p>
          Apontar essa diferença não é acusar ninguém. É devolver o número
          ao público, acompanhado da fonte primária, para quem precisa
          interpretar. <em>Quanto Pagou</em> não diz se está certo ou
          errado. Diz quanto foi.
        </p>
      </Section>

      <Section title="O que esta plataforma faz">
        <p>
          Coletamos contratos públicos federais (e, em fases seguintes,
          estaduais e municipais) das fontes oficiais — Compras.gov.br,
          Portal da Transparência, Querido Diário, TCEs estaduais —, mantemos
          uma cópia imutável de cada coleta versionada por SHA-256, e
          comparamos preço a preço por <em>cluster de item</em>: agrupamentos
          curados a partir do CATMAT/CATSER, com unidades normalizadas
          (kg, litro, unidade-base) e versão registrada.
        </p>
        <p>
          Mostramos a mediana entre pares (mesma esfera, mesmo porte
          municipal, mesma UF), o intervalo entre o quartil inferior e o
          superior (p25–p75) — para que a incerteza fique visível —, e o
          ranking por órgão. <strong>Não usamos média e desvio padrão</strong>{" "}
          porque um único contrato atípico move a média e arruína a
          comparação. Mediana e IQR são robustos; é assim que estatística
          séria trata distribuições assimétricas.
        </p>
      </Section>

      <Section title="Princípios — explícitos para que possam ser cobrados">
        <ul className="list-disc pl-5 space-y-2">
          <li>
            <strong>Comunicação acima de infraestrutura.</strong> Sem clareza
            e distribuição, este projeto vira mais um repositório de dados de
            nicho. A engenharia existe a serviço da frase que vai parar no
            grupo de WhatsApp da família.
          </li>
          <li>
            <strong>Estatística honesta, linguagem honesta.</strong> Mediana
            e IQR. Nunca as palavras &quot;suspeito&quot;,
            &quot;irregular&quot; ou &quot;desviado&quot;. Quem interpreta é
            o leitor; quem investiga é jornalista, vereador, órgão de
            controle. Nosso trabalho é fornecer o número limpo.
          </li>
          <li>
            <strong>Quarentena visível.</strong> Itens que não conseguimos
            classificar (sem CATMAT, sem unidade detectável, descrição
            ambígua) não somem do site. Aparecem com um rótulo &quot;não
            comparável ainda&quot; e a fonte primária acessível. Esconder
            seria o oposto de transparência.
          </li>
          <li>
            <strong>Cluster versionado.</strong> Quando o modo de agrupar
            itens muda, os dados antigos preservam o cluster antigo. O
            histórico nunca é reescrito. Comparações entre versões exigem
            mapeamento explícito documentado.
          </li>
          <li>
            <strong>Correções são públicas.</strong> Toda correção feita
            depois de um relato vai para uma{" "}
            <Link href="/correcoes">página pública</Link> com data, item
            afetado e o delta antes → depois. Errar e corrigir em público é
            mais confiável do que nunca admitir erro.
          </li>
          <li>
            <strong>Progressive correctness.</strong> A versão atual usa
            apenas CATMAT direto e um conjunto pequeno de itens-piloto. Vamos
            sofisticar (embeddings, dicionários, LLM resolver) à medida que
            houver tráfego e feedback. Publicar imperfeito e visível é
            preferível a adiar para perfeito e invisível.
          </li>
        </ul>
      </Section>

      <Section title="Aberto desde o primeiro commit">
        <p>
          Backend AGPL-3.0. SDKs e frontend MIT. Datasets normalizados sob
          ODbL/CC-BY 4.0. Toda a engenharia, todos os testes, todos os YAMLs
          de configuração estão no repositório. Quem discordar de uma escolha
          metodológica pode abrir uma{" "}
          <em>issue</em>; quem quiser usar os dados em uma matéria pode baixar
          o dump em Parquet sem pedir licença a ninguém.
        </p>
        <p>
          Maximizamos uso e contribuição em projetos OSS existentes: Querido
          Diário (OKBR) para diários oficiais municipais, Tá de Pé Dados para
          TCEs estaduais, Brasil.IO para gastos diretos federais. PRs
          upstream sempre que possível.
        </p>
      </Section>

      <Section title="O que vem agora">
        <p>
          Estamos em <strong>Fase 0.5</strong>: site no ar com fixture
          sintética enquanto a API Compras.gov.br não estabiliza (ela está
          com instabilidade crônica de backend). A história editorial
          publicada em <Link href="/insight/diesel-ministerios">/insight</Link>
          {" "}exemplifica o tipo de comparação que faremos com dados reais
          assim que o pipeline rodar contra o upstream — a engenharia já
          está pronta.
        </p>
        <p>
          Fase 1 cobre 80% dos contratos federais com CATMAT, dois ganchos
          virais (Top órgãos por categoria, Top fornecedores em dispensas) e
          boletim semanal automático. Fase 2 traz seis estados (TCE-RS,
          TCE-PE, TCE-SP, TCE-MG, TCE-BA, TCE-RJ). Fase 3 entra em municípios
          via Querido Diário, começando com cinco cidades-piloto e
          alimentação escolar.
        </p>
      </Section>

      <Section title="Quem deve nos cobrar">
        <p>
          Jornalistas que cobrem controle público. Vereadores que precisam
          fiscalizar prefeitos. Servidores de tribunais de contas que fazem
          triagem. Cidadãos que querem saber quanto a sua prefeitura pagou
          pela merenda da escola do filho. Pesquisadores que precisam de
          dados reprodutíveis. Esta plataforma é para vocês — e contra
          ninguém em particular.
        </p>
      </Section>

      <Section title="Sobre dados pessoais — postura LGPD">
        <p>
          Tratamos exclusivamente <strong>dados públicos</strong> publicados
          pelos próprios órgãos de controle (TCE-PR, Compras.gov.br) — base
          legal: cumprimento de obrigação legal (LAI 12.527/2011 + Lei
          Complementar 131/2009) e interesse legítimo de monitoramento de
          gasto público. Não coletamos cookies de rastreamento, não
          desmascaramos CPFs que o TCE já mascarou, e respeitamos
          guardrails de exposição (perfil de fornecedor só com ≥ 5
          contratos, <code>noindex</code>, sem ranking acusatório, etc).
        </p>
        <p>
          Detalhamento completo, base legal por categoria de dado, prazo
          de retenção e canal para exercer os direitos do art. 18 LGPD em{" "}
          <a
            href="https://github.com/inteligateegastorres/Quanto-Pagou/blob/main/data/PRIVACY.md"
            target="_blank"
            rel="noreferrer"
          >
            data/PRIVACY.md
          </a>
          . <strong>v1 — pendente revisão jurídica antes do go-live público</strong>;
          mudanças relevantes ficam no changelog do PLANO.
        </p>
      </Section>

      <footer className="pt-6 border-t border-line text-sm text-muted space-y-2">
        <p>
          <Link href="/metodologia">Metodologia</Link> ·{" "}
          <Link href="/insight/diesel-ministerios">Insight da semana</Link> ·{" "}
          <Link href="/correcoes">Correções</Link>
        </p>
        <p>
          Quanto Pagou é mantido coletivamente. Quem quiser contribuir tem o
          repositório aberto. Quem encontrar erro tem o botão de reportar em
          cada item. Quem quiser receber um boletim semanal com os
          comparativos automáticos terá o formulário aqui assim que estiver
          pronto.
        </p>
      </footer>
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
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">{title}</h2>
      <div className="space-y-3">{children}</div>
    </section>
  );
}
