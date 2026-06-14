// WhatsApp deep-link sharing (free; opens WhatsApp with a pre-filled message).
// Defaults to India (+91) when a bare 10-digit number is given.
export function waLink(phone, text) {
	let p = String(phone || "").replace(/[^0-9]/g, "")
	if (p.length === 10) p = "91" + p
	if (p.length === 11 && p.startsWith("0")) p = "91" + p.slice(1)
	const base = p ? `https://wa.me/${p}` : "https://wa.me/"
	return `${base}?text=${encodeURIComponent(text || "")}`
}

export function openWhatsApp(phone, text) {
	window.open(waLink(phone, text), "_blank")
}
