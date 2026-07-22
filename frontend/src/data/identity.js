// Browser storage must follow the authenticated Frappe user, not the physical phone.
// Field devices are often shared during handovers; a global cache/queue can otherwise expose
// one rep's customers or submit their saved work under the next rep's session.
export function getCookie(name) {
	const escaped = String(name).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
	const match = document.cookie.match(new RegExp("(^|;)\\s*" + escaped + "\\s*=\\s*([^;]+)"))
	return match ? decodeURIComponent(match.pop()) : null
}

export function currentUser() {
	const user = getCookie("user_id")
	return user && user !== "Guest" ? user : null
}

export function requireCurrentUser() {
	const user = currentUser()
	if (!user) throw new Error("Please sign in before saving field activity.")
	return user
}

export function userKey(user = currentUser()) {
	return user ? encodeURIComponent(user) : "guest"
}
