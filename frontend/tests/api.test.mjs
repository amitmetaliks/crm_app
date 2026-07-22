import test from "node:test"
import assert from "node:assert/strict"

import { call, serverMessages } from "../src/data/api.js"

test("decodes Frappe server messages", () => {
	const payload = {
		_server_messages: JSON.stringify([
			JSON.stringify({ message: "Customer is required" }),
			JSON.stringify({ message: "Please retry" }),
		]),
	}
	assert.deepEqual(serverMessages(payload), ["Customer is required", "Please retry"])
})

test("posts authenticated JSON with the CSRF token", async (t) => {
	globalThis.window = { csrf_token: "csrf-123" }
	globalThis.fetch = async (url, options) => {
		assert.equal(url, "/api/method/crm_app.api.ping")
		assert.equal(options.method, "POST")
		assert.equal(options.credentials, "same-origin")
		assert.equal(options.headers["X-Frappe-CSRF-Token"], "csrf-123")
		assert.deepEqual(JSON.parse(options.body), { value: 7 })
		return { ok: true, status: 200, json: async () => ({ message: { pong: true } }) }
	}
	t.after(() => {
		delete globalThis.fetch
		delete globalThis.window
	})

	assert.deepEqual(await call("crm_app.api.ping", { value: 7 }), { pong: true })
})

test("exposes structured authorization errors for queue classification", async (t) => {
	globalThis.window = { csrf_token: "" }
	globalThis.fetch = async () => ({
		ok: false,
		status: 403,
		json: async () => ({
			exc_type: "PermissionError",
			_server_messages: JSON.stringify([JSON.stringify({ message: "Not permitted" })]),
		}),
	})
	t.after(() => {
		delete globalThis.fetch
		delete globalThis.window
	})

	await assert.rejects(
		() => call("crm_app.orders.create_order", {}),
		(error) => error.message === "Not permitted" && error.exc_type === "PermissionError" && error.httpStatus === 403,
	)
})
