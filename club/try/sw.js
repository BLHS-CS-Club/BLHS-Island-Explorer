// Lets the Try page run the island you typed, with no server behind it.
//
// The game always fetches an island from an address. This worker answers three
// kinds of request from the Try page and leaves everything else alone:
//   /grapes/try-it/...     your island, out of the browser's own storage
//   /club/try/game/...     the game's page, with the error reporter added
//   /api/...               nothing, so practice never lands in the game's records

const STORE = 'blhs-try'
const HOOK = '<script src="/club/lib/hook.js"></script>'

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)
  if (url.origin !== self.location.origin) return

  if (url.pathname.startsWith('/grapes/try-it/')) {
    event.respondWith(yours(url.pathname))
  } else if (event.request.mode === 'navigate' && url.pathname.startsWith('/club/try/game/')) {
    event.respondWith(game())
  } else if (url.pathname.startsWith('/api/')) {
    event.respondWith(new Response(null, { status: 204 }))
  }
})

async function yours(path) {
  const cache = await caches.open(STORE)
  const name = path.endsWith('/') ? `${path}island.json` : path
  const hit = await cache.match(name)
  return hit || new Response('that file is not in your island', {
    status: 404, headers: { 'Content-Type': 'text/plain' },
  })
}

async function game() {
  const res = await fetch('/index.html', { cache: 'no-store' })
  let html = await res.text()
  if (!html.includes(HOOK)) html = html.includes('<head>') ? html.replace('<head>', `<head>${HOOK}`) : HOOK + html
  return new Response(html, {
    status: 200,
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' },
  })
}
