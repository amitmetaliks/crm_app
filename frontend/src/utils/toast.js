import { reactive } from "vue"

export const toasts = reactive([])
let _id = 0

export function showToast(message, type = "info", timeout = 3000) {
	if (!message) return
	const t = { id: ++_id, message: String(message), type }
	toasts.push(t)
	setTimeout(() => {
		const i = toasts.findIndex((x) => x.id === t.id)
		if (i !== -1) toasts.splice(i, 1)
	}, timeout)
}

export const toast = {
	success: (m) => showToast(m, "success"),
	error: (m) => showToast(m, "error"),
	info: (m) => showToast(m, "info"),
}
