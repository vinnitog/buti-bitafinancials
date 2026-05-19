# PROJECT_CONTEXT.md - Buti & Bita Financials

## O Que E

PWA de controle financeiro pessoal para Buti e Bita, com dashboard mensal, contas fixas, gastos avulsos, entradas de renda, historico mensal, sincronizacao Supabase e push notifications.

## Stack Publica

| Camada | Tecnologia |
| --- | --- |
| Frontend | HTML, CSS e JavaScript vanilla em `index.html` |
| PWA | `sw.js` |
| Backend | Supabase Auth, PostgreSQL e Edge Functions |
| Push | Web Push API, VAPID e Supabase Edge Function `send-push` |
| Testes | Node.js `node:test` e Playwright Python local |
| Deploy | GitHub Pages |

## Estrutura Principal

```text
index.html
sw.js
package.json
unit/
e2e/
supabase/functions/send-push/
```

## Contexto Sensivel

`CONTEXT.md`, `SECURITY.md` e `e2e/config.py` ficam fora do Git por poderem conter dados privados, rotas locais, credenciais ou detalhes operacionais sensiveis.

## Workflow

Seguir o workflow definido em `AGENTS.md`.

Para front-end, usar `ui-ux-expert` logo apos `senior-dev` quando houver impacto visual/UX.
