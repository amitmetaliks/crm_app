// Read-through cache so the rep's screens show LAST-KNOWN data when offline instead of a
// blank/empty state, and so a dealer can still be picked for a visit with no signal.
//
// The offline queue (offline.js) already protects WRITES. This is its read-side counterpart:
// callCached() serves live data when possible and the last cached copy when the network is
// gone. A separate IndexedDB database keeps it isolated from the write queue.

import { call } from "./api"

const DB = "triam-crm-cache"
const STORE = "reads"

function openDb() {
	return new Promise((resolve, reject) => {
		const req = indexedDB.open(DB, 1)
		req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: "key" })
		req.onsuccess = () => resolve(req.result)
		req.onerror = () => reject(req.error)
	})
}
async function idbGet(key) {
	try {
		const db = await openDb()
		return await new Promise((res) => {
			const r = db.transaction(STORE, "readonly").objectStore(STORE).get(key)
			r.onsuccess = () => res(r.result ? r.result.value : undefined)
			r.onerror = () => res(undefined)
		})
	} catch (e) {
		return undefined
	}
}
function idbPut(key, value) {
	// Fire-and-forget: a cache write must never delay or fail the read it came from.
	openDb()
		.then((db) => db.transaction(STORE, "readwrite").objectStore(STORE).put({ key, value, at: Date.now() }))
		.catch(() => {})
}

function isNetworkError(e) {
	if (!navigator.onLine) return true
	const m = (e && (e.message || e.exc || "")) + ""
	return e?.name === "TypeError" || /network|fetch|failed to fetch|load failed/i.test(m)
}
function keyOf(method, params) {
	return method + ":" + JSON.stringify(params || {})
}

// Live when possible, last-known when offline. Returns the SAME payload shape as call(), so a
// page swaps call -> callCached with no other change. Throws only when offline AND nothing was
// ever cached — the same failure the page already handles into its empty state.
export async function callCached(method, params) {
	const key = keyOf(method, params)
	if (navigator.onLine) {
		try {
			const data = await call(method, params)
			idbPut(key, data)
			return data
		} catch (e) {
			if (isNetworkError(e)) {
				const c = await idbGet(key)
				if (c !== undefined) return c
			}
			throw e
		}
	}
	const c = await idbGet(key)
	if (c !== undefined) return c
	throw new Error("You're offline and this screen hasn't been loaded yet.")
}

// ── Dealer directory for offline visit-pick ────────────────────────────────────
const DEALERS_KEY = "dealers:list"

// Pull the rep's dealer list once (online) and keep it, so the picker works offline.
export async function prefetchDealers() {
	if (!navigator.onLine) return
	try {
		const list = await call("crm_app.customers.list_my_parties", {})
		if (Array.isArray(list)) idbPut(DEALERS_KEY, list)
	} catch (e) {
		/* best-effort */
	}
}

// Server search when online; local filter over the cached list when offline. Same result
// shape as search_parties ({party_type,id,label,sub,phone}).
export async function searchDealers(query, party_type = "Customer", limit = 10) {
	const q = (query || "").trim()
	if (navigator.onLine) {
		try {
			return (await call("crm_app.customers.search_parties", { query: q, party_type, limit })) || []
		} catch (e) {
			if (!isNetworkError(e)) throw e
		}
	}
	const list = (await idbGet(DEALERS_KEY)) || []
	const ql = q.toLowerCase()
	const filtered = ql
		? list.filter((d) => (d.label || "").toLowerCase().includes(ql) || (d.id || "").toLowerCase().includes(ql))
		: list
	return filtered.slice(0, limit)
}
