<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="aa-page-header">
			<div class="flex items-center justify-between">
				<h1 class="text-xl font-bold">{{ $t("Today's Beat") }}</h1>
				<input type="date" v-model="date" @change="load" class="rounded-lg px-2 py-1 text-sm text-navy-700" />
			</div>
			<div v-if="beat.exists" class="mt-3">
				<div class="flex items-center justify-between text-sm">
					<span class="text-navy-100">{{ beat.title || "Beat plan" }}<span v-if="beat.beat_type" class="ml-2 rounded-full bg-white/15 px-2 py-0.5 text-[11px]">{{ beat.beat_type }}</span></span>
					<span class="font-semibold">{{ beat.visited }}/{{ beat.planned }} visited</span>
				</div>
				<div class="mt-2 h-2 w-full overflow-hidden rounded-full bg-white/20">
					<div class="h-full bg-saffron" :style="{ width: pct + '%' }"></div>
				</div>
			</div>
		</header>

		<div class="mx-auto max-w-xl space-y-3 p-4">
			<Skeleton v-if="loading" :count="4" />

			<template v-else>
				<!-- existing beat -->
				<template v-if="beat.exists && !editing">
					<div v-for="(e, i) in beat.entries" :key="i" class="aa-card">
						<div class="flex items-center justify-between">
							<div class="min-w-0">
								<p class="truncate font-semibold text-navy-700 dark:text-white">{{ e.party_name || e.customer }}</p>
								<p class="text-xs text-gray-400">{{ e.area || "—" }}</p>
							</div>
							<div class="flex shrink-0 items-center gap-2">
								<template v-if="!e.visited">
									<button
										v-if="!skipOf(e.customer)"
										class="rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-gray-500 dark:border-navy-700"
										@click="askSkip(e)"
									>{{ $t("Skip") }}</button>
									<router-link
										:to="{ name: 'NewVisit', query: { ptype: e.party_type, id: e.customer, label: e.party_name || e.customer } }"
										class="rounded-lg bg-saffron-600 px-3 py-1.5 text-xs font-semibold text-white"
									>{{ $t("Visit") }}</router-link>
								</template>
								<span v-else class="flex items-center gap-1 text-xs font-semibold text-green-600">
									<CheckCircle2 class="h-4 w-4" /> {{ $t("Done") }} </span>
							</div>
						</div>
						<!-- Skipped: show the reason and let him undo it -->
						<div v-if="skipOf(e.customer) && !e.visited" class="mt-2 flex items-center justify-between rounded-lg bg-amber-50 px-2 py-1.5 text-xs text-amber-900">
							<span class="min-w-0 truncate">{{ $t("Skipped") }}: {{ $t(skipOf(e.customer).skip_reason) }}</span>
							<button class="shrink-0 font-semibold text-amber-700 underline" @click="undoSkip(e)">{{ $t("Undo") }}</button>
						</div>
					</div>
					<button @click="optimize" :disabled="optimizing" class="aa-card w-full text-center text-sm font-medium text-navy-700 dark:text-white">
						{{ optimizing ? "Optimizing…" : "🧭 Optimize route" }}
					</button>
					<div v-if="optStops.length" class="aa-card">
						<div class="mb-2 flex items-center justify-between">
							<p class="text-sm font-semibold text-navy-600 dark:text-navy-200">Suggested order · {{ optTotal }} km</p>
							<a v-if="optMaps" :href="optMaps" target="_blank" class="text-xs font-medium text-saffron">{{ $t("Maps") }}</a>
						</div>
						<div v-for="s in optStops" :key="s.customer" class="flex items-center gap-2 py-1 text-sm">
							<span class="flex h-6 w-6 items-center justify-center rounded-full bg-saffron/15 text-xs font-bold text-saffron">{{ s.seq }}</span>
							<span class="truncate text-navy-700 dark:text-white">{{ s.party_name }}</span>
						</div>
					</div>
					<button @click="startEdit" class="aa-card w-full text-center text-sm font-medium text-saffron">{{ $t("Edit beat") }}</button>
				</template>

				<EmptyState v-else-if="!beat.exists && !editing" :title='$t("No beat planned")' :subtitle='$t("Plan the dealers you&#39;ll visit today.")'>
					<button @click="startEdit" class="aa-btn-primary !py-2 text-sm">{{ $t("Plan beat") }}</button>
				</EmptyState>

				<!-- editor -->
				<template v-if="editing">
					<div class="aa-card">
						<div class="mb-2 flex gap-2">
							<button @click="beatType = 'Primary'" class="flex-1 rounded-lg py-2 text-sm font-medium" :class="beatType === 'Primary' ? 'bg-saffron-600 text-white' : 'bg-gray-100 text-gray-600'">{{ $t("Primary") }}</button>
							<button @click="beatType = 'Secondary'" class="flex-1 rounded-lg py-2 text-sm font-medium" :class="beatType === 'Secondary' ? 'bg-saffron-600 text-white' : 'bg-gray-100 text-gray-600'">{{ $t("Secondary") }}</button>
						</div>
						<input v-model="title" class="aa-input mb-2" :placeholder='$t("Beat title (e.g. North zone)")' />
						<input v-model="territory" class="aa-input mb-2" :placeholder='$t("Territory (e.g. West Bengal)")' />
						<input v-model="q" @input="onSearch" class="aa-input" :placeholder='$t("Add dealer…")' />
						<ul v-if="results.length" class="mt-2 divide-y divide-gray-100">
							<li v-for="r in results" :key="r.id" @click="addStop(r)" class="flex cursor-pointer items-center justify-between py-2 text-sm">
								<span class="text-navy-700 dark:text-white">{{ r.label }}</span>
								<Plus class="h-4 w-4 text-saffron" />
							</li>
						</ul>
					</div>
					<div v-for="(s, i) in stops" :key="i" class="aa-card flex items-center justify-between">
						<span class="text-sm text-navy-700 dark:text-white">{{ s.party_name }}</span>
						<button @click="stops.splice(i, 1)"><Trash2 class="h-4 w-4 text-gray-400" /></button>
					</div>
					<div class="flex gap-2">
						<button @click="editing = false" class="flex-1 rounded-xl bg-gray-200 py-3 text-sm font-medium text-gray-600">{{ $t("Cancel") }}</button>
						<button @click="saveBeat" :disabled="busy" class="aa-btn-primary flex-1 !py-3 text-sm">{{ $t("Save beat") }}</button>
					</div>
				</template>
			</template>
		</div>

		<!-- Skip reason sheet: one tap, because a rep does this standing outside a shut shop -->
		<div v-if="skipFor" class="fixed inset-0 z-50 flex items-end bg-black/40" @click.self="skipFor = null">
			<div class="w-full rounded-t-2xl bg-white p-4 dark:bg-navy-800" style="padding-bottom: calc(1rem + env(safe-area-inset-bottom))">
				<p class="mb-1 font-semibold text-navy-700 dark:text-white">{{ $t("Why skip this stop?") }}</p>
				<p class="mb-3 truncate text-xs text-gray-400">{{ skipFor.party_name || skipFor.customer }}</p>
				<button
					v-for="r in reasons"
					:key="r"
					class="mb-2 w-full rounded-xl border px-3 py-3 text-left text-sm font-medium"
					:class="skipReason === r ? 'border-saffron bg-saffron/10 text-saffron' : 'border-gray-200 text-navy-700 dark:border-navy-700 dark:text-white'"
					@click="skipReason = r"
				>{{ $t(r) }}</button>
				<input v-if="skipReason === 'Other'" v-model="skipOther" class="aa-input mb-2 w-full" :placeholder='$t("Say what happened")' />
				<div class="flex gap-2">
					<button class="flex-1 rounded-xl bg-gray-200 py-3 text-sm font-medium text-gray-600" @click="skipFor = null">{{ $t("Cancel") }}</button>
					<button
						class="aa-btn-primary flex-1 !py-3 text-sm"
						:disabled="!skipReason || skipping"
						@click="confirmSkip"
					>{{ skipping ? $t("Saving…") : $t("Save") }}</button>
				</div>
			</div>
		</div>

		<BottomNav />
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue"
import { CheckCircle2, Plus, Trash2 } from "lucide-vue-next"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { getPosition } from "../utils/geo"
import { toast } from "../utils/toast"

const date = ref(dayjs().format("YYYY-MM-DD"))
const beat = ref({ exists: false, entries: [], planned: 0, visited: 0 })
const loading = ref(true)
const editing = ref(false)
const title = ref("")
const beatType = ref("Primary")
const territory = ref("")
const stops = reactive([])
const q = ref("")
const results = ref([])
const busy = ref(false)
// Skip: reasons mirror the incumbent's vocabulary so their history can migrate 1:1.
const reasons = ["Shop Closed", "Owner Not Available", "No Stock Required", "Credit Limit Exceeded", "Location Not Accessible", "Other"]
const skips = ref([])
const skipFor = ref(null)
const skipReason = ref("")
const skipOther = ref("")
const skipping = ref(false)
const optimizing = ref(false)
const optStops = ref([])
const optTotal = ref(0)
let timer = null

const pct = computed(() => (beat.value.planned ? Math.round((beat.value.visited / beat.value.planned) * 100) : 0))
const optMaps = computed(() => {
	const pts = optStops.value
	if (!pts.length) return null
	const coord = (s) => `${s.lat},${s.lng}`
	if (pts.length === 1) return `https://www.google.com/maps?q=${coord(pts[0])}`
	const way = pts.slice(1, -1).map(coord).join("|")
	let u = `https://www.google.com/maps/dir/?api=1&origin=${coord(pts[0])}&destination=${coord(pts[pts.length - 1])}`
	if (way) u += `&waypoints=${encodeURIComponent(way)}`
	return u
})

async function optimize() {
	optimizing.value = true
	try {
		const pos = await getPosition()
		const res = await call("crm_app.beat.optimize_beat", { plan_date: date.value, start_lat: pos.latitude, start_lng: pos.longitude })
		optStops.value = res.stops || []
		optTotal.value = res.total_km || 0
		if (!optStops.value.length) toast.info("Add dealer locations to optimize the route")
	} catch (e) {
		toast.error("Could not optimize")
	} finally { optimizing.value = false }
}

async function load() {
	loading.value = true
	editing.value = false
	try {
		beat.value = await call("crm_app.beat.get_my_beat", { plan_date: date.value })
		try {
			skips.value = await call("crm_app.skips.get_my_skips", { skip_date: date.value })
		} catch (e) {
			skips.value = [] // never let a skip lookup take the beat down with it
		}
	} finally {
		loading.value = false
	}
}

function skipOf(customer) {
	return skips.value.find((s) => s.customer === customer)
}

function askSkip(entry) {
	skipFor.value = entry
	skipReason.value = ""
	skipOther.value = ""
}

async function confirmSkip() {
	skipping.value = true
	try {
		let pos = {}
		try {
			pos = await getPosition()
		} catch (e) {
			/* a shut shop is worth recording even without a fix */
		}
		await call("crm_app.skips.skip_stop", {
			customer: skipFor.value.customer,
			skip_reason: skipReason.value,
			other_reason: skipOther.value || null,
			skip_date: date.value,
			beat_plan: beat.value.name || null,
			latitude: pos.latitude ?? null,
			longitude: pos.longitude ?? null,
		})
		skipFor.value = null
		await load()
	} catch (e) {
		toast.error(e?.messages?.[0] || "Could not save the skip")
	} finally {
		skipping.value = false
	}
}

async function undoSkip(entry) {
	try {
		await call("crm_app.skips.unskip", { customer: entry.customer, skip_date: date.value })
		await load()
	} catch (e) {
		toast.error("Could not undo")
	}
}
function startEdit() {
	title.value = beat.value.title || ""
	beatType.value = beat.value.beat_type || "Primary"
	territory.value = beat.value.territory || ""
	stops.splice(0, stops.length)
	;(beat.value.entries || []).forEach((e) =>
		stops.push({ party_type: e.party_type, customer: e.customer, party_name: e.party_name || e.customer, area: e.area })
	)
	editing.value = true
}
function onSearch() {
	clearTimeout(timer)
	if (q.value.trim().length < 2) { results.value = []; return }
	timer = setTimeout(async () => {
		results.value = (await call("crm_app.customers.search_parties", { query: q.value, party_type: "Customer", limit: 10 })) || []
	}, 300)
}
function addStop(r) {
	if (!stops.find((s) => s.customer === r.id)) stops.push({ party_type: "Customer", customer: r.id, party_name: r.label, area: r.sub })
	q.value = ""
	results.value = []
}
async function saveBeat() {
	busy.value = true
	try {
		await call("crm_app.beat.save_beat", {
			name: beat.value.name || undefined,
			plan_date: date.value,
			title: title.value,
			beat_type: beatType.value,
			territory: territory.value,
			entries: JSON.stringify(stops),
		})
		toast.success("Beat saved")
		await load()
	} catch (e) {
		toast.error(e?.messages?.[0] || "Could not save beat")
	} finally {
		busy.value = false
	}
}
onMounted(load)
</script>
