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
  const testCmd = read('test.cmd');

  test('AGENTS.md pins workspace and workflow order', () => {
    assert.match(agents, /C:\\Users\\Togszera\\Desktop\\buti-bitafinancials/);
    assertOrdered(agents, ['senior-dev', 'code-reviewer', 'qa-senior', 'qa-automate'], 'AGENTS.md');
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
});
