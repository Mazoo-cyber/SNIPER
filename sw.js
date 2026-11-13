const CACHE_NAME = 'binance-scanner-v42';
const STATIC_ASSETS = ['./manifest.json', './icon.svg'];

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(STATIC_ASSETS)).catch(() => {}));
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// دائماً جلب أحدث تقرير من الإنترنت أولاً، واستخدام النسخة المحفوظة فقط عند انقطاع الشبكة.
// الكاش مقصور على النطاق الذاتي (التقرير/الأصول) — لا يُخزَّن أي طلب لواجهات API الخارجية (بايننس/OKX)
// لتفادي تضخم الكاش وتقديم بيانات سعرية قديمة من الكاش.
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const sameOrigin = event.request.url.startsWith(self.location.origin);
  if (!sameOrigin) return;
  event.respondWith(
    fetch(event.request, { cache: 'no-store' })
      .then(resp => {
        const clone = resp.clone();
        caches.open(CACHE_NAME).then(async c => {
          await c.put(event.request, clone);
          // حد حجم بسيط: أقدم من 40 ملفاً يُحذف
          const keys = await c.keys();
          if (keys.length > 40) {
            for (const k of keys.slice(0, keys.length - 40)) await c.delete(k);
          }
        }).catch(() => {});
        return resp;
      })
      .catch(() => caches.match(event.request))
  );
});
