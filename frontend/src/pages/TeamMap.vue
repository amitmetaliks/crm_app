<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="flex items-center justify-between bg-navy-700 px-4 py-4 text-white">
			<div class="flex items-center gap-3">
				<button @click="$router.back()"><ChevronLeft class="h-6 w-6" /></button>
				<h1 class="text-lg font-semibold">Team — Live</h1>
			</div>
			<button @click="load" class="rounded-lg bg-white/10 px-3 py-1.5 text-xs">Refresh</button>
		</header>

		<div class="mx-auto max-w-xl p-4">
			<EmptyState v-if="!session.isSalesManager" title="Managers only" />
			<template v-else>
				<div ref="mapEl" class="h-72 w-full overflow-hidden rounded-2xl border border-gray-200"></div>
				<p class="mt-2 px-1 text-xs text-gray-400">Latest known location today ({{ reps.length }} rep(s) reporting). Updates when reps' app is open.</p>
				<div class="mt-3 space-y-2">
					<div v-for="r in reps" :key="r.sales_person" class="aa-card flex items-center justify-between">
						<div>
							<p class="text-sm font-medium text-navy-700 dark:text-white">{{ r.name }}</p>
							<p class="text-xs text-gray-400">Last seen {{ fmtTime(r.time) }}</p>
						</div>
						<a :href="`https://www.google.com/maps?q=${r.lat},${r.lng}`" target="_blank" class="text-xs font-medium text-saffron">Map</a>
					</div>
					<EmptyState v-if="!loading && !reps.length" title="No reps reporting yet" subtitle="Locations appear once reps open the app today." />
				</div>
			</template>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { ChevronLeft } from "lucide-vue-next"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import EmptyState from "../components/EmptyState.vue"
import { session } from "../data/session"
import { call } from "../data/api"

const reps = ref([])
const loading = ref(true)
const mapEl = ref(null)
let map = null
let L = null
let markers = []

function fmtTime(t) { return t ? dayjs(t).format("h:mm A") : "" }

async function ensureMap() {
	if (map) return
	L = (await import("leaflet")).default
	await import("leaflet/dist/leaflet.css")
	map = L.map(mapEl.value).setView([22.5726, 88.3639], 6)
	L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
		attribution: "© OpenStreetMap",
		maxZoom: 19,
	}).addTo(map)
}

function draw() {
	markers.forEach((m) => map.removeLayer(m))
	markers = []
	const pts = []
	reps.value.forEach((r) => {
		const mk = L.circleMarker([r.lat, r.lng], { radius: 8, color: "#E8541C", fillColor: "#E8541C", fillOpacity: 0.85 })
			.addTo(map)
			.bindPopup(`<b>${r.name}</b><br>${fmtTime(r.time)}`)
		markers.push(mk)
		pts.push([r.lat, r.lng])
	})
	if (pts.length) map.fitBounds(pts, { padding: [40, 40], maxZoom: 14 })
}

async function load() {
	if (!session.isSalesManager) { loading.value = false; return }
	loading.value = true
	try {
		reps.value = (await call("crm_app.dashboards.get_live_team")).reps || []
		await ensureMap()
		draw()
	} finally {
		loading.value = false
	}
}
onMounted(load)
</script>
