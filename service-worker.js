/* ====== LIBAS PWA Service Worker ====== */
/* bump when you change UI/JS so users get updates */
const SW_VERSION = 'v1.0.2';
const APP_CACHE = `libas-app-${SW_VERSION}`;
const RUNTIME_CACHE = `libas-runtime-${SW_VERSION}`;

/* App shell: keep the UI available offline */
const APP_SHELL = [
  '/',                      // your Flask home route (libas.html)
  '/static/manifest.json',
  '/static/logo.png',       // optional, fine if missing
  '/static/icon-192.png',
  '/static/icon-512.png'
];

/* Install: pre-cache app shell */
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(APP_CACHE).then(cache => cache.addAll(APP_SHELL))
  );
  // no skipWaiting here; page shows banner and asks to activate
});

/* Activate: delete old caches */
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => ![APP_CACHE, RUNTIME_CACHE].includes(k)).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

/* Message from page: activate immediately */
self.addEventListener('message', event => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();
});

/* Fetch strategy:
   - /api/search: network-first (cache fallback)
   - everything else: cache-first (network fallback) */
self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith('/api/search')) {
    event.respondWith(networkFirst(req));
  } else {
    event.respondWith(cacheFirst(req));
  }
});

async function cacheFirst(req) {
  const cache = await caches.open(APP_CACHE);
  const cached = await cache.match(req);
  if (cached) return cached;
  try {
    const fresh = await fetch(req);
    if (req.method === 'GET' && fresh.ok) cache.put(req, fresh.clone());
    return fresh;
  } catch (e) {
    if (req.mode === 'navigate') {
      const fallback = await cache.match('/');
      if (fallback) return fallback;
    }
    throw e;
  }
}

async function networkFirst(req) {
  const cache = await caches.open(RUNTIME_CACHE);
  try {
    const fresh = await fetch(req);
    if (req.method === 'GET' && fresh.ok) cache.put(req, fresh.clone());
    return fresh;
  } catch (e) {
    const cached = await cache.match(req);
    if (cached) return cached;
    return new Response(JSON.stringify({ items: [] }), {
      headers: { 'Content-Type': 'application/json' }, status: 200
    });
  }
}
