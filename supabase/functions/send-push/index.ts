// supabase/functions/send-push/index.ts
// Deploy: supabase functions deploy send-push --no-verify-jwt
//
// Secrets (Supabase → Settings → Edge Functions → Secrets):
//   VAPID_PUBLIC_KEY
//   VAPID_PRIVATE_KEY
//   VAPID_SUBJECT  (ex: mailto:seu@email.com)

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import webpush from 'https://esm.sh/web-push@3.6.7'

const VAPID_PUBLIC_KEY = Deno.env.get('VAPID_PUBLIC_KEY')!
const VAPID_PRIVATE_KEY = Deno.env.get('VAPID_PRIVATE_KEY')!
const VAPID_SUBJECT = Deno.env.get('VAPID_SUBJECT') ?? 'mailto:admin@butibita.app'
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SUPABASE_SERVICE = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

function formatBRL(v: number): string {
  return 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'authorization, content-type' }
    })
  }

  try {
    // Configurar VAPID
    webpush.setVapidDetails(VAPID_SUBJECT, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY)

    const body = await req.json().catch(() => ({}))
    const tipo: string = body.tipo ?? 'test'

    const now = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/Sao_Paulo' }))
    const diaHoje = now.getDate()
    const mesAtual = now.getMonth() + 1
    const anoAtual = now.getFullYear()

    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE)

    // Buscar subscriptions
    const { data: subs, error: subErr } = await supabase
      .from('push_subscriptions').select('*')
    if (subErr) throw new Error(`push_subscriptions: ${subErr.message}`)
    if (!subs || subs.length === 0) {
      return Response.json({ ok: true, enviados: 0, msg: 'sem subscriptions' })
    }

    // Buscar contas e pagamentos
    const { data: contas } = await supabase
      .from('contas').select('*').eq('ativo', true).gt('dia', 0).neq('tipo', 'auto')

    const { data: pagamentos } = await supabase
      .from('pagamentos').select('*').eq('mes', mesAtual).eq('ano', anoAtual)

    // Filtrar por tipo
    const filtradas = (contas ?? []).filter((c: any) => {
      const pag = pagamentos?.find((p: any) => p.conta_id === c.id)
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

    // Montar payload
    const titulo = tipo === 'hoje_12h'
      ? '🚨 Lembrete: vencimento hoje!'
      : tipo === '3dias'
        ? '⚡ Vencimento em 3 dias'
        : '📋 Buti&Bita — Vencimentos'

    const corpo = filtradas.map((c: any) => {
      const diff = c.dia - diaHoje
      return diff === 0
        ? `${c.emoji || '💰'} ${c.nome} vence HOJE — ${formatBRL(c.valor)}`
        : `${c.emoji || '💰'} ${c.nome} vence em ${diff} dia${diff > 1 ? 's' : ''} — ${formatBRL(c.valor)}`
    }).join('\n')

    const notifPayload = JSON.stringify({
      title: titulo,
      body: corpo,
      tag: `venc-${tipo}-${diaHoje}`,
      requireInteraction: tipo.includes('hoje'),
      icon: 'https://vinnitog.github.io/buti-bitafinancials/icon-192.png',
      badge: 'https://vinnitog.github.io/buti-bitafinancials/icon-32.png',
    })

    // Enviar para cada subscription
    let enviados = 0
    const expiradas: number[] = []
    const erros: string[] = []

    for (const sub of subs) {
      try {
        const pushSub = {
          endpoint: sub.endpoint,
          keys: { p256dh: sub.p256dh, auth: sub.auth }
        }
        await webpush.sendNotification(pushSub, notifPayload, { TTL: 86400 })
        console.log(`✓ sub ${sub.id} enviado`)
        enviados++
      } catch (e: any) {
        const status = e?.statusCode ?? 0
        console.error(`✗ sub ${sub.id}: status=${status} msg=${e?.message}`)
        if (status === 404 || status === 410) {
          expiradas.push(sub.id)
        } else {
          erros.push(`sub ${sub.id}: ${e?.message ?? String(e)}`)
        }
      }
    }

    // Limpar expiradas
    if (expiradas.length > 0) {
      await supabase.from('push_subscriptions').delete().in('id', expiradas)
    }

    return Response.json({
      ok: true, enviados,
      total: subs.length,
      contas: filtradas.length,
      expiradas: expiradas.length,
      erros: erros.length > 0 ? erros : undefined,
    })

  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    console.error('send-push fatal:', msg)
    return Response.json({ ok: false, error: msg }, { status: 500 })
  }
})