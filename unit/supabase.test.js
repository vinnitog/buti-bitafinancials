/**
 * Integration Tests — Supabase API wrappers
 * Testa: sbGet, sbPost, sbPatch, sbDelete, sbGetConfig, sbSetConfig
 * Usa fetch mock nativo (Node 22 tem fetch global)
 */

import { test, describe, beforeEach, afterEach, mock } from 'node:test';
import assert from 'node:assert/strict';

const SB_URL = 'https://ykoyezbftqxrlqvwlrek.supabase.co';
const SB_KEY = 'test-key-mock';

// ─── Implementação das funções (extraídas do app) ─────────────────────────────

function makeSbFuncs(fetchFn) {
  async function sbGet(t, p = '') {
    const r = await fetchFn(`${SB_URL}/rest/v1/${t}?${p}`, {
      headers: { 'apikey': SB_KEY, 'Authorization': `Bearer ${SB_KEY}` }
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async function sbPost(t, d) {
    const r = await fetchFn(`${SB_URL}/rest/v1/${t}`, {
      method: 'POST',
      headers: { 'apikey': SB_KEY, 'Authorization': `Bearer ${SB_KEY}`, 'Content-Type': 'application/json', 'Prefer': 'return=representation' },
      body: JSON.stringify(d)
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async function sbPatch(t, id, d) {
    const r = await fetchFn(`${SB_URL}/rest/v1/${t}?id=eq.${id}`, {
      method: 'PATCH',
      headers: { 'apikey': SB_KEY, 'Authorization': `Bearer ${SB_KEY}`, 'Content-Type': 'application/json', 'Prefer': 'return=representation' },
      body: JSON.stringify(d)
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async function sbDelete(t, id) {
    const r = await fetchFn(`${SB_URL}/rest/v1/${t}?id=eq.${id}`, {
      method: 'DELETE',
      headers: { 'apikey': SB_KEY, 'Authorization': `Bearer ${SB_KEY}` }
    });
    if (!r.ok) throw new Error(await r.text());
  }

  async function sbGetConfig(chave) {
    try {
      const rows = await sbGet('configuracoes', `chave=eq.${encodeURIComponent(chave)}&limit=1`);
      return rows.length > 0 ? rows[0].valor : null;
    } catch (e) { return null; }
  }

  async function sbSetConfig(chave, valor) {
    const existing = await sbGetConfig(chave);
    if (existing !== null) {
      await fetchFn(`${SB_URL}/rest/v1/configuracoes?chave=eq.${encodeURIComponent(chave)}`, {
        method: 'PATCH',
        headers: { 'apikey': SB_KEY, 'Authorization': `Bearer ${SB_KEY}`, 'Content-Type': 'application/json', 'Prefer': 'return=minimal' },
        body: JSON.stringify({ valor, updated_at: new Date().toISOString() })
      });
    } else {
      await sbPost('configuracoes', { chave, valor });
    }
  }

  return { sbGet, sbPost, sbPatch, sbDelete, sbGetConfig, sbSetConfig };
}

// ─── Helper para criar fetch mock ────────────────────────────────────────────

function mockFetch(responses) {
  let callIndex = 0;
  const calls = [];
  const fetchFn = async (url, opts) => {
    calls.push({ url, opts });
    const resp = Array.isArray(responses) ? responses[callIndex++] : responses;
    return {
      ok: resp.ok ?? true,
      status: resp.status ?? 200,
      json: async () => resp.body ?? [],
      text: async () => resp.error ?? 'error'
    };
  };
  fetchFn.calls = calls;
  return fetchFn;
}

// ─── TC-INT: sbGet ───────────────────────────────────────────────────────────

describe('sbGet', () => {
  test('TC-INT-001 retorna array de dados em sucesso', async () => {
    const dados = [{ id: 1, nome: 'Carro', valor: 2600 }];
    const fetch = mockFetch({ body: dados });
    const { sbGet } = makeSbFuncs(fetch);

    const result = await sbGet('contas', 'ativo=eq.true');
    assert.deepEqual(result, dados);
  });

  test('TC-INT-002 envia apikey no header', async () => {
    const fetch = mockFetch({ body: [] });
    const { sbGet } = makeSbFuncs(fetch);
    await sbGet('contas');

    const [call] = fetch.calls;
    assert.equal(call.opts.headers['apikey'], SB_KEY);
    assert.equal(call.opts.headers['Authorization'], `Bearer ${SB_KEY}`);
  });

  test('TC-INT-003 lança erro quando resposta não é ok', async () => {
    const fetch = mockFetch({ ok: false, error: 'relation does not exist' });
    const { sbGet } = makeSbFuncs(fetch);

    await assert.rejects(
      () => sbGet('tabela_inexistente'),
      /relation does not exist/
    );
  });

  test('TC-INT-004 URL inclui tabela e params', async () => {
    const fetch = mockFetch({ body: [] });
    const { sbGet } = makeSbFuncs(fetch);
    await sbGet('pagamentos', 'mes=eq.5&ano=eq.2026');

    const [call] = fetch.calls;
    assert.match(call.url, /pagamentos/);
    assert.match(call.url, /mes=eq.5/);
    assert.match(call.url, /ano=eq.2026/);
  });
});

// ─── TC-INT: sbPost ──────────────────────────────────────────────────────────

describe('sbPost', () => {
  test('TC-INT-005 envia dados como JSON e retorna criado', async () => {
    const nova = { id: 42, nome: 'Netflix', valor: 55 };
    const fetch = mockFetch({ body: [nova] });
    const { sbPost } = makeSbFuncs(fetch);

    const result = await sbPost('contas', { nome: 'Netflix', valor: 55 });
    assert.deepEqual(result, [nova]);
  });

  test('TC-INT-006 envia header Prefer return=representation', async () => {
    const fetch = mockFetch({ body: [] });
    const { sbPost } = makeSbFuncs(fetch);
    await sbPost('contas', { nome: 'X' });

    const [call] = fetch.calls;
    assert.equal(call.opts.headers['Prefer'], 'return=representation');
  });

  test('TC-INT-007 body serializado como JSON string', async () => {
    const fetch = mockFetch({ body: [] });
    const { sbPost } = makeSbFuncs(fetch);
    const data = { nome: 'Spotify', valor: 22 };
    await sbPost('contas', data);

    const [call] = fetch.calls;
    assert.deepEqual(JSON.parse(call.opts.body), data);
  });

  test('TC-INT-008 lança erro em falha', async () => {
    const fetch = mockFetch({ ok: false, error: 'unique constraint violation' });
    const { sbPost } = makeSbFuncs(fetch);

    await assert.rejects(
      () => sbPost('contas', { nome: 'X' }),
      /unique constraint/
    );
  });
});

// ─── TC-INT: sbPatch ─────────────────────────────────────────────────────────

describe('sbPatch', () => {
  test('TC-INT-009 envia PATCH com filtro por ID', async () => {
    const fetch = mockFetch({ body: [{ id: 5, pago: true }] });
    const { sbPatch } = makeSbFuncs(fetch);
    await sbPatch('pagamentos', 5, { pago: true });

    const [call] = fetch.calls;
    assert.match(call.url, /id=eq\.5/);
    assert.equal(call.opts.method, 'PATCH');
  });

  test('TC-INT-010 envia somente os campos informados', async () => {
    const fetch = mockFetch({ body: [] });
    const { sbPatch } = makeSbFuncs(fetch);
    await sbPatch('contas', 1, { valor: 3000 });

    const [call] = fetch.calls;
    const body = JSON.parse(call.opts.body);
    assert.deepEqual(body, { valor: 3000 });
  });
});

// ─── TC-INT: sbDelete ────────────────────────────────────────────────────────

describe('sbDelete', () => {
  test('TC-INT-011 envia DELETE com filtro por ID', async () => {
    const fetch = mockFetch({ body: null });
    const { sbDelete } = makeSbFuncs(fetch);
    await sbDelete('gastos_avulsos', 99);

    const [call] = fetch.calls;
    assert.match(call.url, /id=eq\.99/);
    assert.equal(call.opts.method, 'DELETE');
  });

  test('TC-INT-012 lança erro quando DELETE falha', async () => {
    const fetch = mockFetch({ ok: false, error: 'row not found' });
    const { sbDelete } = makeSbFuncs(fetch);

    await assert.rejects(
      () => sbDelete('gastos_avulsos', 999),
      /row not found/
    );
  });
});

// ─── TC-INT: sbGetConfig / sbSetConfig ───────────────────────────────────────

describe('sbGetConfig', () => {
  test('TC-INT-013 retorna valor quando chave existe', async () => {
    const valor = { buti: { base: 12000, bonus: 1000 }, bita: { base: 0, bonus: 0 } };
    const fetch = mockFetch({ body: [{ chave: 'salarios', valor }] });
    const { sbGetConfig } = makeSbFuncs(fetch);

    const result = await sbGetConfig('salarios');
    assert.deepEqual(result, valor);
  });

  test('TC-INT-014 retorna null quando chave não existe', async () => {
    const fetch = mockFetch({ body: [] }); // array vazio = não encontrado
    const { sbGetConfig } = makeSbFuncs(fetch);

    const result = await sbGetConfig('chave_inexistente');
    assert.equal(result, null);
  });

  test('TC-INT-015 retorna null silenciosamente em erro de rede', async () => {
    const fetch = mockFetch({ ok: false, error: 'network error' });
    const { sbGetConfig } = makeSbFuncs(fetch);

    // Não deve lançar — retorna null como fallback
    const result = await sbGetConfig('qualquer');
    assert.equal(result, null);
  });
});

describe('sbSetConfig', () => {
  test('TC-INT-016 faz PATCH quando chave já existe', async () => {
    const valorExistente = { buti: { base: 10000, bonus: 0 }, bita: { base: 0, bonus: 0 } };
    const valorNovo = { buti: { base: 12000, bonus: 1000 }, bita: { base: 3000, bonus: 500 } };

    // Primeira call = sbGetConfig (retorna existente), segunda = PATCH
    const fetch = mockFetch([
      { body: [{ chave: 'salarios', valor: valorExistente }] }, // sbGetConfig
      { body: null, ok: true }                                   // PATCH
    ]);
    const { sbSetConfig } = makeSbFuncs(fetch);
    await sbSetConfig('salarios', valorNovo);

    const patchCall = fetch.calls[1];
    assert.equal(patchCall.opts.method, 'PATCH');
    assert.match(patchCall.url, /configuracoes/);
    assert.match(patchCall.url, /chave=eq.salarios/);
  });

  test('TC-INT-017 faz POST quando chave não existe', async () => {
    const valorNovo = [{ nome: 'Supermercado', valor: 1600 }];

    const fetch = mockFetch([
      { body: [] },      // sbGetConfig → null (não existe)
      { body: [{}] }     // sbPost → inserção
    ]);
    const { sbSetConfig } = makeSbFuncs(fetch);
    await sbSetConfig('variaveis', valorNovo);

    const postCall = fetch.calls[1];
    assert.equal(postCall.opts.method, 'POST');
    const body = JSON.parse(postCall.opts.body);
    assert.equal(body.chave, 'variaveis');
    assert.deepEqual(body.valor, valorNovo);
  });
});

// ─── TC-SEC: Supabase headers nunca vazam chave em GET plain ─────────────────

describe('Segurança dos headers Supabase', () => {
  test('TC-SEC-005 todas as chamadas incluem Authorization Bearer', async () => {
    const funcs = [
      (f) => makeSbFuncs(f).sbGet('contas'),
      (f) => makeSbFuncs(f).sbPost('contas', { nome: 'X' }),
      (f) => makeSbFuncs(f).sbPatch('contas', 1, { nome: 'Y' }),
      (f) => makeSbFuncs(f).sbDelete('contas', 1),
    ];

    for (const fn of funcs) {
      const fetch = mockFetch({ body: [] });
      await fn(fetch).catch(() => {});
      const [call] = fetch.calls;
      assert.match(call.opts.headers['Authorization'], /^Bearer /);
    }
  });
});
