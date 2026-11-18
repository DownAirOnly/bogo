/* bogo. network-first service worker.
 * Always request the live app shell and catalog. A cached copy is used only
 * when the network is unavailable, never as the preferred update source.
 */
const SHELL_CACHE = "bogo-shell-v1";
const ROOT = new URL("./", self.registration.scope).href;
const CORE_FILE = /\/(?:index\.html|app\.js|style\.css|deploy\.json|deals\.json|manifest\.webmanifest)$/;

function canonicalKey(request) {
  if (request.mode === "navigate") return ROOT;
  const url = new URL(request.url);
  url.search = "";
  url.hash = "";
  return url.href;
}

async function networkFirst(request) {
  const key = canonicalKey(request);
  try {
    const response = await fetch(new Request(request, {cache: "no-store"}));
    if (response.ok && response.type === "basic") {
      try {
        const cache = await caches.open(SHELL_CACHE);
        await cache.put(key, response.clone());
      } catch (error) {
        // Browsers may restrict storage; network responses still work.
        console.debug("bogo cache write skipped", error);
      }
    }
    return response;
  } catch (error) {
    const cached = await caches.match(key);
    if (cached) return cached;
    throw error;
  }
}

self.addEventListener("install", event => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(name => name.startsWith("bogo-shell-") && name !== SHELL_CACHE)
      .map(name => caches.delete(name)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (request.mode !== "navigate" && !CORE_FILE.test(url.pathname)) return;
  event.respondWith(networkFirst(request));
});
