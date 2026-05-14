// supabase/functions/send-push/index.ts
// Deploy: supabase functions deploy send-push --no-verify-jwt
//
// Secrets necessários (Supabase → Settings → Edge Functions → Secrets):
//   VAPID_PUBLIC_KEY
//   VAPID_PRIVATE_KEY
//   VAPID_SUBJECT (ex: mailto:seu@email.com)

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const VAPID_PUBLIC_KEY  = Deno.env.get('VAPID_PUBLIC_KEY')!
const VAPID_PRIVATE_KEY = Deno.env.get('VAPID_PRIVATE_KEY')!
const VAPID_SUBJECT     = Deno.env.get('VAPID_SUBJECT') ?? 'mailto:admin@butibita.app'
const SUPABASE_URL      = Deno.env.get('SUPABASE_URL')!
const SUPABASE_SERVICE  = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

// ─── Helpers ─────────────────────────────────────────────────────────────────

function b64u(data: Uint8Array): string {
  return btoa(String.fromCharCode(...data))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
}

function b64uDecode(s: string): Uint8Array {
  s = s.replace(/-/g, '+').replace(/_/g, '/')
  while (s.length % 4) s += '='
  return Uint8Array.from(atob(s), c => c.charCodeAt(0))
}

function formatBRL(v: number): string {
  return 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

// ─── VAPID JWT ────────────────────────────────────────────────────────────────

async function vapidJwt(audience: string): Promise<string> {
  const enc     = new TextEncoder()
  const header  = b64u(enc.encode(JSON.stringify({ typ: 'JWT', alg: 'ES256' })))
  const payload = b64u(enc.encode(JSON.stringify({
    aud: audience,
    exp: Math.floor(Date.now() / 1000) + 43200,
    sub: VAPID_SUBJECT,
  })))
  const unsigned = `${header}.${payload}`

  const rawPriv = b64uDecode(VAPID_PRIVATE_KEY)
  const rawPub  = b64uDecode(VAPID_PUBLIC_KEY)

  const jwk = {
    kty: 'EC', crv: 'P-256',
    d: b64u(rawPriv),
    x: b64u(rawPub.slice(1, 33)),
    y: b64u(rawPub.slice(33, 65)),
    key_ops: ['sign'],
  }

  const key = await crypto.subtle.importKey(
    'jwk', jwk, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign']
  )
  const sig = new Uint8Array(
    await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, key, enc.encode(unsigned))
  )
  return `${unsigned}.${b64u(sig)}`
}

// ─── Web Push encryption (RFC 8291 / aes128gcm) ──────────────────────────────

async function encryptPayload(
  sub: { p256dh: string; auth: string },
  plaintext: string
): Promise<{ ciphertext: Uint8Array; salt: Uint8Array; serverPublicKey: Uint8Array }> {
  const enc = new TextEncoder()

  const receiverPub = await crypto.subtle.importKey(
    'raw', b64uDecode(sub.p256dh),
    { name: 'ECDH', namedCurve: 'P-256' }, false, []
  )

  const serverKP = await crypto.subtle.generateKey(
    { name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']
  )
  const serverPubRaw = new Uint8Array(await crypto.subtle.exportKey('raw', serverKP.publicKey))

  const sharedSecret = new Uint8Array(
    await crypto.subtle.deriveBits({ name: 'ECDH', public: receiverPub }, serverKP.privateKey, 256)
  )

  const authSecret = b64uDecode(sub.auth)
  const salt       = crypto.getRandomValues(new Uint8Array(16))

  // PRK
  const prkHmacKey = await crypto.subtle.importKey(
    'raw', authSecret, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  )
  const prk = new Uint8Array(await crypto.subtle.sign('HMAC', prkHmacKey, sharedSecret))

  // IKM → CEK (128 bits) and Nonce (96 bits) via HKDF
  async function hkdfExpand(prk: Uint8Array, info: string, len: number): Promise<Uint8Array> {
    const key = await crypto.subtle.importKey('raw', prk, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
    const infoBytes = enc.encode(info)
    const input = new Uint8Array([...infoBytes, 0x01])
    const out = new Uint8Array(await crypto.subtle.sign('HMAC', key, input))
    return out.slice(0, len)
  }

  const saltKey = await crypto.subtle.importKey('raw', salt, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
  const ikmBytes = new Uint8Array([...b64uDecode(sub.p256dh), ...serverPubRaw])
  const ikm = new Uint8Array(await crypto.subtle.sign('HMAC', saltKey, ikmBytes))

  // Simpler approach: use HKDF via SubtleCrypto directly
  const ikmKey = await crypto.subtle.importKey('raw', prk, { name: 'HKDF' }, false, ['deriveBits'])

  const cekBits = new Uint8Array(await crypto.subtle.deriveBits(
    { name: 'HKDF', hash: 'SHA-256', salt, info: enc.encode('Content-Encoding: aes128gcm\x00') },
    ikmKey, 128
  ))
  const nonceBits = new Uint8Array(await crypto.subtle.deriveBits(
    { name: 'HKDF', hash: 'SHA-256', salt, info: enc.encode('Content-Encoding: nonce\x00') },
    ikmKey, 96
  ))

  const cek = await crypto.subtle.importKey('raw', cekBits, 'AES-GCM', false, ['encrypt'])
  const pt  = new Uint8Array([...enc.encode(plaintext), 0x02])
  const ct  = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv: nonceBits }, cek, pt))

  return { ciphertext: ct, salt, serverPublicKey: serverPubRaw }
}

// ─── Send a single push ───────────────────────────────────────────────────────

async function sendPush(
  sub: { endpoint: string; p256dh: string; auth: string },
  payload: object
): Promise<{ ok: boolean; status: number }> {
  const { ciphertext, salt, serverPublicKey } = await encryptPayload(sub, JSON.stringify(payload))

  const rs   = new Uint8Array(4); new DataView(rs.buffer).setUint32(0, 4096, false)
  const body = new Uint8Array([...salt, ...rs, 65, ...serverPublicKey, ...ciphertext])

  const url      = new URL(sub.endpoint)
  const audience = `${url.protocol}//${url.host}`
  const jwt      = await vapidJwt(audience)

  const res = await fetch(sub.endpoint, {
    method: 'POST',
    headers: {
      'Content-Type':     'application/octet-stream',
      'Content-Encoding': 'aes128gcm',
      'TTL':              '86400',
      'Urgency':          'normal',
      'Authorization':    `vapid t=${jwt},k=${VAPID_PUBLIC_KEY}`,
    },
    body,
  })

  return { ok: res.ok || res.status === 201, status: res.status }
}

// ─── Main ─────────────────────────────────────────────────────────────────────

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'authorization, content-type' }
    })
  }

  try {
    const body     = await req.json().catch(() => ({}))
    const tipo: string = body.tipo ?? 'test'

    const now      = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/Sao_Paulo' }))
    const diaHoje  = now.getDate()
    const mesAtual = now.getMonth() + 1
    const anoAtual = now.getFullYear()

    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE)

    const { data: subs, error: subErr } = await supabase.from('push_subscriptions').select('*')
    if (subErr) throw new Error(`push_subscriptions: ${subErr.message}`)
    if (!subs || subs.length === 0) {
      return Response.json({ ok: true, enviados: 0, msg: 'sem subscriptions' })
    }

    const { data: contas } = await supabase
      .from('contas').select('*').eq('ativo', true).gt('dia', 0).neq('tipo', 'auto')

    const { data: pagamentos } = await supabase
      .from('pagamentos').select('*').eq('mes', mesAtual).eq('ano', anoAtual)

    const filtradas = (contas ?? []).filter(c => {
      const pag  = pagamentos?.find((p: any) => p.conta_id === c.id)
      if (pag?.pago) return false
      const diff = c.dia - diaHoje
      if (tipo === '3dias')    return diff === 3
      if (tipo === 'hoje_8h')  return diff === 0
      if (tipo === 'hoje_12h') return diff === 0
      if (tipo === 'test')     return diff >= 0 && diff <= 7
      return false
    })

    if (filtradas.length === 0) {
      return Response.json({ ok: true, enviados: 0, msg: 'nenhuma conta para notificar', diaHoje, tipo })
    }

    const titulo = tipo === 'hoje_12h'
      ? '🚨 Lembrete: vencimento hoje!'
      : tipo === '3dias' ? '⚡ Vencimento em 3 dias' : '📋 Buti&Bita — Vencimentos'

    const corpo = filtradas.map((c: any) => {
      const diff = c.dia - diaHoje
      return diff === 0
        ? `${c.emoji || '💰'} ${c.nome} vence HOJE — ${formatBRL(c.valor)}`
        : `${c.emoji || '💰'} ${c.nome} vence em ${diff} dia${diff > 1 ? 's' : ''} — ${formatBRL(c.valor)}`
    }).join('\n')

    const notifPayload = {
      title: titulo,
      body: corpo,
      tag: `venc-${tipo}-${diaHoje}`,
      requireInteraction: tipo.includes('hoje'),
    }

    let enviados = 0
    const expiradas: number[] = []
    const erros: string[] = []

    for (const sub of subs) {
      try {
        const { ok, status } = await sendPush(sub, notifPayload)
        console.log(`sub ${sub.id}: status=${status} ok=${ok}`)
        if (ok) {
          enviados++
        } else if (status === 404 || status === 410) {
          expiradas.push(sub.id)
        } else {
          erros.push(`sub ${sub.id}: HTTP ${status}`)
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        console.error(`sub ${sub.id} error:`, msg)
        erros.push(`sub ${sub.id}: ${msg}`)
      }
    }

    if (expiradas.length > 0) {
      await supabase.from('push_subscriptions').delete().in('id', expiradas)
    }

    return Response.json({ ok: true, enviados, total: subs.length, contas: filtradas.length, erros: erros.length > 0 ? erros : undefined })

  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    console.error('send-push fatal:', msg)
    return Response.json({ ok: false, error: msg }, { status: 500 })
  }
})