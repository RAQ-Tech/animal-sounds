const CACHE_NAME = "animal-sounds-{{ version }}";
const SHELL = {{ assets | tojson }};

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith("animal-sounds-") && key !== CACHE_NAME).map(key => caches.delete(key))
  )).then(() => self.clients.claim()));
});
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  // Save only the bundled shell. Settings and personal recordings stay on the server.
  if (event.request.method !== "GET" || url.origin !== self.location.origin ||
      url.pathname.startsWith("/api/") || url.pathname.startsWith("/config/")) return;
  if (event.request.mode === "navigate") {
    event.respondWith(fetch(event.request).catch(() => caches.match("/")));
  } else if (SHELL.includes(url.pathname + url.search)) {
    event.respondWith(caches.match(event.request).then(saved => saved || fetch(event.request)));
  }
});
