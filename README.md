# 💰 Buti & Bita Financials

PWA de controle financeiro pessoal com sincronização em tempo real.

---

## O que faz

- Painel com resumo mensal, alertas de vencimento e saldo estimado
- Cadastro e acompanhamento de contas fixas, financiamentos e assinaturas
- Ícone personalizável por conta (na criação e na edição)
- Marcação de contas pagas com identificação de quem pagou
- Registro de gastos avulsos por categoria e por usuário
- Histórico mensal com extrato completo
- Sincronização em tempo real entre dispositivos via banco de dados na nuvem
- Login individual com tema e perfil automático por usuário
- Notificações locais para contas próximas do vencimento

---

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Frontend | HTML5 + CSS3 + JavaScript vanilla |
| Banco de dados | Supabase (PostgreSQL) |
| Fonte | Geist (Google Fonts) |
| PWA | Service Worker (`sw.js`) |
| Testes unitários | Node.js `node:test` |
| Testes E2E | Playwright + Python |

---

## Estrutura

```
.
├── index.html                        # App completo
├── sw.js                             # Service Worker (obrigatório para PWA)
├── README.md
├── package.json
├── unit/
│   ├── helpers.test.js               # Funções puras
│   └── supabase.test.js              # Wrappers de API
└── e2e/
    ├── playwright_tests.py           # Testes de UI
    ├── playwright_auth_tests.py      # Testes de autenticação
    ├── playwright_features_tests.py  # Testes de novas funcionalidades
    └── config.py.example             # Template de configuração (copiar para config.py)
```

---

## Instalação no celular

O banner de instalação só aparece quando o app é acessado via **HTTPS** — não funciona em `file://` local. Use o link do GitHub Pages.

**Android:** Chrome → menu ⋮ → "Adicionar à tela inicial"

**iPhone:** Safari → compartilhar □↑ → "Adicionar à Tela de Início"

O app aparece na tela inicial como **Buti&Bita**.

---

## Notificações

As notificações alertam sobre contas que vencem no dia ou em até 3 dias. Para ativar:

1. Acesse o app via HTTPS (GitHub Pages)
2. Vá em **Configuração → ativar o toggle de notificações**
3. Aceite a permissão quando o browser perguntar

> Notificações só funcionam com o app aberto. Para receber alertas com o app fechado seria necessário um servidor de push — não implementado.

---

## Testes

### Pré-requisitos

- Node.js v18+
- Python 3.8+
- `pip install playwright && python -m playwright install chromium`

### Configuração dos testes E2E

Copie o arquivo de configuração e preencha com seus dados:

```bash
cp e2e/config.py.example e2e/config.py
```

Edite `e2e/config.py` com o caminho local do HTML e os dados dos usuários de teste.

### Unitários e integração

```bash
node --test unit/helpers.test.js unit/supabase.test.js
```

### E2E — UI

```bash
python e2e/playwright_tests.py
```

### E2E — Autenticação

```bash
python e2e/playwright_auth_tests.py
```

### E2E — Novas funcionalidades

```bash
python e2e/playwright_features_tests.py
```

Para ver o browser abrindo em qualquer suite, localize `chromium.launch` e troque `headless=True` por `headless=False, slow_mo=600`.

### Resultado esperado

| Suite | Arquivo | Testes |
|-------|---------|--------|
| Unitários | `unit/helpers.test.js` + `supabase.test.js` | 73 |
| E2E UI | `playwright_tests.py` | 48 |
| E2E Auth | `playwright_auth_tests.py` | 37 |
| E2E Features | `playwright_features_tests.py` | 18 |
| **Total** | | **176** |

---

*Buti & Bita 💚💜*