# AGENTS.md - Buti & Bita Financials

## Workspace Obrigatorio

O workspace correto deste projeto e:

```text
C:\Users\Togszera\Desktop\buti-bitafinancials
```

Antes de qualquer leitura, edicao, teste, commit ou push, confirme que o comando esta rodando nesse diretorio.

## Stack Do Projeto

- App PWA em HTML, CSS e JavaScript vanilla, concentrado em `index.html`.
- Service Worker externo em `sw.js`.
- Supabase para Auth, PostgreSQL, Edge Functions e push notifications.
- Testes Node.js com `node:test` em `unit/` e `e2e/ui.test.js`.
- Testes Playwright Python em `e2e/playwright_*.py`, dependentes de `e2e/config.py`.

## Fluxo Obrigatorio De Desenvolvimento

Toda mudanca de desenvolvimento deve seguir esta ordem:

1. `senior-dev`
   - Sempre usar para ajustes, melhorias, bugs, ideias novas, funcionalidades novas e qualquer trabalho de desenvolvimento.
   - Implementa a mudanca com escopo pequeno, sem over-engineering e seguindo o padrao existente.

2. `code-reviewer`
   - Entra logo apos o `senior-dev`.
   - Faz revisao minuciosa das alteracoes, procurando regressao, bug, risco, quebra de fluxo e ausencia de cobertura.
   - Corrige o que for necessario antes de passar para QA.

3. `qa-senior`
   - Faz analise de impacto da mudanca.
   - Define casos de teste manuais, regressivos e automatizados conforme o impacto.
   - Se a mudanca toca algo existente, testes regressivos sao obrigatorios.

4. `qa-automate`
   - Cria ou ajusta testes automatizados a partir dos casos definidos pelo `qa-senior`.
   - Mantem os testes simples, executaveis localmente e alinhados ao app sem build step.

5. Validacao final
   - Rodar testes automatizados.
   - Revisar `git diff`.
   - Confirmar que nao entrou alteracao fora do escopo.

6. Git
   - Trabalhar sempre a partir de `develop`.
   - Nunca fazer push direto para `main`.
   - Fazer staging apenas dos arquivos revisados e pertencentes ao escopo.
   - Rodar `git diff --cached` antes de commitar.
   - Quando tudo estiver ok, fazer commit, push para `develop` e abrir ou atualizar PR `develop -> main` para aprovacao do usuario.

Se algum agent formal nao existir na sessao, simule a funcao como etapa explicita no proprio Codex e registre isso no resumo final. Quando houver ferramenta de subagents disponivel, usar subagents com esses papeis no prompt.

## Testes No Windows

No PowerShell, nao use `npm test`, porque `npm.ps1` pode ser bloqueado pela ExecutionPolicy.

Use um destes comandos:

```powershell
.\test.cmd
npm.cmd test
```

`test.cmd` e o caminho preferencial para evitar falhas de policy no Windows.

## Browser E ERR_BLOCKED_BY_CLIENT

Para este projeto, priorize testes automatizados locais e inspecoes estaticas.

Nao usar Browser para `file://`, `localhost` ou `127.0.0.1`, salvo pedido explicito do usuario. Se o usuario pedir Browser e aparecer `ERR_BLOCKED_BY_CLIENT`, pare imediatamente a tentativa visual e substitua por testes automatizados/estaticos.

## Arquivos Sensiveis

Nao versionar:

- `CONTEXT.md`
- `SECURITY.md`
- `e2e/config.py`
- `.env*`

Esses arquivos podem conter contexto privado, credenciais, rotas locais ou dados sensiveis.

## Service Worker

Incrementar `CACHE_NAME` em `sw.js` quando houver deploy com mudancas em HTML/CSS/JS.
