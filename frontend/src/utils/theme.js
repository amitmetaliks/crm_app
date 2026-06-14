const KEY = "aa-theme"

export function applyStoredTheme() {
	const t = localStorage.getItem(KEY)
	const dark =
		t === "dark" ||
		(!t && window.matchMedia?.("(prefers-color-scheme: dark)")?.matches)
	document.documentElement.classList.toggle("dark", !!dark)
}

export function isDark() {
	return document.documentElement.classList.contains("dark")
}

export function setDark(dark) {
	document.documentElement.classList.toggle("dark", dark)
	localStorage.setItem(KEY, dark ? "dark" : "light")
	return dark
}
