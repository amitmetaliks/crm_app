// Native-only bridge (Capacitor). No-op on the web/PWA.
// In the native Android build it runs ALWAYS-ON background GPS and posts pings
// (with a mock-location flag) even when the app is backgrounded.
// The background-geolocation plugin ships native code only; its JS API is obtained
// via Capacitor's registerPlugin (so nothing extra is bundled for the web build).
import { Capacitor, registerPlugin } from "@capacitor/core"
import { call } from "./api"

export async function startNative() {
	try {
		if (!Capacitor || !Capacitor.isNativePlatform || !Capacitor.isNativePlatform()) return
	} catch (e) {
		return
	}
	try {
		const BackgroundGeolocation = registerPlugin("BackgroundGeolocation")
		await BackgroundGeolocation.addWatcher(
			{
				backgroundMessage: "TRIAM A+ is recording your field route.",
				backgroundTitle: "TRIAM A+ tracking",
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
		/* plugin unavailable */
	}
}
