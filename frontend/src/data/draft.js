// In-progress visit draft persistence.
//
// A rep fills a visit write-up (dealer, orders, competitors, notes, outcome) over several
// minutes at the counter. On a cheap Android the OS can kill the backgrounded tab before they
// hit Save, and everything typed was gone — the offline queue only captures it at Save time.
// This snapshots the structured write-up to localStorage as it's typed, so it survives an
// app-kill and can be resumed.
//
// localStorage (not IndexedDB) on purpose: it's synchronous and reliable for small text, and
// there is at most ONE in-progress visit at a time. Photos are deliberately NOT persisted here
// (base64 would blow the ~5MB quota); a killed app loses only the photos, which are re-takeable,
// never the write-up.

import { currentUser, userKey } from "./identity"

function key(user = currentUser()) { return "triam-newvisit-draft:" + userKey(user) }

export function saveDraft(data) {
	try {
		if (!currentUser()) return
		localStorage.setItem(key(), JSON.stringify({ ...data, savedAt: Date.now() }))
	} catch (e) {
		/* quota / disabled storage — a lost draft must never break the visit flow */
	}
}

export function loadDraft() {
	try {
		if (!currentUser()) return null
		return JSON.parse(localStorage.getItem(key()) || "null")
	} catch (e) {
		return null
	}
}

export function clearDraft() {
	try {
		localStorage.removeItem(key())
	} catch (e) {
		/* ignore */
	}
}

export function clearDraftForUser(user) {
	if (!user) return
	try { localStorage.removeItem(key(user)) } catch (e) { /* ignore */ }
}
