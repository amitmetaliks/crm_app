// Native-only (Capacitor) duty tracking. No-op on the web/PWA.
//
// Uses a LOCATION FOREGROUND SERVICE (persistent notification) rather than
// background location. Android counts a running location foreground service as
// "foreground", so the route keeps recording when the rep pockets the phone and
// the screen goes off — using only ACCESS_FINE/COARSE_LOCATION.
//
// Per Android docs: "Your app is running a foreground service... Your app retains
// access when it's placed in the background, such as when the user presses the Home
// button on their device or turns their device's display off."
//
// This deliberately avoids ACCESS_BACKGROUND_LOCATION, which would trigger Google
// Play's Permissions Declaration review (form + video demo) — see PLAY-STORE-SETUP.md.
// The notification is also honest: the rep can always see tracking is on.
//
// Tracking runs only between attendance check-IN and check-OUT ("on duty"), so it
// never records at night or on an off day. The plugin ships native code only; its JS
// API comes from registerPlugin so nothing extra is bundled into the web build.
import { Capacitor, registerPlugin } from "@capacitor/core"
import { call } from "./api"

const DUTY_KEY = "triam_duty_on"
let watcherId = null

function isNative() {
	try {
		return !!(Capacitor && Capacitor.isNativePlatform && Capacitor.isNativePlatform())
	} catch (e) {
		return false
	}
}

function plugin() {
	return registerPlugin("BackgroundGeolocation")
}

export function isDutyOn() {
	try {
		return localStorage.getItem(DUTY_KEY) === "1"
	} catch (e) {
		return false
	}
}

/** Start the on-duty foreground service. Safe to call twice. */
export async function startDutyTracking() {
	try {
		localStorage.setItem(DUTY_KEY, "1")
	} catch (e) {
		/* private mode */
	}
	if (!isNative() || watcherId) return
	try {
		watcherId = await plugin().addWatcher(
			{
				// Setting backgroundMessage is what makes the plugin run a foreground
				// service with a persistent notification (instead of needing background
				// location permission).
				backgroundMessage: "Recording your field route while you are on duty.",
				backgroundTitle: "TRIAM A+ — on duty",
				requestPermissions: true,
				stale: false,
				distanceFilter: 50,
			},
			(location, error) => {
				if (error || !location) return
				call("crm_app.tracking.record_ping", {
					latitude: location.latitude,
					longitude: location.longitude,
					accuracy: location.accuracy,
					source: "native",
					is_mock: location.simulated ? 1 : 0,
				}).catch(() => {})
			}
		)
	} catch (e) {
		watcherId = null
	}
}

/** Stop the foreground service (attendance check-out). */
export async function stopDutyTracking() {
	try {
		localStorage.removeItem(DUTY_KEY)
	} catch (e) {
		/* ignore */
	}
	if (!watcherId) return
	try {
		await plugin().removeWatcher({ id: watcherId })
	} catch (e) {
		/* already gone */
	}
	watcherId = null
}

/** Re-arm the service if the app was restarted mid-shift. Called on app boot. */
export function resumeDutyTracking() {
	if (isNative() && isDutyOn()) startDutyTracking()
}
