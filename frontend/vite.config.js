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
	optimizeDeps: {
		// frappe-ui pulls in feather-icons (CJS); force pre-bundling so the dev
		// server resolves its default export (production/rollup build is unaffected).
		include: ["feather-icons", "showdown", "prismjs", "frappe-ui"],
	},
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
	},
	build: {
		outDir: "../crm_app/public/frontend",
		emptyOutDir: true,
		target: "es2015",
		sourcemap: false,
		commonjsOptions: {
			include: [/tailwind.config.js/, /node_modules/],
		},
		rollupOptions: {
			output: {
				manualChunks: {
					"frappe-ui": ["frappe-ui"],
				},
			},
		},
	},
})
