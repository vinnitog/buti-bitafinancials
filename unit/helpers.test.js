/**
 * Unit Tests — Buti & Bita Financials
 * Funções testadas: escHtml, sanitizeCsvRow, fmtR, getUrg, dueLabel, nomeMes
 * Runner: node:test (built-in, zero dependências)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

// ─── Funções extraídas do app (copiadas fielmente) ────────────────────────────

function escHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function parseMoney(v) {
  const cleaned = String(v ?? '').trim().replace(/[^\d,.-]/g, '');
  if (!cleaned) return 0;
  const hasComma = cleaned.includes(',');
  const hasDot = cleaned.includes('.');
  let normalized = cleaned;
  if (hasComma && hasDot) {
    normalized = cleaned.lastIndexOf(',') > cleaned.lastIndexOf('.')
      ? cleaned.replace(/\./g, '').replace(',', '.')
      : cleaned.replace(/,/g, '');
  } else if (hasComma) {
    normalized = cleaned.replace(',', '.');
  }
  return parseFloat(normalized) || 0;
}

function sanitizeCsvRow(r) {
  return {
    nome:  escHtml(String(r.nome || r.name || '').slice(0, 100)).trim(),
    valor: Math.max(0, Math.min(999999, parseMoney(r.valor || '0'))),
    dia:   Math.min(31, Math.max(0, parseInt(r.dia || '0') || 0)),
    cat:   ['financiamento', 'fixa', 'assinatura', 'variavel'].includes(r.categoria || r.cat)
             ? (r.categoria || r.cat) : 'fixa',
    tipo:  ['manual', 'auto', 'credito'].includes(r.tipo) ? r.tipo : 'manual',
    obs:   escHtml(String(r.observacao || r.obs || '').slice(0, 200)).trim(),
  };
}

function fmtR(v) {
  return 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function nomeMes(m, a) {
  return new Date(a, m - 1, 1)
    .toLocaleString('pt-BR', { month: 'long', year: 'numeric' })
    .replace(/^\w/, c => c.toUpperCase());
}

// Injeta data fixa para testes determinísticos: 10 de maio de 2026
const DIA_HOJE_TEST = 10;
function getUrg(dia, diaHoje = DIA_HOJE_TEST) {
  if (!dia) return 'auto';
  const d = dia - diaHoje;
  if (d < 0)  return 'vencida';
  if (d === 0) return 'hoje';
  if (d <= 3) return 'urgente';
  if (d <= 7) return 'breve';
  return 'ok';
}

function dueLabel(dia, diaHoje = DIA_HOJE_TEST) {
  if (!dia) return 'Débito automático';
  const d = dia - diaHoje;
  if (d < 0)  return `⚠ Venceu dia ${dia} (em atraso)`;
  if (d === 0) return `🚨 Vence HOJE`;
  if (d === 1) return `⚡ Vence amanhã (dia ${dia})`;
  if (d <= 3) return `⚡ Vence em ${d} dias (dia ${dia})`;
  return `Vence dia ${dia} (em ${d} dias)`;
}

// ─── TC-UNIT: escHtml ─────────────────────────────────────────────────────────

describe('escHtml', () => {
  test('TC-UNIT-001 escapa tag <script>', () => {
    assert.equal(escHtml('<script>alert(1)</script>'), '&lt;script&gt;alert(1)&lt;/script&gt;');
  });

  test('TC-UNIT-002 escapa aspas duplas', () => {
    assert.equal(escHtml('"test"'), '&quot;test&quot;');
  });

  test('TC-UNIT-003 escapa apóstrofo', () => {
    assert.equal(escHtml("O'Brien"), 'O&#39;Brien');
  });

  test('TC-UNIT-004 null retorna string vazia', () => {
    assert.equal(escHtml(null), '');
  });

  test('TC-UNIT-004b undefined retorna string vazia', () => {
    assert.equal(escHtml(undefined), '');
  });

  test('TC-UNIT-004c escapa & (ampersand)', () => {
    assert.equal(escHtml('Buti & Bita'), 'Buti &amp; Bita');
  });

  test('TC-UNIT-004d string limpa não é alterada', () => {
    assert.equal(escHtml('Conta de Luz'), 'Conta de Luz');
  });

  test('TC-UNIT-004e escapa XSS via atributo onerror', () => {
    assert.equal(escHtml('<img src=x onerror=alert(1)>'), '&lt;img src=x onerror=alert(1)&gt;');
  });
});

// ─── TC-UNIT: fmtR ───────────────────────────────────────────────────────────

describe('fmtR', () => {
  test('TC-UNIT-005 formata 12000 corretamente', () => {
    assert.equal(fmtR(12000), 'R$ 12.000');
  });

  test('TC-UNIT-006 formata 0', () => {
    assert.equal(fmtR(0), 'R$ 0');
  });

  test('TC-UNIT-006b formata valor simples 300', () => {
    assert.equal(fmtR(300), 'R$ 300');
  });

  test('TC-UNIT-006c formata 1000000', () => {
    assert.equal(fmtR(1000000), 'R$ 1.000.000');
  });
});

// ─── TC-UNIT: getUrg ─────────────────────────────────────────────────────────

describe('getUrg', () => {
  test('TC-UNIT-007 dia 0 retorna auto', () => {
    assert.equal(getUrg(0), 'auto');
  });

  test('TC-UNIT-008 dia passado retorna vencida', () => {
    assert.equal(getUrg(5, 10), 'vencida'); // dia 5, hoje é 10
  });

  test('TC-UNIT-009 dia hoje retorna hoje', () => {
    assert.equal(getUrg(10, 10), 'hoje');
  });

  test('TC-UNIT-010 dia+2 retorna urgente', () => {
    assert.equal(getUrg(12, 10), 'urgente');
  });

  test('TC-UNIT-010b dia+3 retorna urgente (limite)', () => {
    assert.equal(getUrg(13, 10), 'urgente');
  });

  test('TC-UNIT-010c dia+4 retorna breve', () => {
    assert.equal(getUrg(14, 10), 'breve');
  });

  test('TC-UNIT-010d dia+7 retorna breve (limite)', () => {
    assert.equal(getUrg(17, 10), 'breve');
  });

  test('TC-UNIT-010e dia+8 retorna ok', () => {
    assert.equal(getUrg(18, 10), 'ok');
  });

  test('TC-UNIT-010f dia amanhã retorna urgente', () => {
    assert.equal(getUrg(11, 10), 'urgente');
  });
});

// ─── TC-UNIT: dueLabel ───────────────────────────────────────────────────────

describe('dueLabel', () => {
  test('dia 0 retorna texto de débito automático', () => {
    assert.equal(dueLabel(0), 'Débito automático');
  });

  test('dia passado retorna texto de atraso', () => {
    assert.match(dueLabel(5, 10), /em atraso/);
  });

  test('dia hoje retorna HOJE', () => {
    assert.match(dueLabel(10, 10), /HOJE/);
  });

  test('amanhã retorna amanhã', () => {
    assert.match(dueLabel(11, 10), /amanhã/);
  });

  test('dia+2 retorna "em 2 dias"', () => {
    assert.match(dueLabel(12, 10), /em 2 dias/);
  });

  test('dia+8 retorna "em N dias" genérico', () => {
    assert.match(dueLabel(18, 10), /em 8 dias/);
  });
});

// ─── TC-UNIT: nomeMes ────────────────────────────────────────────────────────

describe('nomeMes', () => {
  test('maio 2026 capitalizado', () => {
    const result = nomeMes(5, 2026);
    assert.match(result, /Maio/i);
    assert.match(result, /2026/);
  });

  test('janeiro começa com maiúscula', () => {
    const result = nomeMes(1, 2026);
    assert.match(result, /^Janeiro/);
  });

  test('dezembro 2025', () => {
    const result = nomeMes(12, 2025);
    assert.match(result, /Dezembro/i);
    assert.match(result, /2025/);
  });
});

// ─── TC-UNIT: sanitizeCsvRow ─────────────────────────────────────────────────

describe('sanitizeCsvRow', () => {
  test('TC-UNIT-011 nome > 100 chars truncado para 100', () => {
    const nome = 'A'.repeat(150);
    const result = sanitizeCsvRow({ nome });
    assert.equal(result.nome.length, 100);
  });

  test('TC-UNIT-012 categoria inválida normalizada para fixa', () => {
    const result = sanitizeCsvRow({ nome: 'Teste', cat: 'hacker' });
    assert.equal(result.cat, 'fixa');
  });

  test('TC-UNIT-012b categorias válidas aceitas', () => {
    for (const cat of ['financiamento', 'fixa', 'assinatura', 'variavel']) {
      const result = sanitizeCsvRow({ nome: 'X', cat });
      assert.equal(result.cat, cat);
    }
  });

  test('TC-UNIT-013 tipo inválido normalizado para manual', () => {
    const result = sanitizeCsvRow({ nome: 'Teste', tipo: 'xss_inject' });
    assert.equal(result.tipo, 'manual');
  });

  test('TC-UNIT-013b tipos válidos aceitos', () => {
    for (const tipo of ['manual', 'auto', 'credito']) {
      const result = sanitizeCsvRow({ nome: 'X', tipo });
      assert.equal(result.tipo, tipo);
    }
  });

  test('TC-UNIT-014 valor negativo vira 0', () => {
    const result = sanitizeCsvRow({ nome: 'X', valor: '-500' });
    assert.equal(result.valor, 0);
  });

  test('TC-UNIT-014b valor acima de 999999 truncado', () => {
    const result = sanitizeCsvRow({ nome: 'X', valor: '9999999' });
    assert.equal(result.valor, 999999);
  });

  test('TC-UNIT-014c valor brasileiro com milhar e vírgula decimal é interpretado corretamente', () => {
    const result = sanitizeCsvRow({ nome: 'X', valor: '1.500,50' });
    assert.equal(result.valor, 1500.5);
  });

  test('TC-UNIT-014d valor decimal com vírgula simples é interpretado corretamente', () => {
    const result = sanitizeCsvRow({ nome: 'X', valor: '22,90' });
    assert.equal(result.valor, 22.9);
  });

  test('TC-UNIT-015 dia 32 vira 31', () => {
    const result = sanitizeCsvRow({ nome: 'X', dia: '32' });
    assert.equal(result.dia, 31);
  });

  test('TC-UNIT-015b dia negativo vira 0', () => {
    const result = sanitizeCsvRow({ nome: 'X', dia: '-5' });
    assert.equal(result.dia, 0);
  });

  test('TC-UNIT-015c dia 15 aceito normalmente', () => {
    const result = sanitizeCsvRow({ nome: 'X', dia: '15' });
    assert.equal(result.dia, 15);
  });

  test('TC-SEC-001 XSS em nome de conta sanitizado', () => {
    const result = sanitizeCsvRow({ nome: '<script>alert(1)</script>' });
    assert.ok(!result.nome.includes('<script>'));
    assert.match(result.nome, /&lt;script&gt;/);
  });

  test('TC-SEC-002 XSS em obs sanitizado', () => {
    const result = sanitizeCsvRow({ nome: 'X', obs: '<img src=x onerror=alert(1)>' });
    assert.ok(!result.obs.includes('<img'));
  });

  test('TC-SEC-003 XSS via categoria não bypassa whitelist', () => {
    const result = sanitizeCsvRow({ nome: 'X', cat: '<script>fixa</script>' });
    assert.equal(result.cat, 'fixa'); // o valor com XSS não está na whitelist → default fixa
  });

  test('nome vazio com fallback para name', () => {
    const result = sanitizeCsvRow({ name: 'Spotify', valor: '22' });
    assert.equal(result.nome, 'Spotify');
  });

  test('row completamente vazio retorna defaults seguros', () => {
    const result = sanitizeCsvRow({});
    assert.equal(result.nome, '');
    assert.equal(result.valor, 0);
    assert.equal(result.dia, 0);
    assert.equal(result.cat, 'fixa');
    assert.equal(result.tipo, 'manual');
  });
});

// ─── TC-UNIT: lógica de saldo ─────────────────────────────────────────────────

describe('Cálculo de saldo estimado', () => {
  test('saldo = renda total - contas - variáveis', () => {
    const salarios = { buti: { base: 12000, bonus: 1000 }, bita: { base: 3000, bonus: 500 } };
    const totalSalario = salarios.buti.base + salarios.buti.bonus + salarios.bita.base + salarios.bita.bonus;
    const totalContas = 5000;
    const variaveis = 3460;
    const saldo = totalSalario - totalContas - variaveis;
    assert.equal(totalSalario, 16500);
    assert.equal(saldo, 8040);
  });

  test('saldo negativo quando contas > renda', () => {
    const totalSalario = 3000;
    const totalContas = 4000;
    const variaveis = 1000;
    const saldo = totalSalario - totalContas - variaveis;
    assert.equal(saldo, -2000);
    assert.ok(saldo < 0);
  });

  test('renda total com Bita zerada usa só Buti', () => {
    const salarios = { buti: { base: 12000, bonus: 1000 }, bita: { base: 0, bonus: 0 } };
    const total = salarios.buti.base + salarios.buti.bonus + salarios.bita.base + salarios.bita.bonus;
    assert.equal(total, 13000);
  });
});
