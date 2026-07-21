import { reactive } from "vue"
import { createResource } from "frappe-ui"

function getCookie(name) {
	const match = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)")
	return match ? decodeURIComponent(match.pop()) : null
}

function currentUserFromCookie() {
	const u = getCookie("user_id")
	return u && u !== "Guest" ? u : null
}

export const session = reactive({
	user: currentUserFromCookie(),
	employee: null,
	employeeName: "",
	isSalesManager: false,
	hasEmployee: false,
	gateLoaded: false,
	get isLoggedIn() {
		return !!this.user
	},
})

const meRes = createResource({ url: "crm_app.api.whoami" })

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

export const loginResource = createResource({
	url: "login",
	makeParams({ email, password }) {
		return { usr: email, pwd: password }
	},
	onSuccess() {
		session.user = currentUserFromCookie()
		session.gateLoaded = false
	},
})

export const logoutResource = createResource({
	url: "logout",
	onSuccess() {
		session.user = null
		session.employee = null
		session.hasEmployee = false
		session.gateLoaded = false
		// Stop the foreground GPS pings + resume listener; they must not keep reading the
		// signed-out user's location.
		import("./tracker").then((m) => m.stopTracking()).catch(() => {})
	},
})
