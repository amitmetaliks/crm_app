<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="flex items-center gap-3 bg-navy-700 px-4 py-4 text-white">
			<button @click="$router.back()"><ChevronLeft class="h-6 w-6" /></button>
			<h1 class="truncate text-lg font-semibold">{{ c?.customer_name || name }}</h1>
		</header>

		<div v-if="loading" class="mx-auto max-w-xl p-4"><Skeleton :count="4" /></div>

		<div v-else-if="c" class="mx-auto max-w-xl space-y-4 p-4">
			<!-- Identity + risk flag -->
			<div class="aa-card space-y-1">
				<div class="flex items-start justify-between gap-2">
					<div class="min-w-0">
						<p class="text-lg font-bold text-navy-700 dark:text-white">{{ c.customer_name }}</p>
						<p v-if="c.territory || c.customer_group" class="text-sm text-gray-500">
							{{ [c.territory, c.customer_group].filter(Boolean).join(" · ") }}
						</p>
						<p v-if="d.geo?.city" class="text-xs text-gray-400">{{ d.geo.city }}</p>
					</div>
					<span v-if="d.at_risk" class="shrink-0 rounded-full bg-red-50 px-2 py-1 text-xs font-semibold text-red-600">{{ $t("At risk") }}</span>
				</div>

				<!-- Quick actions -->
				<div class="flex flex-wrap gap-2 pt-2">
					<a v-if="c.mobile_no" :href="`tel:${c.mobile_no}`" class="chip"><Phone class="h-3.5 w-3.5" /> {{ $t("Call") }}</a>
					<button v-if="c.mobile_no" class="chip" @click="wa"><MessageCircle class="h-3.5 w-3.5" /> {{ $t("WhatsApp") }}</button>
					<button v-if="d.geo" class="chip chip-primary" @click="navigate"><Navigation class="h-3.5 w-3.5" /> {{ $t("Navigate") }}</button>
					<button v-if="canPin" class="chip" :disabled="pinning" @click="pin">
						<MapPin class="h-3.5 w-3.5" /> {{ pinning ? "Getting GPS…" : d.geo ? "Re-pin shop" : "Pin this shop" }}
					</button>
					<span v-else-if="!d.geo" class="chip opacity-50"><MapPinOff class="h-3.5 w-3.5" /> {{ $t("No location") }}</span>
				</div>
				<p v-if="!d.geo" class="pt-1 text-xs text-gray-400"> {{ $t("No location on record. Stand at the shop and tap") }} <strong>{{ $t("Pin this shop") }}</strong> — it enables
					navigation and visit verification for everyone.
				</p>
			</div>

			<!-- The numbers that matter at the door -->
			<div class="grid grid-cols-2 gap-3">
				<div class="aa-card">
					<p class="text-xs text-gray-400">{{ $t("Outstanding") }}</p>
					<p class="text-xl font-bold" :class="d.outstanding > 0 ? 'text-red-600' : 'text-green-600'">{{ inrShort(d.outstanding) }}</p>
					<p v-if="d.overdue > 0" class="text-xs font-medium text-red-500">{{ inrShort(d.overdue) }} overdue</p>
				</div>
				<div class="aa-card">
					<p class="text-xs text-gray-400">{{ $t("Business done") }}</p>
					<p class="text-xl font-bold text-navy-700 dark:text-white">{{ inrShort(d.orders?.value) }}</p>
					<p class="text-xs text-gray-400">{{ d.orders?.count || 0 }} orders · {{ num(d.orders?.qty_mt) }} MT</p>
				</div>
			</div>

			<!-- Relationship pulse -->
			<div class="aa-card grid grid-cols-3 gap-2 text-center">
				<div>
					<p class="text-xs text-gray-400">{{ $t("Last visit") }}</p>
					<p class="text-sm font-semibold text-navy-700 dark:text-white">{{ ago(d.days_since_visit) }}</p>
				</div>
				<div>
					<p class="text-xs text-gray-400">{{ $t("Last order") }}</p>
					<p class="text-sm font-semibold" :class="d.at_risk ? 'text-red-600' : 'text-navy-700 dark:text-white'">{{ ago(d.days_since_order) }}</p>
				</div>
				<div>
					<p class="text-xs text-gray-400">{{ $t("Visits") }}</p>
					<p class="text-sm font-semibold text-navy-700 dark:text-white">{{ d.visit_count || 0 }}</p>
				</div>
			</div>

			<div class="flex gap-2">
				<router-link
					:to="{ name: 'NewVisit', query: { ptype: 'Customer', id: name, label: c.customer_name } }"
					class="aa-btn-primary flex-1 text-center"
				>{{ $t("Start visit") }}</router-link>
				<router-link
					:to="{ name: 'Collect', query: { customer: name, label: c.customer_name, phone: c.mobile_no || '' } }"
					class="flex flex-1 items-center justify-center gap-2 rounded-xl bg-green-600 py-2.5 text-center text-sm font-semibold text-white"
				><IndianRupee class="h-4 w-4" /> {{ $t("Collect") }}</router-link>
			</div>

			<!-- What he buys -->
			<div v-if="d.top_products?.length">
				<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Buys most") }}</h2>
				<div class="aa-card space-y-2">
					<div v-for="p in d.top_products" :key="p.item" class="flex items-center justify-between text-sm">
						<span class="min-w-0 truncate text-navy-700 dark:text-white">{{ p.item }}</span>
						<span class="shrink-0 text-gray-500">{{ num(p.qty) }} · {{ inrShort(p.amount) }}</span>
					</div>
				</div>
			</div>

			<!-- Recent orders -->
			<div v-if="d.recent_orders?.length">
				<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Recent orders") }}</h2>
				<div class="aa-card space-y-2">
					<div v-for="o in d.recent_orders" :key="o.name" class="flex items-center justify-between text-sm">
						<div class="min-w-0">
							<p class="truncate text-navy-700 dark:text-white">{{ o.name }}</p>
							<p class="text-xs text-gray-400">{{ formatDate(o.date) }}</p>
						</div>
						<span class="shrink-0 font-medium text-navy-700 dark:text-white">{{ inrShort(o.amount) }}</span>
					</div>
				</div>
			</div>

			<!-- Visit history -->
			<div>
				<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Visit history") }}</h2>
				<EmptyState v-if="!visits.length" :title='$t("No visits yet")' />
				<div v-else class="space-y-2">
					<router-link
						v-for="vi in visits"
						:key="vi.name"
						:to="{ name: 'VisitDetail', params: { name: vi.name } }"
						class="aa-card flex items-center justify-between"
					>
						<div>
							<p class="text-sm font-medium text-navy-700 dark:text-white">{{ vi.visit_purpose }}</p>
							<p class="text-xs text-gray-400">{{ formatDate(vi.visit_date) }} · {{ vi.sales_person_name }}</p>
						</div>
						<span class="text-xs text-gray-400">{{ vi.visit_status }}</span>
					</router-link>
				</div>
			</div>
		</div>

		<EmptyState v-else class="m-4" :title='$t("Customer not found")' />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { ChevronLeft, Phone, MessageCircle, Navigation, MapPinOff, MapPin, IndianRupee } from "lucide-vue-next"
import dayjs from "dayjs"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { openWhatsApp } from "../utils/wa"
import { getPosition } from "../utils/geo"
import { toast } from "../utils/toast"
import { inrShort, num } from "../utils/money"

const props = defineProps({ name: { type: String, required: true } })
const c = ref(null)
const d = ref({})
const visits = ref([])
const loading = ref(true)
const pinning = ref(false)
const isManager = ref(false)

// Reps may pin only shops we cannot locate yet; re-pinning moves the geofence, so it
// stays a manager action (see customers.pin_shop).
const canPin = computed(() => !d.value.geo || isManager.value)

function formatDate(x) { return x ? dayjs(x).format("DD MMM YYYY") : "" }
function ago(days) {
	if (days === null || days === undefined) return "Never"
	if (days === 0) return "Today"
	if (days === 1) return "Yesterday"
	if (days < 30) return `${days}d ago`
	if (days < 365) return `${Math.round(days / 30)}mo ago`
	return `${(days / 365).toFixed(1)}y ago`
}

function navigate() {
	// Hand off to whatever maps app the rep already uses — no API key, works offline-ish.
	const { lat, lng } = d.value.geo
	window.open(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving`, "_blank")
}
function wa() {
	openWhatsApp(c.value.mobile_no, `Dear ${c.value.customer_name},`)
}

async function pin() {
	pinning.value = true
	try {
		const pos = await getPosition()
		await call("crm_app.customers.pin_shop", {
			customer: props.name,
			latitude: pos.latitude,
			longitude: pos.longitude,
		})
		toast.success("Shop location saved")
		await load()
	} catch (err) {
		toast.error(err?.messages?.[0] || err?.message || "Could not save the location")
	} finally {
		pinning.value = false
	}
}

async function load() {
	const res = await call("crm_app.customers.get_customer_360", { name: props.name })
	d.value = res
	c.value = res.customer
	visits.value = res.visits || []
}

onMounted(async () => {
	try {
		await load()
		try {
			isManager.value = !!(await call("crm_app.api.whoami"))?.is_sales_manager
		} catch (e) {
			/* non-fatal: just hides the re-pin action */
		}
	} catch (e) {
		c.value = null
	} finally {
		loading.value = false
	}
})
</script>

<style scoped>
.chip {
	@apply inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-semibold text-navy-700 dark:border-navy-700 dark:bg-navy-800 dark:text-white;
}
.chip-primary {
	@apply border-saffron bg-saffron text-white dark:border-saffron dark:bg-saffron;
}
</style>
