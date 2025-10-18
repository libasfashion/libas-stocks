/* ====== LIBAS PWA Service Worker ====== */
const SW_VERSION = 'v1.0.1';               // ⬅ bump this whenever you change app shell
const APP_CACHE = `libas-app-${SW_VERSION}`;
const RUNTIME_CACHE = `libas-runtime-${SW_VERSION}`;

// App shell: cache the main page and core assets
const APP_SHELL = [
  '/',                     // homepage route (libas.html from Flask)
  '/static/manifest.json',
  '/static/logo.png'
];

// Install: cache app shell
self.addEventListener('install', event => {
  event.waitUntil(caches.open(APP_CACHE).then(cache => cache.addAll(APP_SHELL)));
  // do NOT skipWaiting here — we’ll let the page decide when to activate (safer UX)
});

// Activate: clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => ![APP_CACHE, RUNTIME_CACHE].includes(k)).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Listen for page messages (to trigger immediate activate)
self.addEventListener('message', event => {
  if (event.data === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Fetch handler
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
      const cachedHome = await cache.match('/');
      if (cachedHome) return cachedHome;
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
