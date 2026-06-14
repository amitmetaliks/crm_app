import { reactive } from "vue"
import { call } from "./api"

// Reactive network/sync state for the UI banner.
export const net = reactive({ online: navigator.onLine, pending: 0, syncing: false })

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
	try { net.pending = (await allRecs()).length } catch (e) { /* */ }
}

export async function enqueue(method, params, label) {
	await addRec({ method, params, label: label || method, ts: Date.now() })
	await refresh()
}

function isNetworkError(e) {
	if (!navigator.onLine) return true
	const m = (e && (e.message || e.exc || "")) + ""
	return e?.name === "TypeError" || /network|fetch|failed to fetch|load failed/i.test(m)
}

// Online → call directly; offline or network failure → queue and return a marker.
export async function callOrQueue(method, params, label) {
	if (navigator.onLine) {
		try {
			return await call(method, params)
		} catch (e) {
			if (isNetworkError(e)) {
				await enqueue(method, params, label)
				return { queued: true }
			}
			throw e
		}
	}
	await enqueue(method, params, label)
	return { queued: true }
}

export async function flush() {
	if (net.syncing || !navigator.onLine) return
	net.syncing = true
	try {
		const items = await allRecs()
		for (const it of items) {
			try {
				await call(it.method, it.params)
				await delRec(it.id)
			} catch (e) {
				if (isNetworkError(e)) break // still offline — stop, retry later
				await delRec(it.id) // non-network (validation) error: drop so it can't wedge the queue
			}
		}
	} finally {
		net.syncing = false
		await refresh()
	}
}

export function initOffline() {
	window.addEventListener("online", () => { net.online = true; flush() })
	window.addEventListener("offline", () => { net.online = false })
	refresh()
	if (navigator.onLine) flush()
	// Safety: periodic flush attempt.
	setInterval(() => { if (navigator.onLine) flush() }, 30000)
}
