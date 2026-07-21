import { createResource } from "frappe-ui"

// One worker, served at root and scoped to the CRM (see main.js + crm_app/www/sw.js).
const SW_URL = "/sw.js"
const SW_SCOPE = "/amit-crm"

function callMethod(url, params) {
	return createResource({ url }).submit(params)
}

function urlBase64ToUint8Array(base64String) {
	const padding = "=".repeat((4 - (base64String.length % 4)) % 4)
	const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/")
	const raw = atob(base64)
	return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)))
}

export function pushSupported() {
	return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window
}

function isIOS() {
	return /iphone|ipad|ipod/i.test(navigator.userAgent)
}
function isStandalone() {
	return (
		window.matchMedia?.("(display-mode: standalone)")?.matches ||
		window.navigator.standalone === true
	)
}

// Resolve once the registration has an ACTIVE worker. Kept as an explicit wait (rather than
// serviceWorker.ready) so enabling push never blocks on controller handoff timing.
function waitForActive(reg, timeoutMs = 12000) {
	return new Promise((resolve) => {
		if (reg.active) return resolve(reg.active)
		const worker = reg.installing || reg.waiting
		const done = (v) => resolve(v)
		const timer = setTimeout(() => done(reg.active || null), timeoutMs)
		if (!worker) {
			clearTimeout(timer)
			return resolve(reg.active || null)
		}
		worker.addEventListener("statechange", () => {
			if (worker.state === "activated") {
				clearTimeout(timer)
				done(worker)
			}
		})
	})
}

export async function enablePush() {
	if (!pushSupported()) {
		throw new Error("Notifications aren't supported on this browser.")
	}
	if (isIOS() && !isStandalone()) {
		throw new Error(
			"On iPhone: tap Share → Add to Home Screen, then open the app from that icon and try again."
		)
	}

	// 1) Ask permission first (must be inside the tap gesture)
	let perm = Notification.permission
	if (perm === "default") perm = await Notification.requestPermission()
	if (perm !== "granted") {
		throw new Error("Notification permission was not granted. Enable it in your browser settings.")
	}

	// 2) Register SW and wait for it to become active (bounded, never hangs)
	const reg = await navigator.serviceWorker.register(SW_URL, { scope: SW_SCOPE })
	await waitForActive(reg)

	// 3) Subscribe (reuse existing subscription if present)
	const { public_key } = await callMethod("crm_app.push.get_vapid_public_key")
	let sub = await reg.pushManager.getSubscription()
	if (!sub) {
		sub = await reg.pushManager.subscribe({
			userVisibleOnly: true,
			applicationServerKey: urlBase64ToUint8Array(public_key),
		})
	}

	// 4) Save on the server
	await callMethod("crm_app.push.save_push_subscription", { subscription: JSON.stringify(sub) })
	return true
}

export async function disablePush() {
	try {
		await callMethod("crm_app.push.disable_push")
	} catch (e) {
		/* ignore */
	}
	const reg = await navigator.serviceWorker.getRegistration(SW_SCOPE)
	if (reg) {
		const sub = await reg.pushManager.getSubscription()
		if (sub) await sub.unsubscribe()
	}
	return true
}

export async function showTestNotification() {
	if (!("Notification" in window)) throw new Error("Notifications not supported here.")
	if (Notification.permission !== "granted") {
		const p = await Notification.requestPermission()
		if (p !== "granted") throw new Error("Notification permission is OFF for this site/browser.")
	}
	const reg =
		(await navigator.serviceWorker.getRegistration(SW_SCOPE)) ||
		(await navigator.serviceWorker.register(SW_URL, { scope: SW_SCOPE }))
	await waitForActive(reg)
	await reg.showNotification("TRIAM A+", {
		body: "Local test notification ✅ If you see this, notifications work!",
		icon: "/assets/crm_app/frontend/icon-192.png",
		badge: "/assets/crm_app/frontend/icon-192.png",
		vibrate: [80, 40, 80],
	})
	return true
}

export async function isPushEnabled() {
	if (!pushSupported()) return false
	try {
		const reg = await navigator.serviceWorker.getRegistration(SW_SCOPE)
		if (!reg) return false
		const sub = await reg.pushManager.getSubscription()
		return !!sub && Notification.permission === "granted"
	} catch (e) {
		return false
	}
}
