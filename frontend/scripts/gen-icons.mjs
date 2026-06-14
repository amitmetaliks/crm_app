// Generates TRIAM A+ PWA icons from the real logo (public/logo-full.jpg) and a
// cropped horizontal wordmark for in-app headers. Run: node scripts/gen-icons.mjs
import sharp from "sharp"

const LOGO = "public/logo-full.jpg"
const WHITE = { r: 255, g: 255, b: 255, alpha: 1 }

async function makeIcon(size, scale, out) {
	const inner = Math.round(size * scale)
	const logo = await sharp(LOGO).resize(inner, inner, { fit: "inside", background: WHITE }).toBuffer()
	await sharp({ create: { width: size, height: size, channels: 4, background: WHITE } })
		.composite([{ input: logo, gravity: "center" }])
		.png()
		.toFile(out)
	console.log("wrote", out)
}

await makeIcon(192, 0.94, "public/icon-192.png")
await makeIcon(512, 0.94, "public/icon-512.png")
await makeIcon(512, 0.74, "public/icon-512-maskable.png") // extra safe-zone padding
await makeIcon(180, 0.94, "public/apple-touch-icon.png")

// Cropped "TRIAM A+" wordmark (top band, ~51% of height) for in-app headers.
const meta = await sharp(LOGO).metadata()
const bandH = Math.round(meta.height * 0.51)
await sharp(LOGO)
	.extract({ left: 0, top: 0, width: meta.width, height: bandH })
	.png()
	.toFile("src/assets/logo-wordmark.png")
console.log("wrote src/assets/logo-wordmark.png")
