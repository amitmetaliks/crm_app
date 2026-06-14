// Resize/compress an image File to a JPEG data URL (keeps uploads small & fast).
export function resizeImageToDataURL(file, maxSize = 512, quality = 0.82) {
	return new Promise((resolve, reject) => {
		const url = URL.createObjectURL(file)
		const img = new Image()
		img.onload = () => {
			URL.revokeObjectURL(url)
			let { width, height } = img
			if (width >= height && width > maxSize) {
				height = Math.round((height * maxSize) / width)
				width = maxSize
			} else if (height > maxSize) {
				width = Math.round((width * maxSize) / height)
				height = maxSize
			}
			const canvas = document.createElement("canvas")
			canvas.width = width
			canvas.height = height
			const ctx = canvas.getContext("2d")
			ctx.fillStyle = "#ffffff"
			ctx.fillRect(0, 0, width, height)
			ctx.drawImage(img, 0, 0, width, height)
			resolve(canvas.toDataURL("image/jpeg", quality))
		}
		img.onerror = reject
		img.src = url
	})
}
