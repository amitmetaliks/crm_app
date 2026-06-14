import { call } from "./api"

// Foreground location tracking (PWA limitation: only while the app is open).
// Pings now + every 10 min + on resume. Failures are silent (e.g. no Employee).
let timer = null

function ping(source = "ping") {
	if (!navigator.geolocation || !navigator.onLine) return
	navigator.geolocation.getCurrentPosition(
		(pos) => {
			call("crm_app.tracking.record_ping", {
				latitude: pos.coords.latitude,
				longitude: pos.coords.longitude,
				accuracy: pos.coords.accuracy,
				source,
			}).catch(() => {})
		},
		() => {},
		{ enableHighAccuracy: false, timeout: 8000, maximumAge: 60000 }
	)
}

function hasSession() {
	return /(^|;)\s*user_id\s*=/.test(document.cookie) && !/user_id=Guest/.test(document.cookie)
}

export function startTracking() {
	if (!hasSession()) return
	ping("start")
	if (timer) clearInterval(timer)
	timer = setInterval(() => ping("interval"), 10 * 60 * 1000)
	document.addEventListener("visibilitychange", () => {
		if (!document.hidden) ping("resume")
	})
}
