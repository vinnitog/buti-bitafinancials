/**
 * Buti & Bita Financials — Service Worker
 * Estratégia: network-first para o HTML (sempre atualizado),
 * cache-first para assets estáticos (fontes, ícones).
 * Resultado: push no GitHub → usuário vê a mudança no próximo reload,
 * sem precisar reinstalar o PWA ou atualizar versão manualmente.
 */

const CACHE_NAME = 'buti-bita-v1';

// Install — não pré-cacheia nada (evita travar em versão antiga)
self.addEventListener('install', event => {
  self.skipWaiting(); // ativa imediatamente sem esperar aba fechar
});

// Activate — limpa caches antigos
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim(); // assume controle de todas as abas abertas
});

// Fetch — estratégia por tipo de recurso
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Supabase: nunca interceptar — sempre rede
  if (url.hostname.includes('supabase.co')) return;

  // Google Fonts: cache-first (não mudam)
  if (url.hostname.includes('fonts.googleapis.com') ||
      url.hostname.includes('fonts.gstatic.com')) {
    event.respondWith(
      caches.match(event.request).then(cached =>
        cached || fetch(event.request).then(res => {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
          return res;
        })
      )
    );
    return;
  }

  // HTML (index.html / raiz): network-first — garante versão mais recente
  // Se offline, cai no cache como fallback
  if (event.request.mode === 'navigate' ||
      url.pathname.endsWith('.html') ||
      url.pathname === '/' ||
      url.pathname.endsWith('/')) {
    event.respondWith(
      fetch(event.request)
        .then(res => {
          // Atualiza cache com versão nova
          const clone = res.clone();
          caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
          return res;
        })
        .catch(() => caches.match(event.request)) // offline fallback
    );
    return;
  }

  // Demais assets (sw.js, ícones): network-first também
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});

// Push — notificação recebida do servidor
self.addEventListener('push', event => {
  let data = { title: 'Buti&Bita Financials', body: 'Verifique seus vencimentos!', tag: 'buti-bita', requireInteraction: false };
  if (event.data) {
    try { Object.assign(data, event.data.json()); } catch { data.body = event.data.text(); }
  }
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: './icon-192.png',
      badge: './icon-32.png',
      tag: data.tag || 'buti-bita',
      requireInteraction: data.requireInteraction || false,
      vibrate: [200, 100, 200],
      data: { url: './' }
    })
  );
});

// Clique na notificação — abre ou foca o app
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const client of list) {
        if (client.url.includes('buti') || client.url.includes('index')) {
          return client.focus();
        }
      }
      return clients.openWindow(event.notification.data?.url || './');
    })
  );
});