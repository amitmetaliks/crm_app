import { reactive } from "vue"

const PIN = "aacrm_pin"
const BIO = "aacrm_bio_id"
const TS = "aacrm_lock_ts"
const TIMEOUT_MS = 2 * 60 * 1000 // re-lock after 2 min in background

export const lock = reactive({ locked: false })

async function sha(s) {
	const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s))
	return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("")
}

export function hasPin() {
	return !!localStorage.getItem(PIN)
}
export async function setPin(pin) {
	localStorage.setItem(PIN, await sha(pin))
}
export function clearLock() {
	localStorage.removeItem(PIN)
	localStorage.removeItem(BIO)
	lock.locked = false
}
export async function verifyPin(pin) {
	return hasPin() && (await sha(pin)) === localStorage.getItem(PIN)
}
export function unlock() {
	lock.locked = false
	localStorage.setItem(TS, String(Date.now()))
}

function rand(n = 32) {
	const a = new Uint8Array(n)
	crypto.getRandomValues(a)
	return a
}
function b64(buf) {
	return btoa(String.fromCharCode(...new Uint8Array(buf)))
}
function unb64(s) {
	return Uint8Array.from(atob(s), (c) => c.charCodeAt(0))
}

export function bioSupported() {
	return !!(window.PublicKeyCredential && navigator.credentials && location.protocol === "https:")
}
export function bioEnabled() {
	return !!localStorage.getItem(BIO)
}
export async function enableBio() {
	if (!bioSupported()) return false
	try {
		const cred = await navigator.credentials.create({
			publicKey: {
				challenge: rand(),
				rp: { name: "TRIAM A+" },
				user: { id: rand(16), name: "triam-rep", displayName: "TRIAM A+" },
				pubKeyCredParams: [{ type: "public-key", alg: -7 }, { type: "public-key", alg: -257 }],
				authenticatorSelection: { authenticatorAttachment: "platform", userVerification: "required" },
				timeout: 60000,
			},
		})
		localStorage.setItem(BIO, b64(cred.rawId))
		return true
	} catch (e) {
		return false
	}
}
export function disableBio() {
	localStorage.removeItem(BIO)
}
export async function bioUnlock() {
	const id = localStorage.getItem(BIO)
	if (!id) return false
	try {
		await navigator.credentials.get({
			publicKey: {
				challenge: rand(),
				allowCredentials: [{ id: unb64(id), type: "public-key" }],
				userVerification: "required",
				timeout: 60000,
			},
		})
		unlock()
		return true
	} catch (e) {
		return false
	}
}

export function initLock() {
	if (hasPin()) lock.locked = true
	document.addEventListener("visibilitychange", () => {
		if (document.hidden) {
			localStorage.setItem(TS, String(Date.now()))
		} else if (hasPin()) {
			const t = parseInt(localStorage.getItem(TS) || "0", 10)
			if (Date.now() - t > TIMEOUT_MS) lock.locked = true
		}
	})
}
