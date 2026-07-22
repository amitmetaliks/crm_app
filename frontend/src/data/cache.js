// Read-through cache so the rep's screens show LAST-KNOWN data when offline instead of a
// blank/empty state, and so a dealer can still be picked for a visit with no signal.
//
// The offline queue (offline.js) already protects WRITES. This is its read-side counterpart:
// callCached() serves live data when possible and the last cached copy when the network is
// gone. A separate IndexedDB database keeps it isolated from the write queue.

import { reactive } from "vue"
import { call } from "./api"

const DB = "triam-crm-cache"
const STORE = "reads"

// Surfaced to the UI so a screen served from cache doesn't masquerade as live. `stale` flips
// true whenever the most recent read came from the cache (offline OR a failed live request on
// flaky signal), and false on a fresh success. App.vue shows a "showing saved data" banner.
export const cacheState = reactive({ stale: false, at: 0 })

function openDb() {
	return new Promise((resolve, reject) => {
		const req = indexedDB.open(DB, 1)
		req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: "key" })
		req.onsuccess = () => resolve(req.result)
		req.onerror = () => reject(req.error)
	})
}
async function idbGet(key) {
	// Returns the full row {key, value, at} (or undefined) so callers can read the cached-at
	// timestamp, not just the value.
	try {
		const db = await openDb()
		return await new Promise((res) => {
			const r = db.transaction(STORE, "readonly").objectStore(STORE).get(key)
			r.onsuccess = () => res(r.result || undefined)
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
	// Sort keys so a call site that orders params differently still hits the same cache entry
	// (JSON.stringify is order-sensitive). undefined-valued keys are dropped, as before.
	const p = params && typeof params === "object" ? params : {}
	const sorted = Object.keys(p)
		.filter((k) => p[k] !== undefined)
		.sort()
		.reduce((o, k) => ((o[k] = p[k]), o), {})
	return method + ":" + JSON.stringify(sorted)
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
			cacheState.stale = false
			return data
		} catch (e) {
			if (isNetworkError(e)) {
				const row = await idbGet(key)
				if (row !== undefined) {
					cacheState.stale = true
					cacheState.at = row.at || 0
					return row.value
				}
			}
			throw e
		}
	}
	const row = await idbGet(key)
	if (row !== undefined) {
		cacheState.stale = true
		cacheState.at = row.at || 0
		return row.value
	}
	throw new Error("You're offline and this screen hasn't been loaded yet.")
}

// Bound the cache: drop entries older than `maxAgeDays`. Called at startup. Cheap, and it
// stops the per-visit VisitDetail keys from growing without limit on a long-lived install.
export async function pruneCache(maxAgeDays = 21) {
	try {
		const cutoff = Date.now() - maxAgeDays * 24 * 60 * 60 * 1000
		const db = await openDb()
		const store = db.transaction(STORE, "readwrite").objectStore(STORE)
		const req = store.getAll()
		req.onsuccess = () => {
			for (const row of req.result || []) {
				if (!row.at || row.at < cutoff) store.delete(row.key)
			}
		}
	} catch (e) {
		/* best-effort */
	}
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
	const row = await idbGet(DEALERS_KEY)
	const list = (row && row.value) || []
	const ql = q.toLowerCase()
	const filtered = ql
		? list.filter((d) => (d.label || "").toLowerCase().includes(ql) || (d.id || "").toLowerCase().includes(ql))
		: list
	return filtered.slice(0, limit)
}
