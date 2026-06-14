import { createResource } from "frappe-ui"

// Imperative one-shot call to a whitelisted method. Returns the message payload.
export function call(method, params) {
	return createResource({ url: method }).submit(params)
}
