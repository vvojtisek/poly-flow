/* Cache only immutable, same-origin Next.js assets. Never cache pages or API responses. */
const STATIC_CACHE = "polyflow-static-v1";

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const names = await caches.keys();
      await Promise.all(names.filter((name) => name.startsWith("polyflow-static-") && name !== STATIC_CACHE).map((name) => caches.delete(name)));
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(assetFirst(request));
  } else if (request.mode === "navigate") {
    event.respondWith(networkFirst(request));
  }
});

async function assetFirst(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  if (response.ok && response.type === "basic") await cache.put(request, response.clone());
  return response;
}

async function networkFirst(request) {
  try {
    return await fetch(request);
  } catch {
    return new Response(
      `<!doctype html><html lang="cs"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#f8fafc"><title>PolyFlow · bez připojení</title><body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#f8fafc;color:#0f172a;font:16px/1.6 system-ui,sans-serif"><main style="max-width:28rem;margin:1rem;padding:2rem;border:1px solid #cbd5e1;border-radius:1.5rem;background:white;text-align:center"><p style="font-size:2rem;margin:0">PolyFlow</p><h1 style="font-size:1.25rem">Připojení k serveru vypadlo</h1><p>Osobní obsah ani odpovědi nejsou uložené offline. Počkej na obnovení spojení a zkus stránku znovu.</p><button onclick="location.reload()" style="padding:.7rem 1rem;border:0;border-radius:.7rem;background:#2563eb;color:white;font:inherit;font-weight:600">Zkusit znovu</button></main></body></html>`,
      { status: 200, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } },
    );
  }
}
