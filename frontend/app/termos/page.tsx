// LGPD L.6 — Termos de Uso + Licença de Dados (PLANO §18 L.6).
// Cobre: uso pessoal/comercial, atribuição CC-BY 4.0, garantias,
// limitação de responsabilidade, foro. Arquivo canônico da licença:
// LICENSE-DATA na raiz do repo (CC-BY 4.0).

import Link from "next/link";
import type { Metadata } from "next";

export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "Termos de Uso · Quanto Pagou",
  description:
    "Termos de uso da plataforma + licença CC-BY 4.0 dos dados derivados (agregações, perfis, manchetes).",
};

export default function TermosPage() {
  return (
    <article className="space-y-8 max-w-3xl text-sm leading-relaxed">
      <header className="space-y-2">
        <Link href="/" className="text-xs text-muted no-underline">
          ← início
        </Link>
        <h1 className="text-3xl font-semibold tracking-tight">
          Termos de Uso
        </h1>
        <p className="text-xs uppercase tracking-wide text-muted">
          Versão v1 · 2026-05-11 · pendente revisão jurídica antes do go-live
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">1. Aceitação</h2>
        <p>
          Ao acessar o Quanto Pagou (
          <code>quantopagou.org</code> e subdomínios), você concorda com
          estes termos e com a{" "}
          <Link href="/politica-privacidade">Política de Privacidade</Link>.
          Se discordar de qualquer cláusula, não use a plataforma.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">2. O que oferecemos</h2>
        <p>
          O Quanto Pagou é uma <strong>plataforma cívica</strong> que
          consolida e classifica dados públicos de gastos governamentais
          brasileiros (TCE-PR, Compras.gov.br, IBGE), produzindo
          agregações, comparações de preços, manchetes algorítmicas e
          perfis agregados de fornecedor (pessoa jurídica). O serviço é
          gratuito e sem propaganda.
        </p>
        <p>
          <strong>Não somos</strong>: órgão de controle, jornal, banco de
          dados oficial, ou produto comercial. Somos catalisador
          tecnológico do direito à informação (LAI 12.527/2011).
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">3. Licença dos dados</h2>
        <p>
          Os dados derivados (agregações, marts, manchetes, perfis,
          classificações, métricas) são publicados sob{" "}
          <strong>
            <a
              href="https://creativecommons.org/licenses/by/4.0/legalcode.pt"
              target="_blank"
              rel="noreferrer"
            >
              Creative Commons Attribution 4.0 International (CC-BY 4.0)
            </a>
          </strong>
          .
        </p>
        <p>Você PODE:</p>
        <ul className="list-disc ml-6 space-y-1">
          <li>Copiar, redistribuir, adaptar.</li>
          <li>Criar obras derivadas (jornalismo, pesquisa, infográfico).</li>
          <li>Usar para fins <strong>comerciais</strong> e não-comerciais.</li>
        </ul>
        <p>Você DEVE:</p>
        <ul className="list-disc ml-6 space-y-1">
          <li>Atribuir crédito. Exemplo de atribuição mínima:</li>
        </ul>
        <blockquote className="border-l-2 border-line pl-4 italic text-muted">
          Dados derivados de Quanto Pagou (quantopagou.org), CC-BY 4.0, a
          partir de TCE-PR/PIT e Compras.gov.br (dados públicos).
        </blockquote>
        <ul className="list-disc ml-6 space-y-1">
          <li>Fornecer link para a licença e indicar mudanças feitas.</li>
          <li>
            Não aplicar termos legais ou medidas tecnológicas que
            restrinjam outros do que a licença permite.
          </li>
        </ul>
        <p className="text-muted">
          Arquivo canônico da licença:{" "}
          <a
            href="https://github.com/anthropics/quantopagou/blob/main/LICENSE-DATA"
            target="_blank"
            rel="noreferrer"
          >
            LICENSE-DATA
          </a>
          {" "}na raiz do repositório.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">
          4. Dados primários vs derivados
        </h2>
        <p>
          Os <strong>dados primários</strong> (XMLs brutos do TCE-PR, JSON
          do Compras.gov.br) são de <strong>domínio público</strong> sob
          LAI/Lei de Transparência. Esses dados não são licenciados por
          nós — você pode obtê-los diretamente das fontes:
        </p>
        <ul className="list-disc ml-6 space-y-1">
          <li>
            <a
              href="https://pit.tce.pr.gov.br/"
              target="_blank"
              rel="noreferrer"
            >
              pit.tce.pr.gov.br
            </a>
          </li>
          <li>
            <a
              href="https://dadosabertos.compras.gov.br/"
              target="_blank"
              rel="noreferrer"
            >
              dadosabertos.compras.gov.br
            </a>
          </li>
        </ul>
        <p>
          O que licenciamos sob CC-BY 4.0 é o{" "}
          <strong>trabalho derivado</strong>: classificação em clusters,
          normalização de unidades, agregações, identificação de
          discrepâncias, manchetes algorítmicas.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">5. Código-fonte</h2>
        <p>
          O código-fonte é licenciado separadamente sob{" "}
          <a
            href="https://www.gnu.org/licenses/agpl-3.0.html"
            target="_blank"
            rel="noreferrer"
          >
            AGPL-3.0
          </a>
          {" "}(ver{" "}
          <a
            href="https://github.com/anthropics/quantopagou/blob/main/LICENSE"
            target="_blank"
            rel="noreferrer"
          >
            LICENSE
          </a>
          ). Esta página cobre apenas os dados/resultados.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">
          6. Sem garantias · limitação de responsabilidade
        </h2>
        <p>
          OS DADOS SÃO FORNECIDOS{" "}
          <strong>"COMO ESTÃO"</strong>, SEM GARANTIA DE EXATIDÃO,
          COMPLETUDE OU ADEQUAÇÃO A UM FIM ESPECÍFICO. Eventualmente
          haverá erros de extração, classificação, agregação ou
          interpretação.
        </p>
        <p>
          <strong>Antes de uso jornalístico, judicial ou
          administrativo</strong>, verifique contra a fonte primária. Toda
          página tem link "ver fonte" apontando para o ZIP/JSON original.
        </p>
        <p>
          Erros conhecidos são documentados em{" "}
          <Link href="/correcoes">/correcoes</Link>. SLA de correção: 48h
          para fatos verificáveis, 15 dias para pedidos LGPD (art. 19).
        </p>
        <p>
          O Quanto Pagou não responde por decisões tomadas com base nos
          dados aqui apresentados sem verificação contra fonte primária.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">
          7. Direitos do titular (LGPD)
        </h2>
        <p>
          Se você é fornecedor ou titular de dado pessoal mencionado e
          quer exercer direitos do art. 18 LGPD (acesso, correção,
          anonimização, eliminação), use o canal{" "}
          <Link href="/lgpd">/lgpd</Link>. Casos especiais — como
          remoção de perfil de pessoa física ou MEI listado por erro de
          classificação — são tratados via tombstone (LGPD L.1) e
          mascaramento (LGPD L.2).
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">8. Conduta do usuário</h2>
        <p>Você concorda em <strong>não</strong>:</p>
        <ul className="list-disc ml-6 space-y-1">
          <li>
            Usar a plataforma para difamação, perseguição ou ataque
            pessoal contra fornecedores ou agentes públicos. Os dados são
            ponto de partida para análise, não conclusão.
          </li>
          <li>
            Tentar quebrar segurança, fazer scraping abusivo ou
            sobrecarregar a infra de propósito. Use a API documentada com
            rate-limits razoáveis.
          </li>
          <li>
            Republicar dados sem atribuição (cláusula 3).
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">9. Mudanças nestes termos</h2>
        <p>
          Mudanças relevantes geram entrada no{" "}
          <a
            href="https://github.com/anthropics/quantopagou/blob/main/PLANO.md"
            target="_blank"
            rel="noreferrer"
          >
            PLANO.md §14 (changelog)
          </a>
          . Última atualização: 2026-05-11.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">10. Foro</h2>
        <p>
          Eventuais litígios decorrentes destes termos serão resolvidos no
          foro da Comarca de Curitiba, Paraná, salvo disposição legal
          imperativa em contrário.
        </p>
      </section>

      <footer className="text-xs text-muted border-t border-line pt-6 space-y-2">
        <p>
          Links: <Link href="/politica-privacidade">Política de Privacidade</Link>
          {" · "}
          <Link href="/lgpd">Canal LGPD</Link>
          {" · "}
          <Link href="/correcoes">Reportar erro</Link>
          {" · "}
          <Link href="/metodologia">Metodologia</Link>
        </p>
      </footer>
    </article>
  );
}
