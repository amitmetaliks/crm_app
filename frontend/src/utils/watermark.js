// Stamp date/time/GPS (+any lines) onto a photo for tamper-evidence.
// Takes a JPEG/PNG data URL, returns a new JPEG data URL with a footer band.
export function watermark(dataUrl, lines = []) {
	return new Promise((resolve) => {
		if (!dataUrl || !lines.length) return resolve(dataUrl)
		const img = new Image()
		img.onload = () => {
			const canvas = document.createElement("canvas")
			canvas.width = img.width
			canvas.height = img.height
			const ctx = canvas.getContext("2d")
			ctx.drawImage(img, 0, 0)
			const pad = Math.max(8, Math.round(img.width * 0.02))
			const fs = Math.max(13, Math.round(img.width * 0.03))
			const lh = fs + 6
			const bandH = lines.length * lh + pad
			ctx.fillStyle = "rgba(21,38,76,0.55)"
			ctx.fillRect(0, img.height - bandH, img.width, bandH)
			ctx.fillStyle = "#ffffff"
			ctx.font = `600 ${fs}px Arial, sans-serif`
			ctx.textBaseline = "alphabetic"
			lines.forEach((ln, i) => {
				ctx.fillText(ln, pad, img.height - pad - (lines.length - 1 - i) * lh)
			})
			resolve(canvas.toDataURL("image/jpeg", 0.82))
		}
		img.onerror = () => resolve(dataUrl)
		img.src = dataUrl
	})
}
