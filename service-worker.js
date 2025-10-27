// --- Cloudflare / API offline fallback to GitHub Mirror ---
const GITHUB_ITEMS_URL = "https://raw.githubusercontent.com/unique205/libas-site/main/items.json";

// try API first, then cached copy, then GitHub JSON
async function fetchApiOrFallback(request) {
  try {
    // Attempt live network
    const networkResponse = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, networkResponse.clone()).catch(()=>{});
    return networkResponse;
  } catch (err) {
    // If network fails, try cache
    const cached = await caches.match(request);
    if (cached) return cached;

    // Last resort → GitHub Mirror
    try {
      const ghResp = await fetch(GITHUB_ITEMS_URL);
      const body = await ghResp.text();
      return new Response(body, {
        headers: { 'Content-Type': 'application/json' }
      });
    } catch (err2) {
      return new Response(JSON.stringify({ error: "offline", items: [] }), {
        headers: { 'Content-Type': 'application/json' },
        status: 503
      });
    }
  }
}

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  if (url.pathname.startsWith('/api/search')) {
    event.respondWith(fetchApiOrFallback(event.request));
    return;
  }

  // For all other requests, use cache-first
  event.respondWith(cacheFirst(event.request));
});
