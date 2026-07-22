import { reactive } from "vue"
import { createRequestResource } from "./api"
import { currentUser } from "./identity"

export const session = reactive({
	user: currentUser(),
	employee: null,
	employeeName: "",
	isSalesManager: false,
	hasEmployee: false,
	gateLoaded: false,
	get isLoggedIn() {
		return !!this.user
	},
})

const meRes = createRequestResource({ url: "crm_app.api.whoami" })

// Load the logged-in rep's profile (employee + manager flag). A user without an
// Employee record can log in but cannot record visits — the UI surfaces this.
export async function refreshMe() {
	try {
		const d = await meRes.submit()
		session.employee = (d && d.employee && d.employee.name) || null
		session.employeeName = (d && d.employee && d.employee.employee_name) || ""
		session.isSalesManager = !!(d && d.is_sales_manager)
		session.hasEmployee = !!session.employee
	} catch (e) {
		session.employee = null
		session.hasEmployee = false
	} finally {
		session.gateLoaded = true
	}
}

export const loginResource = createRequestResource({
	url: "login",
	makeParams({ email, password }) {
		return { usr: email, pwd: password }
	},
	onSuccess() {
		session.user = currentUser()
		session.gateLoaded = false
		import("./offline").then((m) => m.onIdentityChanged()).catch(() => {})
		import("./cache").then((m) => m.prefetchDealers()).catch(() => {})
	},
})

export const logoutResource = createRequestResource({
	url: "logout",
	onSuccess() {
		const signedOutUser = session.user
		session.user = null
		session.employee = null
		session.hasEmployee = false
		session.gateLoaded = false
		// Stop the foreground GPS pings + resume listener; they must not keep reading the
		// signed-out user's location.
		import("./tracker").then((m) => m.stopTracking()).catch(() => {})
		// Read caches and drafts may contain customer financial data. Remove them on explicit
		// logout; the write queue is retained but remains sealed to its originating account.
		import("./cache").then((m) => m.clearUserCache(signedOutUser)).catch(() => {})
		import("./draft").then((m) => m.clearDraftForUser(signedOutUser)).catch(() => {})
		import("./offline").then((m) => m.onIdentityChanged()).catch(() => {})
	},
})
