<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="flex items-center gap-3 bg-navy-700 px-4 py-4 text-white">
			<button @click="$router.back()"><ChevronLeft class="h-6 w-6" /></button>
			<h1 class="truncate text-lg font-semibold">{{ v?.party_display || name }}</h1>
		</header>

		<div v-if="loading" class="mx-auto max-w-xl p-4"><Skeleton :count="4" /></div>

		<div v-else-if="v" class="mx-auto max-w-xl space-y-4 p-4">
			<div class="aa-card space-y-1">
				<div class="flex items-center justify-between">
					<span class="rounded-full px-2.5 py-1 text-xs font-semibold" :class="badge">{{ v.visit_status }}</span>
					<span class="text-xs text-gray-400">{{ formatDate(v.visit_date) }}</span>
				</div>
				<p class="pt-1 text-lg font-bold text-navy-700 dark:text-white">{{ v.party_display }}</p>
				<p class="text-sm text-gray-500">{{ v.visit_purpose }}<span v-if="v.outcome"> · {{ v.outcome }}</span></p>
				<p v-if="v.contact_name" class="text-sm text-gray-500">{{ v.contact_name }} {{ v.contact_phone }}</p>
			</div>

			<div class="aa-card grid grid-cols-2 gap-3 text-sm">
				<div>
					<p class="text-xs text-gray-400">Check-in</p>
					<p class="font-medium text-navy-700 dark:text-white">{{ formatTime(v.check_in_time) }}</p>
					<a v-if="inLink" :href="inLink" target="_blank" class="text-xs text-saffron">View on map</a>
				</div>
				<div>
					<p class="text-xs text-gray-400">Check-out</p>
					<p class="font-medium text-navy-700 dark:text-white">{{ formatTime(v.check_out_time) || "—" }}</p>
					<p v-if="v.duration_minutes" class="text-xs text-gray-400">{{ v.duration_minutes }} min</p>
				</div>
			</div>

			<div v-if="v.notes || v.next_action" class="aa-card space-y-2 text-sm">
				<div v-if="v.notes"><p class="text-xs text-gray-400">Notes</p><p class="text-navy-700 dark:text-white">{{ v.notes }}</p></div>
				<div v-if="v.next_action"><p class="text-xs text-gray-400">Next action</p><p class="text-navy-700 dark:text-white">{{ v.next_action }}{{ v.next_visit_date ? " (" + formatDate(v.next_visit_date) + ")" : "" }}</p></div>
			</div>

			<div v-if="photos.length" class="aa-card">
				<p class="mb-2 text-sm font-semibold text-navy-600 dark:text-navy-200">Photos</p>
				<div class="flex flex-wrap gap-2">
					<img v-for="(p, i) in photos" :key="i" :src="p.image" class="h-24 w-24 rounded-lg object-cover" />
				</div>
			</div>

			<div v-if="orders.length" class="aa-card">
				<p class="mb-2 text-sm font-semibold text-navy-600 dark:text-navy-200">Orders / Inquiries</p>
				<div v-for="(o, i) in orders" :key="i" class="flex items-center justify-between border-b border-gray-50 py-1.5 text-sm last:border-0">
					<span class="text-navy-700 dark:text-white">{{ o.grade || o.product || "Item" }} <span class="text-xs text-gray-400">{{ o.order_type }}</span></span>
					<span class="text-gray-500">{{ o.quantity_mt }} MT<span v-if="o.expected_value"> · ₹{{ fmt(o.expected_value) }}</span></span>
				</div>
			</div>

			<div v-if="competitors.length" class="aa-card">
				<p class="mb-2 text-sm font-semibold text-navy-600 dark:text-navy-200">Competitor info</p>
				<div v-for="(c, i) in competitors" :key="i" class="flex items-center justify-between border-b border-gray-50 py-1.5 text-sm last:border-0">
					<span class="text-navy-700 dark:text-white">{{ c.competitor_brand }}</span>
					<span class="text-gray-500">{{ c.price_per_mt ? "₹" + fmt(c.price_per_mt) + "/MT" : "" }} {{ c.stock_status }}</span>
				</div>
			</div>

			<button
				v-if="v.visit_status === 'In Progress'"
				@click="checkout"
				:disabled="busy"
				class="w-full rounded-2xl bg-saffron px-4 py-3.5 font-semibold text-white shadow-lg shadow-saffron/30 disabled:opacity-50"
			>
				Check out now
			</button>
		</div>

		<EmptyState v-else class="m-4" title="Visit not found" />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { ChevronLeft } from "lucide-vue-next"
import dayjs from "dayjs"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { getPosition, mapsLink } from "../utils/geo"
import { toast } from "../utils/toast"

const props = defineProps({ name: { type: String, required: true } })

const v = ref(null)
const photos = ref([])
const orders = ref([])
const competitors = ref([])
const loading = ref(true)
const busy = ref(false)

const STATUS_CLASS = {
	Planned: "bg-gray-100 text-gray-600",
	"In Progress": "bg-saffron/15 text-saffron",
	Completed: "bg-green-100 text-green-700",
	Cancelled: "bg-gray-100 text-gray-400",
	Missed: "bg-red-100 text-red-600",
}
const badge = computed(() => STATUS_CLASS[v.value?.visit_status] || "bg-gray-100 text-gray-600")
const inLink = computed(() => mapsLink(v.value?.check_in_latitude, v.value?.check_in_longitude))

function formatDate(d) { return d ? dayjs(d).format("DD MMM YYYY") : "" }
function formatTime(d) { return d ? dayjs(d).format("h:mm A") : "" }
function fmt(n) { return Number(n || 0).toLocaleString("en-IN") }

async function load() {
	loading.value = true
	try {
		const d = await call("crm_app.field_visit.get_visit", { name: props.name })
		v.value = d.visit
		photos.value = d.photos || []
		orders.value = d.order_items || []
		competitors.value = d.competitors || []
	} catch (e) {
		v.value = null
	} finally {
		loading.value = false
	}
}

async function checkout() {
	busy.value = true
	try {
		const pos = await getPosition()
		await call("crm_app.field_visit.check_out", { name: props.name, latitude: pos.latitude, longitude: pos.longitude })
		toast.success("Checked out")
		await load()
	} catch (e) {
		toast.error(e?.messages?.[0] || "Could not check out")
	} finally {
		busy.value = false
	}
}
onMounted(load)
</script>
