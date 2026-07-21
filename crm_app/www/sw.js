// TRIAM A+ CRM — service worker: app-shell caching (offline open) + web push.
//
// Served at /sw.js (from crm_app/www) so its script scope is the site root, then REGISTERED
// with scope "/amit-crm" (see frontend/src/main.js). That narrow scope is deliberate: this
// worker controls ONLY the CRM pages and their subresource fetches — it never sees /amit-hr,
// the Frappe desk, or any other app on this shared site, so it cannot affect them.
//
// Why this file exists: the previous worker's fetch handler was a no-op, so nothing cached
// the app shell — a rep who lost the tab on a cheap Android could not reopen the app offline
// at all, which made the whole IndexedDB offline queue moot. This caches the shell + hashed
// assets so the app boots offline; the IndexedDB queue then handles the writes.

const CACHE = "triam-crm-shell-v1"
const SHELL = "/amit-crm" // the SPA entry HTML; served for every /amit-crm/* deep link
const ASSET_PREFIX = "/assets/crm_app/frontend/"

self.addEventListener("install", () => self.skipWaiting())

self.addEventListener("activate", (event) => {
	event.waitUntil(
		(async () => {
			// Drop older versions of OUR cache only; never touch other apps' caches.
			const keys = await caches.keys()
			await Promise.all(
				keys.filter((k) => k.startsWith("triam-crm-") && k !== CACHE).map((k) => caches.delete(k))
			)
			await self.clients.claim()
		})()
	)
})

function isCrmAsset(url) {
	return url.origin === self.location.origin && url.pathname.startsWith(ASSET_PREFIX)
}

self.addEventListener("fetch", (event) => {
	const req = event.request
	if (req.method !== "GET") return // never intercept writes; the app's IndexedDB queue owns those
	const url = new URL(req.url)

	// App-shell navigations: network-first so an online rep always gets the latest shell, but
	// fall back to the cached shell when offline so the app still opens. One cached entry
	// (SHELL) serves every /amit-crm/* client route — the SPA does the in-app routing.
	if (req.mode === "navigate") {
		event.respondWith(
			(async () => {
				try {
					const res = await fetch(req)
					const cache = await caches.open(CACHE)
					cache.put(SHELL, res.clone())
					return res
				} catch (e) {
					const cache = await caches.open(CACHE)
					return (await cache.match(SHELL)) || (await cache.match(req)) || Response.error()
				}
			})()
		)
		return
	}

	// Hashed static assets (JS/CSS/fonts under /assets/crm_app/frontend/): cache-first. The
	// filename changes on every build, so a cached hit is always the right version and a new
	// build simply fetches new filenames — no stale-asset risk.
	if (isCrmAsset(url)) {
		event.respondWith(
			(async () => {
				const cache = await caches.open(CACHE)
				const hit = await cache.match(req)
				if (hit) return hit
				try {
					const res = await fetch(req)
					if (res.ok) cache.put(req, res.clone())
					return res
				} catch (e) {
					return hit || Response.error()
				}
			})()
		)
		return
	}

	// Everything else (/api reads, images, etc.): don't intercept. Offline API reads fail and
	// the app shows its own empty/last-known state; we deliberately don't fake data here.
})

// ── Web push (unchanged from the previous worker) ──────────────────────────────
self.addEventListener("push", (event) => {
	let data = {}
	try {
		data = event.data.json()
	} catch (e) {
		data = { title: "TRIAM A+", body: event.data ? event.data.text() : "" }
	}
	const title = data.title || "TRIAM A+"
	const options = {
		body: data.body || "",
		icon: "/assets/crm_app/frontend/icon-192.png",
		badge: "/assets/crm_app/frontend/icon-192.png",
		data: { url: data.url || "/amit-crm" },
		vibrate: [80, 40, 80],
	}
	event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener("notificationclick", (event) => {
	event.notification.close()
	const url = (event.notification.data && event.notification.data.url) || "/amit-crm"
	event.waitUntil(
		clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
			for (const c of list) {
				if (c.url.includes("/amit-crm") && "focus" in c) return c.focus()
			}
			if (clients.openWindow) return clients.openWindow(url)
		})
	)
})
