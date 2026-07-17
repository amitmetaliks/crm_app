module.exports = {
	darkMode: "class",
	presets: [require("frappe-ui/src/utils/tailwind.config")],
	content: [
		"./index.html",
		"./src/**/*.{vue,js,ts,jsx,tsx}",
		"./node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}",
	],
	theme: {
		extend: {
			// Palette shared with the HR app, deliberately identical (owner's call: "the
			// colour combination of the HR App is far better, let's stick to it").
			//
			// This is not only a taste decision — it is the safer engineering one. The HR
			// palette has already been through a WCAG contrast pass over a live app, so its
			// numbers are measured rather than derived, and the two apps now read as one
			// suite to the reps who use both.
			//
			// The TRIAM logo keeps its own orange/navy: it sits on its own white plate
			// (.aa-logo-pill), so the mark stays true to the brand while the app chrome is
			// the quieter Amit Alliance tone around it.
			colors: {
				// Amit Alliance brand — Slate Blue (quieter enterprise tone, replacing the
				// earlier deep navy; same token names, so every bg-navy-*/text-navy-* class
				// already written across the app recolors automatically).
				navy: {
					50: "#eff1f6",
					100: "#d8dde9",
					200: "#b0bbd4",
					300: "#8999be",
					400: "#6178a8",
					500: "#4c608a",
					600: "#3b4a6b",
					DEFAULT: "#3b4a6b",
					700: "#2d3952",
					800: "#21293b",
					850: "#19202e",
					900: "#121721",
					// Dark-mode surfaces
					950: "#0d1017",     // app background in dark mode
					surface: "#181e2b", // card surface in dark mode
					hover: "#222b3f",   // card hover in dark mode
				},
				// Amit Alliance brand — muted amber (replacing the earlier saturated
				// saffron; used sparingly for CTAs/highlights, not as a dominant fill).
				saffron: {
					50: "#fcf5e9",
					100: "#f7e6ca",
					200: "#efce95",
					300: "#e7b55f",
					400: "#e3a945",
					500: "#e09f2e",
					DEFAULT: "#e09f2e",
					600: "#c8891e",
					700: "#a06e18",
					800: "#7c5613",
					900: "#593d0d",
				},
			},
			fontFamily: {
				sans: [
					"Inter",
					"-apple-system",
					"BlinkMacSystemFont",
					"Segoe UI",
					"Roboto",
					"sans-serif",
				],
			},
		},
	},
	plugins: [],
}
