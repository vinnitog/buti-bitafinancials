# 💰 Buti & Bita Financials

PWA de controle financeiro pessoal com sincronização em tempo real.

---

## O que faz

- Painel com resumo mensal, alertas de vencimento e saldo estimado
- Vencimentos próximos filtrados por status — contas pagas somem automaticamente da lista
- Cadastro e acompanhamento de contas fixas, financiamentos e assinaturas
- Ícone personalizável por conta (na criação e na edição)
- Exclusão de contas (soft delete — histórico preservado) e gastos avulsos
- Marcação de contas pagas com identificação de quem pagou ou editou por último
- Registro de gastos avulsos por categoria e por usuário
- Múltiplas entradas de renda por mês — o painel soma tudo e exibe total por pessoa e do casal
- Histórico mensal com extrato completo
- Sincronização em tempo real entre dispositivos via banco de dados na nuvem
- Login individual com tema e perfil automático por usuário
- **Push notifications reais** — alertas às 8h (3 dias antes) e às 8h + 12h (no dia do vencimento), mesmo com o app fechado

---

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Frontend | HTML5 + CSS3 + JavaScript vanilla |
| Banco de dados | Supabase (PostgreSQL) |
| Push notifications | Web Push API + VAPID + Supabase Edge Functions + pg_cron |
| Fonte | Geist (Google Fonts) |
| PWA | Service Worker (`sw.js`) |
| Testes unitários | Node.js `node:test` |
| Testes E2E | Playwright + Python |

---

## Estrutura

```
.
├── index.html                          # App completo
├── sw.js                               # Service Worker
├── README.md
├── package.json
├── supabase/
│   └── functions/
│       └── send-push/
│           └── index.ts               # Edge Function de push notifications
├── unit/
│   ├── helpers.test.js
│   └── supabase.test.js
└── e2e/
    ├── playwright_tests.py
    ├── playwright_auth_tests.py
    ├── playwright_features_tests.py
    └── config.py.example
```

---

## Instalação no celular

O banner de instalação só aparece quando o app é acessado via **HTTPS**.

**Android:** Chrome → menu ⋮ → "Adicionar à tela inicial"

**iPhone:** Safari → compartilhar □↑ → "Adicionar à Tela de Início"

O app aparece na tela inicial como **Buti&Bita**.

---

## Push Notifications

### Como funciona

```
pg_cron (8h / 12h BRT)
  → Edge Function send-push
    → consulta contas + pagamentos no Supabase
    → identifica vencimentos não pagos
    → Web Push API → celular de Buti / Bita
```

- **Aviso 3 dias antes** — push às 8h quando faltar exatamente 3 dias para o vencimento
- **Alerta no dia** — push às 8h e ao meio-dia na data de vencer

### Configuração (uma vez)

**1. Criar tabela no Supabase** (SQL Editor):

```sql
CREATE TABLE IF NOT EXISTS push_subscriptions (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  p256dh TEXT NOT NULL,
  auth TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, endpoint)
);
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "usuario_propria_subscription" ON push_subscriptions
  FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
```

**2. Configurar secrets na Edge Function** (Supabase → Settings → Edge Functions → Secrets):

```
VAPID_PUBLIC_KEY   = BOD5s2bqEehGCP6HlP3K6gGDz-...
VAPID_PRIVATE_KEY  = Db1KzlZPkVnJGmYQKJ1646hL...
VAPID_SUBJECT      = mailto:seu@email.com
```

**3. Deploy da Edge Function:**

```bash
supabase functions deploy send-push --no-verify-jwt
```

**4. Agendar com pg_cron** (SQL Editor — substitua `SERVICE_ROLE_KEY`):

```sql
SELECT cron.schedule('push-3dias', '0 11 * * *',
  $$SELECT net.http_post(url:='https://SEU_PROJETO.supabase.co/functions/v1/send-push',
    headers:='{"Content-Type":"application/json","Authorization":"Bearer SERVICE_ROLE_KEY"}'::jsonb,
    body:='{"tipo":"3dias"}'::jsonb)$$);

SELECT cron.schedule('push-hoje-8h', '0 11 * * *',
  $$SELECT net.http_post(url:='https://SEU_PROJETO.supabase.co/functions/v1/send-push',
    headers:='{"Content-Type":"application/json","Authorization":"Bearer SERVICE_ROLE_KEY"}'::jsonb,
    body:='{"tipo":"hoje_8h"}'::jsonb)$$);

SELECT cron.schedule('push-hoje-12h', '0 15 * * *',
  $$SELECT net.http_post(url:='https://SEU_PROJETO.supabase.co/functions/v1/send-push',
    headers:='{"Content-Type":"application/json","Authorization":"Bearer SERVICE_ROLE_KEY"}'::jsonb,
    body:='{"tipo":"hoje_12h"}'::jsonb)$$);
```

**5. Ativar no app:** Configuração → Push notifications → ativar toggle → aceitar permissão

---

## Entradas de renda

Na aba **+ Novo → Entradas do mês** registre múltiplas entradas (adiantamento, salário, bônus) para Buti e Bita. O painel soma tudo automaticamente.

---

## Notificações

Para ativar push notifications reais (funciona com app fechado):
1. Acesse via HTTPS (GitHub Pages)
2. **Configuração → Push notifications → ativar toggle**
3. Aceite a permissão no browser

---

## Testes

### Pré-requisitos

- Node.js v18+
- Python 3.8+
- `pip install playwright && python -m playwright install chromium`

### Configuração dos testes E2E

```bash
cp e2e/config.py.example e2e/config.py
# Edite config.py com o caminho local e dados dos usuários
```

### Comandos

```bash
# Unitários
node --test unit/helpers.test.js unit/supabase.test.js

# E2E — UI
python e2e/playwright_tests.py

# E2E — Autenticação
python e2e/playwright_auth_tests.py

# E2E — Funcionalidades
python e2e/playwright_features_tests.py
```

`headless=False, slow_mo=600` em `chromium.launch` para ver o browser abrindo.

### Resultado esperado

| Suite | Testes |
|-------|--------|
| Unitários | 73 |
| E2E UI | 48 |
| E2E Auth | 37 |
| E2E Features | 37 |
| E2E Entradas + Push | 24 |
| **Total** | **219** |

---

*Buti & Bita 💚💜*