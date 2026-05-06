# Deploy — Quanto Pagou

> **Status:** este documento é o **plano de deploy para a Fase 0.5
> pública**. Nenhuma infra real foi provisionada ainda — a primeira leva
> de ações (domínio, contas, secrets) precisa do usuário humano. Este
> arquivo descreve a ordem de operações e as decisões de stack já
> validadas no PLANO.md §11.

## Stack

| Camada | Provedor | Por quê |
|---|---|---|
| Frontend (Next.js 16) | **Vercel** | Suporte nativo a App Router + `next/og`; preview por PR; CDN incluso. |
| API (FastAPI) | **Fly.io** ou **Railway** | FastAPI não é serverless-first; um worker pequeno (256MB) atende Fase 0.5 com folga. Fly tem Postgres co-localizado se um dia quisermos sair do Supabase. |
| Postgres | **Supabase** | Backup automático, painel SQL, free tier de 500MB cobre Fase 0.5; schema é só `raw.*` + `analytics.*`. |
| Object storage (snapshots) | **Cloudflare R2** | Egress zerado (importante para dump público em Parquet/HuggingFace na Fase 1). |
| Ingestão programada | **GitHub Actions cron** | Semanal, simples; dispara `python -m ingest` + `python -m analytics.build_marts` contra o Postgres de produção. Migra para Airflow só na Fase 3+. |
| E-mail/boletim | **Buttondown** ou **Resend** | Free tier; integra com formulário no `/` e digest semanal. |
| Monitoramento | **Sentry** + **Plausible** | Free tier ambos; sem cookie de tracking. |

Custo total Fase 0.5: **US$ 0/mês** (todos free tiers). Fase 1 estima
~US$ 15/mês quando o boletim cresce e R2 começa a cobrar.

## Pré-requisitos (ações do usuário humano)

Coisas que Claude **não pode fazer sozinho** porque envolvem cadastro
em provedor externo, cartão de crédito, ou decisão de domínio:

1. **Domínio.** Registrar `quantopagou.org` (preferido) ou `.com.br`. Aponta
   `A`/`CNAME` para Vercel quando for hora.
2. **Organização GitHub.** Criar `quanto-pagou` (ou similar). Mover este
   repo para lá (mantém histórico). Adicionar CODEOWNERS, branch protection
   em `main`, secrets de CI (ver lista abaixo).
3. **Conta Vercel** vinculada à org GitHub. Importar o repositório,
   apontar o **root** para `frontend/` no project settings. Auto-deploy
   por push em `main`.
4. **Projeto Supabase** novo. Plano gratuito. Anotar `DATABASE_URL`
   (formato `postgresql://...:6543/postgres` para o pgbouncer transaction
   mode).
5. **Conta Cloudflare** com bucket R2 chamado `quantopagou-snapshots`.
   Gerar API token com `Object Read & Write` no bucket.
6. **App de e-mail (Buttondown ou Resend)** para o formulário de boletim.
   Anotar API key + endpoint do formulário público.
7. **Conta Sentry** + DSN para frontend e backend.
8. **Conta Fly.io** ou **Railway** para o worker FastAPI.
9. **Revisão jurídica preliminar** do manifesto + página de fornecedor
   antes de o site ir ao ar com SEO. Para Fase 0.5 pode rodar `noindex`.

## Variáveis de ambiente (produção)

`.env.production.example` foi adicionado ao repo. Copiar e preencher
nos painéis de cada provedor — **não commitar** valores reais.

| Variável | Onde configura | Exemplo |
|---|---|---|
| `DATABASE_URL` | Vercel (via integration), Fly, GH Actions | `postgresql://postgres:...@aws-0-us-east-1.pooler.supabase.com:6543/postgres` |
| `COMPRAS_API_BASE` | Fly, GH Actions | `https://dadosabertos.compras.gov.br` (default) |
| `SNAPSHOTS_DIR` | Fly | `/data/snapshots` (volume montado) |
| `LOG_LEVEL` | Fly | `INFO` |
| `R2_ACCESS_KEY_ID` | Fly, GH Actions | (Cloudflare) |
| `R2_SECRET_ACCESS_KEY` | Fly, GH Actions | (Cloudflare) |
| `R2_BUCKET` | Fly, GH Actions | `quantopagou-snapshots` |
| `R2_ENDPOINT` | Fly, GH Actions | `https://<acct>.r2.cloudflarestorage.com` |
| `QUANTOPAGOU_API_BASE` | Vercel | `https://api.quantopagou.org` |
| `NEXT_PUBLIC_SITE_URL` | Vercel | `https://quantopagou.org` |
| `BUTTONDOWN_API_KEY` | Vercel server actions (Fase 1) | (Buttondown) |
| `SENTRY_DSN_API` | Fly | (Sentry) |
| `NEXT_PUBLIC_SENTRY_DSN` | Vercel | (Sentry) |

GitHub Actions secrets necessários para o cron de ingestão:

- `DATABASE_URL`
- `R2_*` (4 variáveis acima)
- `COMPRAS_API_BASE` (opcional)

## Ordem de operações para o go-live da Fase 0.5

Cada item é independente do seguinte exceto onde marcado **(bloqueia)**:

1. Provisionar Supabase. Aplicar `sql/000_init.sql`, `sql/001_analytics.sql`,
   `sql/002_resilience.sql` na ordem via painel SQL do Supabase. **(bloqueia)**
2. Criar bucket R2 + API token. Não há schema a aplicar.
3. Provisionar Fly.io/Railway com a imagem do worker FastAPI:

   ```bash
   # frontend/.env.production.local (Vercel UI cuida disso, NUNCA commitar)
   QUANTOPAGOU_API_BASE=https://api.quantopagou.org
   ```

   Worker roda `uvicorn api.main:app --host 0.0.0.0 --port 8080`.
   Apontar healthcheck de `/health`. Dimensionamento: 1 instância 256MB.
4. Configurar Vercel project com root em `frontend/`. Definir env vars.
   Apontar domain. Enable preview deployments.
5. Configurar GH Actions cron (`.github/workflows/ingest-weekly.yml` —
   ainda não existe, ver template abaixo). Trigger semanal.
6. Primeira ingestão de produção: rodar manualmente via `gh workflow run
   ingest-weekly.yml` para validar que o pipeline completa e os marts são
   refrescados.
7. Smoke test final (checklist abaixo).
8. Anunciar em 3 newsletters (Abraji, Escola de Dados, Núcleo) + Twitter
   + Bluesky com OG image apontando para `/insight/diesel-ministerios`.

## Template do GitHub Actions cron

`.github/workflows/ingest-weekly.yml` (a criar quando os secrets
estiverem prontos):

```yaml
name: ingest-weekly
on:
  schedule:
    - cron: "0 6 * * 3"  # quartas, 06:00 UTC
  workflow_dispatch:

jobs:
  ingest:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      COMPRAS_API_BASE: https://dadosabertos.compras.gov.br
      SNAPSHOTS_DIR: ./snapshots
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install uv
      - run: python -m uv sync
      - name: ingest janela ultimos 7 dias
        run: bash scripts/sync_compras.sh
      - name: upload snapshots para R2
        run: |
          # rclone ou aws s3 cli configurado com endpoint R2
          aws s3 sync ./snapshots s3://${{ secrets.R2_BUCKET }}/snapshots/ \
            --endpoint-url ${{ secrets.R2_ENDPOINT }}
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.R2_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.R2_SECRET_ACCESS_KEY }}
```

Este template assume `sync_compras.sh` rodando contra o `DATABASE_URL`
de produção. Em caso de falha total da API Compras, o workflow termina
com exit 2 (parcial) ou exit 0 (total) — ver `scripts/sync_compras.sh`.

## Checklist do smoke test pós-deploy

Bater nas 7 rotas e validar cada uma:

```bash
SITE=https://quantopagou.org
API=https://api.quantopagou.org

curl -fsSI $API/health | head -1                    # 200
curl -fs $API/health | jq .                         # status:ok + counts > 0
curl -fsSI $SITE/                                   # 200
curl -fsSI $SITE/manifesto                          # 200
curl -fsSI $SITE/insight/diesel-ministerios         # 200
curl -fsSI $SITE/metodologia                        # 200
curl -fsSI $SITE/correcoes                          # 200
curl -fsSI $SITE/opengraph-image                    # 200, Content-Type: image/png
curl -fsSI $SITE/insight/diesel-ministerios/opengraph-image  # 200 PNG
```

E validar visualmente no Twitter Card Validator (cards.dev.twitter.com)
e no Facebook Sharing Debugger que as OGs renderizam.

## Rollback

Vercel: rollback instantâneo via UI (cada deploy fica preservado).
Supabase: snapshot diário no plano gratuito. Para recuperar, restore
via painel + re-rodar `python -m analytics.build_marts` para refrescar
materialized views.
Fly/Railway: `fly deploy --image <previous-tag>`.
GH Actions cron: pausar via `gh workflow disable ingest-weekly.yml`.

## O que NÃO fazer no go-live da Fase 0.5

- **Não habilitar SEO público** (`noindex` no `/fornecedor/*` no mínimo) até
  revisão jurídica confirmar que a linguagem factual + modal "como
  interpretar" cobrem o risco de difamação.
- **Não prometer cadência editorial.** A esteira automática é semanal,
  irregular. Manifesto e formulário do boletim já refletem isso.
- **Não esconder o status de demonstração** enquanto a fixture sintética
  estiver em uso. O banner de "Modo demonstração" no layout precisa
  ficar até a primeira ingestão real do Compras.gov.br consolidar marts
  com volume mínimo (~50 itens/cluster).
