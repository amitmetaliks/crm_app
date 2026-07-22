import { createApp } from "vue"
import router from "./router"
import App from "./App.vue"
import "./index.css"
import { applyStoredTheme } from "./utils/theme"
import { initOffline } from "./data/offline"
import { prefetchDealers, pruneCache } from "./data/cache"
import { startTracking } from "./data/tracker"
import { initLock } from "./data/lock"
import { resumeDutyTracking } from "./data/native"
import { t } from "./data/i18n"

applyStoredTheme()
initLock()
initOffline()
startTracking()
resumeDutyTracking()
prefetchDealers() // cache the rep's dealer list so visits can be started offline
pruneCache() // drop read-cache entries older than a few weeks (bounds IndexedDB growth)

const app = createApp(App)
// $t reads the locale ref during render, so switching language re-renders in place.
app.config.globalProperties.$t = t
app.use(router)
app.mount("#app")

// Register the service worker (app-shell caching for offline open + web push).
// Served at /sw.js (root path) but scoped to /amit-crm so it controls ONLY this app and
// never the HR app or Frappe desk on the same site.
if ("serviceWorker" in navigator) {
	window.addEventListener("load", () => {
		navigator.serviceWorker.register("/sw.js", { scope: "/amit-crm" }).catch(() => {})
	})
}
