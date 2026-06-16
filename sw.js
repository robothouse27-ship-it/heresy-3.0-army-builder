/* Asuryani Playtest — offline service worker.
   Precaches the app shell + encrypted rules bundle so the app installs and runs
   fully offline. Navigation = network-first (so a redeploy shows up), static
   assets = cache-first. Bump CACHE to force clients onto a new build. */
const CACHE = "asuryani-v12";
const ASSETS = [
  "./", "./index.html", "./manifest.webmanifest",
  "./app/data.enc.js", "./Eldar_Rune.webp",
  "./app/icons/icon-192.png", "./app/icons/icon-512.png", "./app/icons/apple-touch-icon.png"
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req).then(r => { const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp)); return r; })
        .catch(() => caches.match(req).then(m => m || caches.match("./index.html")))
    );
    return;
  }
  e.respondWith(
    caches.match(req).then(m => m || fetch(req).then(r => {
      if (r.ok && url.origin === location.origin) {
        const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp));
      }
      return r;
    }))
  );
});
