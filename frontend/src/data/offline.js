import { reactive } from "vue"
import { call } from "./api"

// Reactive network/sync state for the UI banner.
//   pending — queued writes still waiting to sync
//   failed  — writes the SERVER rejected (validation); held for the rep to see, not dropped
export const net = reactive({ online: navigator.onLine, pending: 0, failed: 0, syncing: false })

const DB_NAME = "triam-crm"
const STORE = "queue"

function openDb() {
	return new Promise((resolve, reject) => {
		const req = indexedDB.open(DB_NAME, 1)
		req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: "id", autoIncrement: true })
		req.onsuccess = () => resolve(req.result)
		req.onerror = () => reject(req.error)
	})
}
async function store(mode) {
	const db = await openDb()
	return db.transaction(STORE, mode).objectStore(STORE)
}
async function addRec(rec) {
	const s = await store("readwrite")
	return new Promise((res, rej) => {
		const r = s.add(rec)
		r.onsuccess = () => res(r.result)
		r.onerror = () => rej(r.error)
	})
}
async function putRec(rec) {
	const s = await store("readwrite")
	return new Promise((res, rej) => {
		const r = s.put(rec)
		r.onsuccess = () => res(r.result)
		r.onerror = () => rej(r.error)
	})
}
async function allRecs() {
	const s = await store("readonly")
	return new Promise((res) => {
		const r = s.getAll()
		r.onsuccess = () => res(r.result || [])
		r.onerror = () => res([])
	})
}
async function delRec(id) {
	const s = await store("readwrite")
	s.delete(id)
}
async function refresh() {
	try {
		const all = await allRecs()
		net.pending = all.filter((r) => !r.failed).length
		net.failed = all.filter((r) => r.failed).length
	} catch (e) {
		/* db unavailable — leave counts as-is */
	}
}

// A stable per-submission key. Minted ONCE, before the first attempt, and carried on every
// retry — this is the client half of server-side idempotency. Without it, a write that
// COMMITTED but whose response was lost would be retried under a fresh identity and create a
// duplicate (a second attendance punch, a second — reimbursable — expense claim). The server
// (crm_app/idempotency.py) dedupes on this key. Visits carry their own client_ref, so this is
// harmless extra there: submit_full_visit simply ignores the arg.
function newKey() {
	try {
		if (globalThis.crypto?.randomUUID) return crypto.randomUUID()
	} catch (e) {
		/* fall through */
	}
	return "k" + Date.now().toString(36) + Math.random().toString(36).slice(2, 10)
}
function ensureIdem(params) {
	const p = params && typeof params === "object" ? params : {}
	if (p.idempotency_key) return p
	return { ...p, idempotency_key: newKey() }
}

export async function enqueue(method, params, label) {
	await addRec({ method, params: ensureIdem(params), label: label || method, ts: Date.now(), attempts: 0 })
	await refresh()
}

function isNetworkError(e) {
	if (!navigator.onLine) return true
	const m = (e && (e.message || e.exc || "")) + ""
	return e?.name === "TypeError" || /network|fetch|failed to fetch|load failed/i.test(m)
}

// Classify a replay failure. The whole point: only "permanent" ever stops a record from
// being retried, and NOTHING is ever silently deleted. Everything else is transient and
// the same record is tried again on the next flush.
//
//   network   — offline / connection dropped. The write may or may not have committed;
//               keep it and retry. (Backend idempotency, noted below, would remove the
//               small duplicate risk when a commit's RESPONSE is what got lost.)
//   auth      — session expired / CSRF / permission. Recoverable by re-login; keep the
//               record and STOP the run so we don't hammer a dead session.
//   server    — 5xx / deadlock / timestamp mismatch. Transient on the server side; keep.
//   permanent — the server DELIBERATELY rejected this exact payload (validation, mandatory
//               field, duplicate, bad link). Retrying byte-for-byte will fail identically,
//               so flag it as failed and show the rep — but still never delete it.
function classify(e) {
	if (isNetworkError(e)) return "network"
	const status = Number(e?.httpStatus || e?.status || e?.statusCode || 0)
	const type = ((e?.exc_type || "") + "").toLowerCase()
	const text = (
		(Array.isArray(e?.messages) ? e.messages.join(" ") : "") +
		" " +
		(e?.message || e?.exc || e?._server_messages || "")
	).toLowerCase()
	const blob = type + " " + text

	if (
		status === 401 ||
		status === 403 ||
		/permissionerror|csrf|not permitted|please (log ?in|login)|session (expired|stopped)|authentication/.test(blob)
	)
		return "auth"
	if (status >= 500 || /deadlock|timestampmismatch|timeout|internalservererror/.test(blob)) return "server"
	// Anything else the server returned deterministically is permanent for this payload.
	return "permanent"
}

function reasonOf(e) {
	if (Array.isArray(e?.messages) && e.messages.length) return e.messages.join(" ").slice(0, 200)
	return ((e?.message || e?.exc_type || "Rejected by server") + "").slice(0, 200)
}

// Online → call directly; offline or network failure → queue and return a marker.
// The idempotency key is stamped BEFORE the first attempt and reused if we fall through to
// the queue, so the retry carries the SAME key as the request that may have already
// committed — closing the lost-response duplicate window.
export async function callOrQueue(method, params, label) {
	const p = ensureIdem(params)
	if (navigator.onLine) {
		try {
			return await call(method, p)
		} catch (e) {
			if (isNetworkError(e)) {
				await enqueue(method, p, label)
				return { queued: true }
			}
			throw e
		}
	}
	await enqueue(method, p, label)
	return { queued: true }
}

export async function flush() {
	if (net.syncing || !navigator.onLine) return
	net.syncing = true
	try {
		const items = await allRecs()
		for (const it of items) {
			if (it.failed) continue // waiting for an explicit retry from the rep
			try {
				await call(it.method, it.params)
				await delRec(it.id)
			} catch (e) {
				const kind = classify(e)
				// Transient (network / server) or a dead session: stop the whole run and
				// try the entire queue again later. Never touch the record.
				if (kind === "network" || kind === "server" || kind === "auth") break
				// Permanent: the server rejected THIS payload and will again. Flag it so the
				// rep can see and fix/retry/discard — but keep the data. Move on so one bad
				// record can't wedge everything behind it.
				it.failed = true
				it.error = reasonOf(e)
				it.errorAt = Date.now()
				it.attempts = (it.attempts || 0) + 1
				await putRec(it)
			}
		}
	} finally {
		net.syncing = false
		await refresh()
	}
}

// ── For a "Sync errors" UI: list, retry, discard ────────────────────────────
export async function failedRecs() {
	return (await allRecs()).filter((r) => r.failed)
}
export async function retryItem(id) {
	const all = await allRecs()
	const it = all.find((r) => r.id === id)
	if (it) {
		delete it.failed
		delete it.error
		await putRec(it)
		await refresh()
		flush()
	}
}
// Explicit, rep-initiated delete — the ONLY path that removes a record on purpose.
export async function discardItem(id) {
	await delRec(id)
	await refresh()
}
// Clear the failed flag on every held record and try again (e.g. after the rep fixed a
// server-side cause, or a validation rule was corrected). Data is never lost by this.
export async function retryFailed() {
	const all = await allRecs()
	for (const it of all) {
		if (it.failed) {
			delete it.failed
			delete it.error
			await putRec(it)
		}
	}
	await refresh()
	flush()
}

export function initOffline() {
	window.addEventListener("online", () => { net.online = true; flush() })
	window.addEventListener("offline", () => { net.online = false })
	refresh()
	if (navigator.onLine) flush()
	// Safety: periodic flush attempt.
	setInterval(() => { if (navigator.onLine) flush() }, 30000)
}
