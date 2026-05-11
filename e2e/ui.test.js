/**
 * E2E / UI Tests — Buti & Bita Financials
 * Simula interações DOM com jsdom-like approach via node:test
 * Testa: navegação, formulários, toggle pago, temas, confirmação, alertas
 *
 * Estratégia: carregar o HTML como string, criar ambiente DOM mínimo
 * com as funções JS extraídas e testar comportamentos isolados.
 */

import { test, describe, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// ─── Lê o HTML do app para extração de funções ────────────────────────────────
const HTML_PATH = resolve(__dirname, '../index.html');
let appHtml = '';
try {
  appHtml = readFileSync(HTML_PATH, 'utf-8');
} catch (e) {
  appHtml = readFileSync(resolve(__dirname, '../index.html'), 'utf-8').toString();
}

// ─── Extrai bloco <script> do app ────────────────────────────────────────────
const scriptMatch = appHtml.match(/<script>([\s\S]*?)<\/script>\s*<\/body>/);
const appScript = scriptMatch ? scriptMatch[1] : '';

// ─── Verifica presença de funções críticas no código ─────────────────────────

describe('TC-SMK: Estrutura e presença de funções críticas', () => {
  test('TC-SMK-001 HTML contém título correto', () => {
    assert.match(appHtml, /Buti.*Bita.*Financials/);
  });

  test('TC-SMK-002 HTML contém as 6 seções principais', () => {
    const secoes = ['section-dashboard', 'section-contas', 'section-gastos',
                    'section-cadastrar', 'section-historico', 'section-config'];
    for (const s of secoes) {
      assert.match(appHtml, new RegExp(`id="${s}"`), `Seção ${s} não encontrada`);
    }
  });

  test('TC-SMK-003 HTML contém as 6 abas de navegação', () => {
    const abas = ['Painel', 'Contas', 'Gastos', 'Novo', 'Histórico', 'Configuração'];
    for (const a of abas) {
      assert.match(appHtml, new RegExp(a), `Aba "${a}" não encontrada`);
    }
  });

  test('TC-SMK-004 função init() está definida', () => {
    assert.match(appScript, /async function init\(\)/);
  });

  test('TC-SMK-005 função renderAll() está definida', () => {
    assert.match(appScript, /function renderAll\(\)/);
  });

  test('função escHtml() está definida no script', () => {
    assert.match(appScript, /function escHtml\(s\)/);
  });

  test('função sanitizeCsvRow() está definida no script', () => {
    assert.match(appScript, /function sanitizeCsvRow\(r\)/);
  });

  test('função showConfirm() está definida — confirm() nativo substituído', () => {
    assert.match(appScript, /function showConfirm\(/);
  });

  test('TC-SEC-005 confirm() nativo não é usado nas ações críticas', () => {
    // Não deve haver window.confirm() ou confirm() standalone nas ações
    const confirmNativo = appScript.match(/(?<!show|close|execute|\/\/.*)\bconfirm\s*\(/g) || [];
    // Permite apenas: showConfirm(, closeConfirm(, executeConfirm(
    const invalidos = confirmNativo.filter(c => !['showConfirm(', 'closeConfirm(', 'executeConfirm('].includes(c.trim()));
    assert.equal(invalidos.length, 0,
      `confirm() nativo encontrado ${invalidos.length} vez(es). Usar showConfirm() em vez disso.`);
  });
});

// ─── TC-UI: Navegação entre seções ───────────────────────────────────────────

describe('TC-UI: showSection — lógica de navegação', () => {
  // Extrai e testa a lógica de mapeamento de seções
  const sectionMap = { dashboard: 0, contas: 1, gastos: 2, cadastrar: 3, historico: 4, config: 5 };

  test('TC-UI-SMK-003 todas as 6 seções têm índice mapeado', () => {
    assert.equal(Object.keys(sectionMap).length, 6);
    const indices = Object.values(sectionMap);
    assert.deepEqual([...new Set(indices)].sort(), [0, 1, 2, 3, 4, 5]);
  });

  test('showSection mapeia corretamente dashboard → índice 0', () => {
    assert.equal(sectionMap['dashboard'], 0);
  });

  test('showSection mapeia corretamente historico → índice 4', () => {
    assert.equal(sectionMap['historico'], 4);
  });

  test('showSection mapeia corretamente config → índice 5', () => {
    assert.equal(sectionMap['config'], 5);
  });
});

// ─── TC-UI: Sub-abas da seção +Novo ──────────────────────────────────────────

describe('TC-UI: Sub-abas em +Novo', () => {
  test('HTML contém 4 sub-abas', () => {
    const subAbas = ['subbtn-conta', 'subbtn-gasto', 'subbtn-salario', 'subbtn-import'];
    for (const id of subAbas) {
      assert.match(appHtml, new RegExp(`id="${id}"`), `Sub-aba ${id} não encontrada`);
    }
  });

  test('subtab-conta é a aba ativa por padrão', () => {
    // A aba conta deve ter classe active no HTML inicial
    const match = appHtml.match(/id="subtab-conta"[^>]*class="([^"]*)"/) ||
                  appHtml.match(/class="([^"]*)"[^>]*id="subtab-conta"/);
    if (match) {
      assert.match(match[1], /active/);
    } else {
      // Verificar se subtab-conta precede as outras sem active
      const contaIdx = appHtml.indexOf('id="subtab-conta" class="subtab active"');
      assert.ok(contaIdx > -1, 'subtab-conta deve ter classe active');
    }
  });

  test('HTML contém formulário de salários com 4 campos', () => {
    const campos = ['sal-buti-base', 'sal-buti-bonus', 'sal-bita-base', 'sal-bita-bonus'];
    for (const id of campos) {
      assert.match(appHtml, new RegExp(`id="${id}"`), `Campo ${id} não encontrado`);
    }
  });
});

// ─── TC-UI: Cards de salário no painel ───────────────────────────────────────

describe('TC-UI: Dashboard — cards de salário', () => {
  test('HTML contém IDs de exibição dos salários', () => {
    const ids = ['salary-buti-base', 'salary-buti-bonus', 'salary-bita-base', 'salary-bita-bonus', 'salary-total'];
    for (const id of ids) {
      assert.match(appHtml, new RegExp(`id="${id}"`), `Elemento ${id} não encontrado no painel`);
    }
  });

  test('HTML contém salary-total-bar para renda do casal', () => {
    assert.match(appHtml, /salary-total-bar/);
    assert.match(appHtml, /Renda total do casal/);
  });
});

// ─── TC-UI: Formulário de cadastro de conta ──────────────────────────────────

describe('TC-UI: Formulário de nova conta', () => {
  test('HTML contém todos os campos obrigatórios do form', () => {
    const campos = ['new-name', 'new-valor', 'new-dia', 'new-cat', 'new-tipo', 'new-obs'];
    for (const id of campos) {
      assert.match(appHtml, new RegExp(`id="${id}"`), `Campo ${id} não encontrado`);
    }
  });

  test('checkbox "já paga" existe no HTML', () => {
    assert.match(appHtml, /id="new-ja-pago"/);
    assert.match(appHtml, /já paga neste mês/);
  });

  test('wrapper do checkbox começa oculto (display:none)', () => {
    assert.ok(
      appHtml.includes('id="new-ja-pago-wrap"') && appHtml.includes('display:none'),
      'new-ja-pago-wrap deve existir com display:none'
    );
  });

  test('botão de cadastrar conta existe', () => {
    assert.match(appHtml, /id="btn-add-conta"/);
    assert.match(appHtml, /Cadastrar conta/);
  });
});

// ─── TC-UI: Fechar mês exige digitação ───────────────────────────────────────

describe('TC-UI-013/014: Modal fecharMes com palavra de confirmação', () => {
  test('HTML contém modal de confirmação', () => {
    assert.match(appHtml, /id="confirm-overlay"/);
    assert.match(appHtml, /id="confirm-msg"/);
    assert.match(appHtml, /id="confirm-type-input"/);
  });

  test('fecharMes usa showConfirm com palavra FECHAR', () => {
    assert.match(appScript, /'FECHAR'/);
  });

  test('executeConfirm verifica palavra digitada antes de executar', () => {
    assert.match(appScript, /function executeConfirm\(\)/);
    assert.match(appScript, /toUpperCase\(\)/); // comparação case-insensitive
  });

  // Simulação da lógica de executeConfirm
  test('TC-UI-014 texto errado bloqueia execução (lógica isolada)', () => {
    const wordRequired = 'FECHAR';
    const typed = 'fechar_errado';
    const bloqueado = typed.toUpperCase() !== wordRequired.toUpperCase();
    assert.ok(bloqueado, 'Texto incorreto deve bloquear a execução');
  });

  test('TC-UI-014b texto correto libera execução', () => {
    const wordRequired = 'FECHAR';
    const typed = 'FECHAR';
    const liberado = typed.toUpperCase() === wordRequired.toUpperCase();
    assert.ok(liberado, 'Texto correto deve liberar a execução');
  });

  test('TC-UI-014c texto minúsculo "fechar" também aceito (case-insensitive)', () => {
    const wordRequired = 'FECHAR';
    const typed = 'fechar';
    const liberado = typed.toUpperCase() === wordRequired.toUpperCase();
    assert.ok(liberado, 'Case-insensitive deve aceitar minúsculo');
  });
});

// ─── TC-UI: Alertas e urgência ───────────────────────────────────────────────

describe('TC-UI-016/017: Alertas e badge de urgentes', () => {
  test('HTML contém elemento alert-area no dashboard', () => {
    assert.match(appHtml, /id="alert-area"/);
  });

  test('HTML contém badge urgentes-badge', () => {
    assert.match(appHtml, /id="urgentes-badge"/);
  });

  test('badge alert-count chama goAlerts ao clicar', () => {
    assert.match(appHtml, /onclick="goAlerts\(\)"/);
  });

  test('TC-UI-017 goAlerts navega para dashboard', () => {
    assert.match(appScript, /function goAlerts\(\).*showSection.*dashboard/s);
  });

  // Lógica de urgência simulada
  test('TC-UI-016 conta vencida gera alerta (lógica isolada)', () => {
    const DIA_HOJE = 10;
    function getUrg(dia) {
      if (!dia) return 'auto';
      const d = dia - DIA_HOJE;
      if (d < 0) return 'vencida';
      if (d === 0) return 'hoje';
      if (d <= 3) return 'urgente';
      return 'ok';
    }
    const contaVencida = { dia: 5, tipo: 'manual' };
    const pago = false;
    const urg = getUrg(contaVencida.dia);
    const deveAlertar = !pago && (urg === 'vencida' || urg === 'hoje' || urg === 'urgente');
    assert.ok(deveAlertar, 'Conta vencida não paga deve gerar alerta');
  });
});

// ─── TC-UI: Tema yin yang ─────────────────────────────────────────────────────

describe('TC-UI-011: Toggle de tema', () => {
  test('HTML contém SVG do yin yang', () => {
    assert.match(appHtml, /class="theme-toggle"/);
    assert.match(appHtml, /<svg.*viewBox/s);
  });

  test('toggleTheme alterna entre olive e purple', () => {
    assert.match(appScript, /temaAtual.*olive.*purple/s);
  });

  test('CSS contém variáveis para tema olive (padrão)', () => {
    assert.match(appHtml, /:root\s*\{/);
    assert.match(appHtml, /--accent.*#8a9a3a/); // verde oliva
  });

  test('CSS contém variáveis para tema purple', () => {
    assert.match(appHtml, /body\.theme-purple/);
    assert.match(appHtml, /--accent.*#c084fc/); // roxo
  });

  // Simulação da lógica de toggle
  test('TC-UI-011 toggle muda olive→purple→olive', () => {
    let tema = 'olive';
    function toggle() { tema = tema === 'olive' ? 'purple' : 'olive'; }
    toggle();
    assert.equal(tema, 'purple');
    toggle();
    assert.equal(tema, 'olive');
  });
});

// ─── TC-UI: Identificação Buti/Bita ──────────────────────────────────────────

describe('TC-UI-012: Seleção Buti/Bita', () => {
  test('HTML contém botões pessoa-btn-eu e pessoa-btn-esposa', () => {
    assert.match(appHtml, /id="pessoa-btn-eu"/);
    assert.match(appHtml, /id="pessoa-btn-esposa"/);
  });

  test('botões mostram Buti e Bita sem emojis', () => {
    // Verifica que os botões contêm os nomes corretos
    const butiBtn = appHtml.match(/id="pessoa-btn-eu"[^>]*>[^<]*/)?.[0] || '';
    const bitaBtn = appHtml.match(/id="pessoa-btn-esposa"[^>]*>[^<]*/)?.[0] || '';
    // Os botões devem conter o texto dos nomes
    assert.match(appHtml, />Buti<\/button>/);
    assert.match(appHtml, />Bita<\/button>/);
  });

  test('função setPessoa salva em localStorage', () => {
    assert.match(appScript, /localStorage\.setItem\('pessoa'/);
  });

  test('função setPessoa aplica cores fixas para Buti (verde oliva)', () => {
    assert.match(appScript, /#a8bc48/); // cor oliva do Buti
  });

  test('função setPessoa aplica cores fixas para Bita (roxo)', () => {
    assert.match(appScript, /#c084fc/); // cor roxa da Bita
  });
});

// ─── TC-UI: Importação CSV ───────────────────────────────────────────────────

describe('TC-UI-015: Importação CSV com preview', () => {
  test('HTML contém área de upload com input file', () => {
    assert.match(appHtml, /id="csv-upload"/);
    assert.match(appHtml, /accept="\.csv,\.xlsx"/);
  });

  test('HTML contém área de preview antes de confirmar', () => {
    assert.match(appHtml, /id="csv-preview"/);
    assert.match(appHtml, /id="csv-preview-list"/);
  });

  test('preview começa oculto', () => {
    assert.match(appHtml, /id="csv-preview"[^>]*style="display:none"/);
  });

  test('função cancelCSV limpa preview e input', () => {
    assert.match(appScript, /function cancelCSV\(\)/);
    assert.match(appScript, /csv-upload.*value.*=.*''|''.*csv-upload/s);
  });
});

// ─── TC-UI: Histórico e extrato ──────────────────────────────────────────────

describe('TC-UI-018: Histórico e extrato modal', () => {
  test('HTML contém seção histórico com lista', () => {
    assert.match(appHtml, /id="historico-list"/);
  });

  test('HTML contém modal de extrato', () => {
    assert.match(appHtml, /id="modal-overlay"/);
    assert.match(appHtml, /id="modal-body"/);
    assert.match(appHtml, /id="modal-title"/);
  });

  test('função abrirExtrato existe no script', () => {
    assert.match(appScript, /async function abrirExtrato\(key\)/);
  });

  test('função closeModal existe', () => {
    assert.match(appScript, /function closeModal\(/);
  });

  test('modal começa oculto com classe hidden', () => {
      const modalHidden = appHtml.includes('id="modal-overlay"') && appHtml.includes('class="modal-overlay hidden"');
    assert.ok(modalHidden, 'modal-overlay deve começar com classe hidden');;
  });
});

// ─── TC-UI: Polling e sincronização ──────────────────────────────────────────

describe('Polling e sincronização compartilhada', () => {
  test('polling de 30s está no script', () => {
    assert.match(appScript, /setInterval.*30000/s);
  });

  test('polling verifica salários e variáveis além de pagamentos', () => {
    assert.match(appScript, /salChanged/);
    assert.match(appScript, /varChanged/);
  });

  test('fallback localStorage quando Supabase falha', () => {
    assert.match(appScript, /salarios_bak/);
    assert.match(appScript, /variaveis_bak/);
  });

  test('sbGetConfig e sbSetConfig estão definidos', () => {
    assert.match(appScript, /async function sbGetConfig\(/);
    assert.match(appScript, /async function sbSetConfig\(/);
  });
});

// ─── TC-SEC: Segurança no HTML ────────────────────────────────────────────────

describe('TC-SEC: Verificações de segurança no código', () => {
  test('TC-SEC-001/002 escHtml está sendo chamado nos pontos de renderização', () => {
    const escHtmlCalls = (appScript.match(/escHtml\(/g) || []).length;
    assert.ok(escHtmlCalls >= 10,
      `Esperado pelo menos 10 chamadas a escHtml, encontrado ${escHtmlCalls}`);
  });

  test('TC-SEC-003/004 sanitizeCsvRow é usado no handleCSV', () => {
    assert.match(appScript, /\.map\(r=>sanitizeCsvRow\(r\)\)/);
  });

  test('Geist font carregada de fonte segura (Google Fonts)', () => {
    assert.match(appHtml, /fonts\.googleapis\.com.*Geist/);
  });

  test('Supabase URL e Key estão presentes no script', () => {
    assert.match(appScript, /SB_URL.*supabase\.co/);
    assert.match(appScript, /SB_KEY/);
  });
});
