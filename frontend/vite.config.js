import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import path from "path"

// Dev backend (used only by `npm run dev` proxy). Production is served same-origin.
const DEV_BACKEND = "https://hrdev.34-93-148-147.sslip.io"

export default defineConfig({
	base: "/assets/crm_app/frontend/",
	server: {
		port: 8080,
		allowedHosts: true,
		proxy: {
			"^/(api|assets|files|private|app)": {
				target: DEV_BACKEND,
				changeOrigin: true,
				secure: true,
			},
		},
	},
	plugins: [vue()],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
	},
	build: {
		outDir: "../crm_app/public/frontend",
		emptyOutDir: true,
		// The service worker reads this manifest after an online launch and precaches every
		// route chunk. That makes "offline" mean the whole app, not only screens visited before.
		// Emit at the outDir root (NOT the default .vite/ dot-directory, which Frappe's static
		// server refuses to serve — a 404 there silently disables the whole precache).
		manifest: "manifest.json",
		target: "es2015",
		sourcemap: false,
		commonjsOptions: {
			include: [/tailwind.config.js/, /node_modules/],
		},
	},
})
