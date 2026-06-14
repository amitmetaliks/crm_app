import { createApp } from "vue"
import { setConfig, frappeRequest, resourcesPlugin } from "frappe-ui"
import router from "./router"
import App from "./App.vue"
import "./index.css"
import { applyStoredTheme } from "./utils/theme"
import { initOffline } from "./data/offline"
import { startTracking } from "./data/tracker"
import { initLock } from "./data/lock"

applyStoredTheme()
initLock()
initOffline()
startTracking()

// Route all frappe-ui resources through the Frappe request helper (cookie/session auth)
setConfig("resourceFetcher", frappeRequest)

const app = createApp(App)
app.use(router)
app.use(resourcesPlugin)
app.mount("#app")

// Register the service worker (enables installability + web push)
if ("serviceWorker" in navigator) {
	window.addEventListener("load", () => {
		navigator.serviceWorker.register("/assets/crm_app/frontend/sw.js").catch(() => {})
	})
}
