// Indian currency formatting.
export function num(n) {
	return Number(n || 0).toLocaleString("en-IN")
}

export function inr(n) {
	return "₹" + num(n)
}

// Compact headline format: ₹1.25 Cr / ₹3.4 L / ₹12.5K / ₹450
export function inrShort(n) {
	n = Number(n || 0)
	const a = Math.abs(n)
	if (a >= 1e7) return "₹" + (n / 1e7).toFixed(2).replace(/\.?0+$/, "") + " Cr"
	if (a >= 1e5) return "₹" + (n / 1e5).toFixed(2).replace(/\.?0+$/, "") + " L"
	if (a >= 1e3) return "₹" + (n / 1e3).toFixed(1).replace(/\.0$/, "") + "K"
	return "₹" + num(n)
}
