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
			colors: {
				// Amit Alliance brand — Navy Blue
				navy: {
					50: "#eef1f7",
					100: "#d3dbea",
					200: "#a7b6d5",
					300: "#7b91bf",
					400: "#4f6caa",
					500: "#2f4d8c",
					600: "#223a6b",
					700: "#15264c",
					DEFAULT: "#15264c",
					800: "#0f1c39",
					900: "#0a1326",
				},
				// Amit Alliance brand — Reddish Saffron / Orange
				saffron: {
					50: "#fdeee7",
					100: "#fad3c2",
					200: "#f5a888",
					300: "#f17d4e",
					400: "#ee6630",
					500: "#e8541c",
					DEFAULT: "#e8541c",
					600: "#c44415",
					700: "#963310",
					800: "#69240b",
					900: "#3b1406",
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
