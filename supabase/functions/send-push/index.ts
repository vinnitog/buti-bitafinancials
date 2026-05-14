// supabase/functions/send-push/index.ts
// Deploy: supabase functions deploy send-push --no-verify-jwt
//
// Variáveis de ambiente necessárias (supabase secrets set):
//   VAPID_PUBLIC_KEY
//   VAPID_PRIVATE_KEY
//   VAPID_SUBJECT (ex: mailto:seu@email.com)

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const VAPID_PUBLIC_KEY  = Deno.env.get('VAPID_PUBLIC_KEY')!
const VAPID_PRIVATE_KEY = Deno.env.get('VAPID_PRIVATE_KEY')!
const VAPID_SUBJECT     = Deno.env.get('VAPID_SUBJECT') ?? 'mailto:admin@butibita.app'
const SUPABASE_URL      = Deno.env.get('SUPABASE_URL')!
const SUPABASE_SERVICE  = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

// ─── VAPID JWT helpers ────────────────────────────────────────────────────────

function base64url(data: Uint8Array): string {
  return btoa(String.fromCharCode(...data))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
}

function base64urlDecode(s: string): Uint8Array {
  s = s.replace(/-/g, '+').replace(/_/g, '/')
  while (s.length % 4) s += '='
  return Uint8Array.from(atob(s), c => c.charCodeAt(0))
}

async function makeVapidJwt(audience: string): Promise<string> {
  const header  = { typ: 'JWT', alg: 'ES256' }
  const payload = {
    aud: audience,
    exp: Math.floor(Date.now() / 1000) + 12 * 3600,
    sub: VAPID_SUBJECT,
  }
  const enc = new TextEncoder()
  const headerB64  = base64url(enc.encode(JSON.stringify(header)))
  const payloadB64 = base64url(enc.encode(JSON.stringify(payload)))
  const unsigned   = `${headerB64}.${payloadB64}`

  const keyData = base64urlDecode(VAPID_PRIVATE_KEY)
  const key = await crypto.subtle.importKey(
    'pkcs8',
    // Convert raw EC key to PKCS#8 if needed — handle both formats
    keyData.length === 32
      ? (() => {
          // Wrap raw 32-byte private key in PKCS#8 DER for P-256
          const der = new Uint8Array([
            0x30,0x41,0x02,0x01,0x00,0x30,0x13,0x06,0x07,0x2a,0x86,0x48,0xce,
            0x3d,0x02,0x01,0x06,0x08,0x2a,0x86,0x48,0xce,0x3d,0x03,0x01,0x07,
            0x04,0x27,0x30,0x25,0x02,0x01,0x01,0x04,0x20,
            ...keyData
          ])
          return der.buffer
        })()
      : keyData.buffer,
    { name: 'ECDSA', namedCurve: 'P-256' },
    false,
    ['sign']
  )

  const sig = await crypto.subtle.sign(
    { name: 'ECDSA', hash: 'SHA-256' },
    key,
    enc.encode(unsigned)
  )
  return `${unsigned}.${base64url(new Uint8Array(sig))}`
}

// ─── Web Push sender ──────────────────────────────────────────────────────────

async function sendPush(sub: { endpoint: string; p256dh: string; auth: string }, payload: string): Promise<boolean> {
  const url      = new URL(sub.endpoint)
  const audience = `${url.protocol}//${url.host}`
  const jwt      = await makeVapidJwt(audience)

  // Encrypt payload using Web Push encryption (RFC 8291)
  // For simplicity we use the raw content-encoding=aes128gcm approach
  const enc = new TextEncoder()
  const bodyBytes = enc.encode(payload)

  // Generate salt and local key pair
  const salt    = crypto.getRandomValues(new Uint8Array(16))
  const localKP = await crypto.subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveKey', 'deriveBits'])

  // Import receiver's public key
  const receiverKey = await crypto.subtle.importKey(
    'raw', base64urlDecode(sub.p256dh),
    { name: 'ECDH', namedCurve: 'P-256' }, false, []
  )

  // Derive shared secret
  const sharedBits = await crypto.subtle.deriveBits(
    { name: 'ECDH', public: receiverKey },
    localKP.privateKey, 256
  )

  // Export local public key
  const localPubRaw = new Uint8Array(await crypto.subtle.exportKey('raw', localKP.publicKey))

  // Auth secret
  const authSecret = base64urlDecode(sub.auth)

  // HKDF for content encryption key and nonce (RFC 8291)
  const prk = await crypto.subtle.importKey('raw', sharedBits, 'HKDF', false, ['deriveKey', 'deriveBits'])

  // ikm = HKDF-Extract(authSecret, sharedBits) with info
  const ikm = await crypto.subtle.deriveBits(
    { name: 'HKDF', hash: 'SHA-256', salt: authSecret, info: enc.encode('WebPush: info\x00') },
    prk, 256
  )
  const ikmKey = await crypto.subtle.importKey('raw', ikm, 'HKDF', false, ['deriveKey', 'deriveBits'])

  // Content encryption key
  const cekBits = await crypto.subtle.deriveBits(
    { name: 'HKDF', hash: 'SHA-256', salt, info: enc.encode('Content-Encoding: aes128gcm\x00') },
    ikmKey, 128
  )
  const cek = await crypto.subtle.importKey('raw', cekBits, 'AES-GCM', false, ['encrypt'])

  // Nonce
  const nonceBits = await crypto.subtle.deriveBits(
    { name: 'HKDF', hash: 'SHA-256', salt, info: enc.encode('Content-Encoding: nonce\x00') },
    ikmKey, 96
  )
  const nonce = new Uint8Array(nonceBits)

  // Encrypt (add padding delimiter 0x02)
  const plaintext = new Uint8Array([...bodyBytes, 0x02])
  const ciphertext = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv: nonce }, cek, plaintext))

  // Build aes128gcm content header
  // header = salt(16) + rs(4 BE) + idlen(1) + keyid(65)
  const rs = new Uint8Array(4); new DataView(rs.buffer).setUint32(0, 4096, false)
  const header = new Uint8Array([...salt, ...rs, 65, ...localPubRaw])
  const body   = new Uint8Array([...header, ...ciphertext])

  const res = await fetch(sub.endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/octet-stream',
      'Content-Encoding': 'aes128gcm',
      'TTL': '86400',
      'Authorization': `vapid t=${jwt},k=${VAPID_PUBLIC_KEY}`,
    },
    body,
  })

  return res.ok || res.status === 201
}

// ─── Main handler ─────────────────────────────────────────────────────────────

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'authorization, content-type' } })
  }

  const { tipo } = await req.json().catch(() => ({ tipo: 'test' }))
  const hoje = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/Sao_Paulo' }))
  const diaHoje = hoje.getDate()
  const mesAtual = hoje.getMonth() + 1
  const anoAtual = hoje.getFullYear()

  const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE)

  // Buscar subscriptions ativas
  const { data: subs } = await supabase.from('push_subscriptions').select('*')
  if (!subs || subs.length === 0) {
    return new Response(JSON.stringify({ ok: true, enviados: 0, msg: 'sem subscriptions' }), { status: 200 })
  }

  // Buscar contas ativas e pagamentos do mês
  const { data: contas } = await supabase.from('contas').select('*').eq('ativo', true).gt('dia', 0).neq('tipo', 'auto')
  const { data: pagamentos } = await supabase.from('pagamentos').select('*').eq('mes', mesAtual).eq('ano', anoAtual)

  if (!contas) return new Response(JSON.stringify({ ok: false, msg: 'erro ao buscar contas' }), { status: 500 })

  // Filtrar contas não pagas e com vencimento relevante para o tipo de push
  const contasFiltradas = contas.filter(c => {
    const pag = pagamentos?.find(p => p.conta_id === c.id)
    if (pag?.pago) return false // já paga, não notifica

    const diff = c.dia - diaHoje
    if (tipo === '3dias')    return diff === 3
    if (tipo === 'hoje_8h')  return diff === 0
    if (tipo === 'hoje_12h') return diff === 0
    if (tipo === 'test')     return diff >= 0 && diff <= 3
    return false
  })

  if (contasFiltradas.length === 0) {
    return new Response(JSON.stringify({ ok: true, enviados: 0, msg: 'nenhuma conta para notificar' }), { status: 200 })
  }

  // Montar mensagem
  const msgs = contasFiltradas.map(c => {
    const diff = c.dia - diaHoje
    if (diff === 0) {
      return tipo === 'hoje_12h'
        ? `🚨 ${c.nome} vence HOJE — não esqueça! (${formatBRL(c.valor)})`
        : `🚨 ${c.nome} vence HOJE — ${formatBRL(c.valor)}`
    }
    return `⚡ ${c.nome} vence em ${diff} dia${diff > 1 ? 's' : ''} — ${formatBRL(c.valor)}`
  })

  const titulo = tipo === 'hoje_12h' ? '🚨 Vencimento hoje!' : tipo === '3dias' ? '⚡ Vencimento em 3 dias' : '📋 Buti&Bita Financials'
  const corpo  = msgs.join('\n')

  // Disparar push para todas as subscriptions
  let enviados = 0
  const expiradas: number[] = []
  for (const sub of subs) {
    try {
      const ok = await sendPush(sub, JSON.stringify({ title: titulo, body: corpo, tag: `venc-${tipo}-${diaHoje}`, requireInteraction: tipo.includes('hoje') }))
      if (ok) enviados++
      else expiradas.push(sub.id)
    } catch {
      expiradas.push(sub.id)
    }
  }

  // Remover subscriptions expiradas/inválidas
  if (expiradas.length > 0) {
    await supabase.from('push_subscriptions').delete().in('id', expiradas)
  }

  return new Response(JSON.stringify({ ok: true, enviados, total: subs.length, contas: contasFiltradas.length }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  })
})

function formatBRL(v: number): string {
  return 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}