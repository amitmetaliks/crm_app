// Lightweight Frappe request client. The app previously shipped all of frappe-ui (~209 kB
// gzip) solely for createResource/frappeRequest; a field CRM on weak mobile data should not
// pay that cost for a small authenticated POST helper.

export function serverMessages(payload) {
	const messages = []
	try {
		const outer = JSON.parse(payload?._server_messages || "[]")
		for (const value of outer) {
			try {
				const parsed = typeof value === "string" ? JSON.parse(value) : value
				if (parsed?.message) messages.push(parsed.message)
			} catch (e) {
				if (value) messages.push(String(value))
			}
		}
	} catch (e) { /* no structured server messages */ }
	if (!messages.length && payload?.message && typeof payload.message === "string") messages.push(payload.message)
	return messages
}

export async function call(method, params = {}) {
	let response
	try {
		response = await fetch(`/api/method/${method}`, {
			method: "POST",
			credentials: "same-origin",
			headers: {
				Accept: "application/json",
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": window.csrf_token || "",
			},
			body: JSON.stringify(params || {}),
		})
	} catch (error) {
		// Keep a TypeError-shaped network failure: offline.js intentionally recognizes it.
		throw error
	}

	let payload = {}
	let parsed = false
	try { payload = await response.json(); parsed = true } catch (e) { /* non-JSON proxy/server response */ }
	if (parsed === false && response.ok) {
		// A 200 with a non-JSON body is not a Frappe API response — almost always a captive
		// portal / proxy interstitial. Surface it as a NETWORK failure (TypeError-shaped, which
		// offline.js/cache.js treat as offline) so the caller retries or serves last-known data,
		// rather than returning `undefined` and caching it as if it were fresh.
		const err = new TypeError("Network returned a non-JSON response (captive portal?)")
		throw err
	}
	if (!response.ok || payload.exc || payload.exception) {
		const messages = serverMessages(payload)
		const error = new Error(messages[0] || payload.exc_type || `Request failed (${response.status})`)
		error.messages = messages
		error.exc_type = payload.exc_type || payload.exception || ""
		error.exc = payload.exc || ""
		error.httpStatus = response.status
		throw error
	}
	return payload.message
}

// Small compatibility surface for session resources; intentionally not a reactive framework.
export function createRequestResource({ url, makeParams, onSuccess }) {
	return {
		async submit(params = {}) {
			const result = await call(url, makeParams ? makeParams(params) : params)
			if (onSuccess) onSuccess(result)
			return result
		},
	}
}
