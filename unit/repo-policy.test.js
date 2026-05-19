import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');

function read(file) {
  return readFileSync(resolve(root, file), 'utf8');
}

function assertOrdered(content, labels, file) {
  let previous = -1;
  for (const label of labels) {
    const current = content.indexOf(label);
    assert.ok(current > previous, `${file}: expected ${label} after previous workflow step`);
    previous = current;
  }
}

describe('Repo policy', () => {
  const agents = read('AGENTS.md');
  const gitignore = read('.gitignore');
  const packageJson = read('package.json');
  const publicContext = read('PROJECT_CONTEXT.md');
  const testCmd = read('test.cmd');

  test('AGENTS.md pins workspace and workflow order', () => {
    assert.match(agents, /C:\\Users\\Togszera\\Desktop\\buti-bitafinancials/);
    assertOrdered(agents, ['senior-dev', 'ui-ux-expert', 'code-reviewer', 'qa-senior', 'qa-automate'], 'AGENTS.md');
    assert.match(agents, /front-end sempre deve acionar `ui-ux-expert`, mesmo sem `\/ui-ux`/);
    assert.match(agents, /HTML, CSS, layout, componentes, responsividade, acessibilidade visual, microinteracoes ou experiencia do usuario/);
    assert.match(agents, /antes do `code-reviewer`/);
    assert.match(agents, /front-end for puramente logica e sem impacto visual\/UX/);
    assert.match(agents, /Trabalhar sempre a partir de `develop`/);
    assert.match(agents, /Nunca fazer push direto para `main`/);
    assert.match(agents, /git diff --cached/);
    assert.match(agents, /develop -> main/);
  });

  test('AGENTS.md documents local Browser restriction', () => {
    assert.match(agents, /ERR_BLOCKED_BY_CLIENT/);
    assert.match(agents, /file:\/\/|localhost|127\.0\.0\.1/);
    assert.match(agents, /Nao usar Browser/);
  });

  test('.gitignore protects sensitive and local-only files', () => {
    for (const pattern of [
      'CONTEXT.md',
      'SECURITY.md',
      'e2e/config.py',
      '.env',
      'node_modules/',
      '.claude/',
      '.supabase/',
      'supabase/.temp/',
      '*.log',
    ]) {
      assert.match(gitignore, new RegExp(pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')), `.gitignore should include ${pattern}`);
    }
  });

  test('test.cmd avoids npm.ps1 and is wired into npm test coverage', () => {
    assert.match(testCmd, /cd \/d "%~dp0"/);
    assert.doesNotMatch(testCmd, /npm test/);
    assert.match(packageJson, /repo-policy\.test\.js/);
  });

  test('kit reuse and public context are documented', () => {
    assert.match(agents, /Como Aplicar Este Kit Em Novos Projetos/);
    for (const required of ['AGENTS.md', 'test.cmd', 'teste de politica', '.gitignore', 'develop', 'PR `develop -> main`', 'PROJECT_CONTEXT.md']) {
      assert.match(agents, new RegExp(required.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')), `AGENTS.md kit instructions should mention ${required}`);
    }
    assert.match(publicContext, /CONTEXT\.md, `SECURITY\.md` e `e2e\/config\.py` ficam fora do Git|CONTEXT\.md/);
    assert.match(publicContext, /Workflow/);
    assert.match(publicContext, /ui-ux-expert/);
  });
});
