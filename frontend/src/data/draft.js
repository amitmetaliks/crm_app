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

const KEY = "triam-newvisit-draft"

export function saveDraft(data) {
	try {
		localStorage.setItem(KEY, JSON.stringify({ ...data, savedAt: Date.now() }))
	} catch (e) {
		/* quota / disabled storage — a lost draft must never break the visit flow */
	}
}

export function loadDraft() {
	try {
		return JSON.parse(localStorage.getItem(KEY) || "null")
	} catch (e) {
		return null
	}
}

export function clearDraft() {
	try {
		localStorage.removeItem(KEY)
	} catch (e) {
		/* ignore */
	}
}
