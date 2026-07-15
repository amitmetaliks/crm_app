<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="bg-navy-700 px-4 pb-4 pt-5 text-white">
			<h1 class="text-lg font-semibold">{{ $t("My Route") }}</h1>
			<div class="mt-3 flex items-center justify-between">
				<button @click="shift(-1)" class="rounded-lg bg-white/10 px-3 py-1"><ChevronLeft class="h-5 w-5" /></button>
				<span class="text-sm font-medium">{{ fmtDay(date) }}</span>
				<button @click="shift(1)" class="rounded-lg bg-white/10 px-3 py-1"><ChevronRight class="h-5 w-5" /></button>
			</div>
		</header>

		<div class="mx-auto max-w-xl space-y-4 p-4">
			<Skeleton v-if="loading" :count="3" />
			<template v-else>
				<div class="aa-card text-center">
					<p class="text-3xl font-bold text-navy-700 dark:text-white">{{ route.distance_km || 0 }} km</p>
					<p class="text-xs text-gray-400">distance travelled ({{ route.points || 0 }} location points)</p>
				</div>

				<a v-if="mapsUrl" :href="mapsUrl" target="_blank" class="aa-card flex items-center justify-center gap-2 text-sm font-semibold text-saffron">
					<MapPin class="h-5 w-5" /> {{ $t("Open route in Google Maps") }} </a>

				<div>
					<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">Stops ({{ (route.stops || []).length }})</h2>
					<EmptyState v-if="!route.stops || !route.stops.length" :title='$t("No visits this day")' />
					<div v-else class="space-y-2">
						<router-link v-for="(s, i) in route.stops" :key="i" :to="{ name: 'VisitDetail', params: { name: s.name } }" class="aa-card flex items-center gap-3">
							<span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy-100 text-xs font-bold text-navy-700">{{ i + 1 }}</span>
							<div class="min-w-0 flex-1">
								<p class="truncate text-sm font-medium text-navy-700 dark:text-white">{{ s.party_display }}</p>
								<p class="text-xs text-gray-400">{{ fmtTime(s.check_in_time) }} · {{ s.visit_status }}</p>
							</div>
						</router-link>
					</div>
				</div>

				<p class="px-1 text-xs text-gray-400">Location is captured while the app is open. For always-on tracking, the app can be installed as a native Android build later.</p>
			</template>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { ChevronLeft, ChevronRight, MapPin } from "lucide-vue-next"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"

const date = ref(dayjs().format("YYYY-MM-DD"))
const route = ref({ stops: [] })
const loading = ref(true)

function fmtDay(d) { return dayjs(d).format("ddd, DD MMM YYYY") }
function fmtTime(t) { return t ? dayjs(t).format("h:mm A") : "—" }
function shift(n) { date.value = dayjs(date.value).add(n, "day").format("YYYY-MM-DD"); load() }

const mapsUrl = computed(() => {
	const pts = (route.value.stops || []).filter((s) => s.check_in_latitude && s.check_in_longitude)
	if (pts.length < 1) return null
	const coord = (s) => `${s.check_in_latitude},${s.check_in_longitude}`
	if (pts.length === 1) return `https://www.google.com/maps?q=${coord(pts[0])}`
	const origin = coord(pts[0])
	const dest = coord(pts[pts.length - 1])
	const way = pts.slice(1, -1).map(coord).join("|")
	let u = `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${dest}`
	if (way) u += `&waypoints=${encodeURIComponent(way)}`
	return u
})

async function load() {
	loading.value = true
	try { route.value = await call("crm_app.tracking.get_day_route", { date: date.value }) }
	finally { loading.value = false }
}
onMounted(load)
</script>
