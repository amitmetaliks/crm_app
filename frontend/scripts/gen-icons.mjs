// Generates TRIAM A+ app icons (navy square + saffron "A+"), matching the brand.
// PWA icons need a legible SQUARE mark; the full horizontal logo is used on the
// login/splash instead. Run: node scripts/gen-icons.mjs
import sharp from "sharp"

const NAVY = "#15264C"
const SAFFRON = "#E8541C"

function iconSvg(size, { maskable = false } = {}) {
	const radius = maskable ? size * 0.5 : size * 0.22 // maskable: full-bleed circle-safe
	const pad = maskable ? size * 0.18 : size * 0.0
	const fontSize = size * (maskable ? 0.42 : 0.5)
	const triam = size * 0.13
	return Buffer.from(`
<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <rect x="${pad}" y="${pad}" width="${size - pad * 2}" height="${size - pad * 2}" rx="${radius}" fill="${NAVY}"/>
  <text x="50%" y="51%" text-anchor="middle" dominant-baseline="central"
        font-family="Arial, Helvetica, sans-serif" font-weight="800"
        font-size="${fontSize}" fill="${SAFFRON}">A+</text>
  <text x="50%" y="${size - pad - size * 0.13}" text-anchor="middle" dominant-baseline="central"
        font-family="Arial, Helvetica, sans-serif" font-weight="700" letter-spacing="${size * 0.01}"
        font-size="${triam}" fill="#FFFFFF">TRIAM</text>
</svg>`)
}

async function write(size, opts, out) {
	await sharp(iconSvg(size, opts)).png().toFile(out)
	console.log("wrote", out)
}

await write(192, {}, "public/icon-192.png")
await write(512, {}, "public/icon-512.png")
await write(512, { maskable: true }, "public/icon-512-maskable.png")
await write(180, {}, "public/apple-touch-icon.png")
