/**
 * Buti & Bita Financials — Service Worker
 * Handles: offline cache, push notifications
 */

const CACHE_NAME = 'buti-bita-v1';
const ASSETS = ['./'];  // cache the app shell

// Install — cache app shell
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

// Activate — clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch — network first, fallback to cache
self.addEventListener('fetch', event => {
  // Don't intercept Supabase API calls — always need fresh data
  if (event.request.url.includes('supabase.co')) return;

  event.respondWith(
    fetch(event.request)
      .then(res => {
        // Cache successful GET responses
        if (res.ok && event.request.method === 'GET') {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(event.request))
  );
});

// Push — show notification when triggered by server (future use)
self.addEventListener('push', event => {
  const data = event.data?.json() ?? {
    title: 'Buti&Bita Financials',
    body: 'Você tem contas a verificar!'
  };
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: './icon-192.png',
      badge: './icon-32.png',
      tag: data.tag || 'buti-bita',
      requireInteraction: data.requireInteraction || false,
      data: { url: data.url || './' }
    })
  );
});

// Notification click — open or focus the app
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