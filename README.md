# 💰 Buti & Bita Financials

PWA de controle financeiro pessoal com sincronização em tempo real.

---

## O que faz

- Painel com resumo mensal, alertas de vencimento e saldo estimado
- Cadastro e acompanhamento de contas fixas, financiamentos e assinaturas
- Marcação de contas pagas com identificação por usuário
- Registro de gastos avulsos por categoria
- Histórico mensal com extrato completo
- Sincronização em tempo real entre dispositivos via banco de dados na nuvem
- Login individual com perfil automático por usuário

---

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Frontend | HTML5 + CSS3 + JavaScript vanilla |
| Banco de dados | Supabase (PostgreSQL) |
| Fonte | Geist (Google Fonts) |
| PWA | Service Worker |
| Testes unitários | Node.js `node:test` |
| Testes E2E | Playwright + Python |

---

## Estrutura

```
.
├── financeiro-pessoal.html       # App completo
├── README.md
├── package.json
├── unit/
│   ├── helpers.test.js           # Funções puras
│   └── supabase.test.js          # Wrappers de API
└── e2e/
    ├── playwright_tests.py       # Testes de UI
    └── playwright_auth_tests.py  # Testes de autenticação
```

---

## Instalação no celular

**Android:** Chrome → menu ⋮ → "Adicionar à tela inicial"

**iPhone:** Safari → compartilhar □↑ → "Adicionar à Tela de Início"

---

## Testes

### Pré-requisitos

- Node.js v18+
- Python 3.8+
- `pip install playwright && python -m playwright install chromium`

### Unitários e integração

```bash
node --test unit/helpers.test.js unit/supabase.test.js
```

### E2E — UI

Ajuste `APP_PATH` no arquivo para o caminho local do HTML, depois:

```bash
python e2e/playwright_tests.py
```

### E2E — Autenticação

```bash
python e2e/playwright_auth_tests.py
```

Para ver o browser abrindo, localize `chromium.launch` nos arquivos e troque `headless=True` por `headless=False, slow_mo=600`.

### Resultado esperado

| Suite | Testes |
|-------|--------|
| Unitários | 73 |
| E2E UI | 48 |
| E2E Auth | 37 |
| **Total** | **158** |

---

*Buti & Bita 💚💜*