// TRIAM A+ CRM — service worker (web push + installability)
self.addEventListener("install", () => self.skipWaiting())
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()))
// Minimal fetch handler (required for installability); lets the browser handle requests.
self.addEventListener("fetch", () => {})

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
