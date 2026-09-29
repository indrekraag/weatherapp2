/* Madise Ilmaradar (phone) — app-shell service worker.
 *
 * NETWORK-FIRST, and for the page itself only. Every navigation goes to the
 * server first, so a new deploy is picked up exactly as it would be without
 * a service worker; the copy kept here is used only when that request
 * fails. Then an offline launch from the home screen — or the hourly reload
 * during an outage — paints the last page instead of the browser's
 * "cannot open the page" screen, and the page renders its cached data under
 * its age labels.
 *
 * Everything else — Open-Meteo, the data-branch bundles, NOAA, tarktee,
 * radar and map tiles, the Leaflet CDN, the page's own reachability check —
 * is never intercepted: no respondWith(), so the browser fetches it exactly
 * as if this file did not exist. (The page keeps its data in localStorage.)
 *
 * The previous worker (May 2026, cache 'ilmaradar-v1') served the page
 * stale-while-revalidate — always one deploy behind — and was no longer
 * registered after the redesign. This file has the same URL and scope, so
 * a phone that still holds that registration gets this one as an update.
 *
 * Shared origin: wa1 (the iPad kiosk) lives at indrekraag.github.io/weatherapp/
 * on the same origin and keeps its own cache, 'madise-shell-*'. This worker
 * only ever touches caches named 'wa2-shell-*' and the old 'ilmaradar-*'.
 *
 * Registered from index.html on https only (GitHub Pages). The ⟲ button's
 * hardRefresh() unregisters it and deletes its cache. ES5 on purpose, like
 * index.html.
 */
var SHELL_CACHE = 'wa2-shell-v1';

/* One entry per document: '/weatherapp2/' and '/weatherapp2/index.html' are
   the same page, and a query string never names a different one. */
function shellKey(url){
  var u = new URL(url);
  var path = u.pathname;
  if(path.charAt(path.length - 1) === '/') path += 'index.html';
  return u.origin + path;
}

function keepCopy(key, res){
  return caches.open(SHELL_CACHE).then(function(c){ return c.put(key, res); });
}

self.addEventListener('install', function(event){
  // Take the page into the cache straight away, so the very first outage
  // after install is already covered. Best effort: a failure here must not
  // block installing.
  var page = new URL('./', self.location.href).href;
  event.waitUntil(
    fetch(page, { cache: 'no-cache', credentials: 'same-origin' }).then(function(res){
      if(res.ok && !res.redirected) return keepCopy(shellKey(page), res);
    }).then(null, function(){}).then(function(){ return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function(event){
  event.waitUntil(
    caches.keys().then(function(names){
      return Promise.all(names.filter(function(n){
        return (n.indexOf('wa2-shell-') === 0 && n !== SHELL_CACHE)
            || n.indexOf('ilmaradar-') === 0;          // the May worker's caches
      }).map(function(n){ return caches.delete(n); }));
    }).then(function(){ return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function(event){
  var req = event.request;
  if(req.method !== 'GET' || req.mode !== 'navigate') return;
  var key = shellKey(req.url);
  event.respondWith(
    fetch(req).then(function(res){
      // Only a plain same-origin 200 is worth keeping — never an error
      // page or a redirect.
      if(res.ok && res.type === 'basic' && !res.redirected){
        var saving = keepCopy(key, res.clone()).then(null, function(){});
        try { event.waitUntil(saving); } catch(e){}
      }
      return res;
    }, function(err){
      return caches.open(SHELL_CACHE).then(function(c){
        return c.match(key);
      }).then(function(hit){
        if(hit) return hit;
        throw err;
      });
    })
  );
});
