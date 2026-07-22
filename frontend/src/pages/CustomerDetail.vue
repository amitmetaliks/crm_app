<template>
	<div class="aa-workspace">
		<header class="aa-topbar">
			<button class="aa-back" @click="$router.back()"><ChevronLeft class="h-5 w-5" /></button>
			<div class="min-w-0 flex-1 px-1 text-center">
				<p class="aa-kicker">Customer 360</p>
				<h1 class="truncate text-base font-bold text-navy-800 dark:text-white">{{ c?.customer_name || name }}</h1>
			</div>
			<span class="aa-back text-xs font-bold">{{ initials }}</span>
		</header>

		<div v-if="loading" class="mx-auto max-w-xl p-4"><Skeleton :count="4" /></div>

		<div v-else-if="c" class="aa-content space-y-5 pt-3">
			<!-- Identity + risk flag -->
			<div class="aa-hero space-y-1 !p-5">
				<div class="flex items-start justify-between gap-2">
					<div class="min-w-0">
						<p class="aa-kicker !text-amber-200">Dealer account</p>
						<p class="mt-1 text-[1.45rem] font-bold leading-tight tracking-tight text-white">{{ c.customer_name }}</p>
						<p v-if="c.territory || c.customer_group" class="mt-1 text-sm text-white/60">
							{{ [c.territory, c.customer_group].filter(Boolean).join(" · ") }}
						</p>
						<p v-if="d.geo?.city" class="mt-0.5 text-xs text-white/50">{{ d.geo.city }}</p>
					</div>
					<span v-if="d.at_risk" class="shrink-0 rounded-full bg-red-50 px-2 py-1 text-xs font-semibold text-red-600">{{ $t("At risk") }}</span>
				</div>

				<!-- Quick actions -->
				<div class="mt-5 flex flex-wrap gap-2 border-t border-white/10 pt-4">
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
			<div class="aa-panel grid grid-cols-2 gap-0 overflow-hidden">
				<div class="border-r border-[#e7e5df] p-4 dark:border-navy-700">
					<p class="text-xs text-gray-400">{{ d.in_credit ? $t("In credit") : $t("Outstanding") }}</p>
					<p class="text-xl font-bold" :class="d.in_credit ? 'text-green-600' : d.outstanding > 0 ? 'text-red-600' : 'text-green-600'">
						{{ inrShort(d.in_credit ? Math.abs(d.balance) : d.outstanding) }}
					</p>
					<p v-if="d.overdue > 0" class="text-xs font-medium text-red-500">{{ inrShort(d.overdue) }} overdue</p>
					<!-- The balance is a SAP snapshot, not live. Say when, so nobody argues
					     with a dealer using a stale number. -->
					<p v-else-if="d.balance_as_of" class="text-xs text-gray-400">{{ $t("as of") }} {{ formatDate(d.balance_as_of) }}</p>
				</div>
				<div class="p-4">
					<p class="text-xs text-gray-400">{{ $t("Business done") }}</p>
					<p class="text-xl font-bold text-navy-700 dark:text-white">{{ inrShort(d.orders?.value) }}</p>
					<p class="text-xs text-gray-400">{{ d.orders?.count || 0 }} orders · {{ num(d.orders?.qty_mt) }} MT</p>
				</div>
			</div>

			<!-- Relationship pulse -->
			<div class="aa-panel grid grid-cols-3 gap-2 p-4 text-center">
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

			<router-link :to="nextBestAction.to" class="aa-panel flex items-center gap-3 p-4">
				<span class="aa-icon-surface"><CalendarClock class="h-5 w-5" /></span>
				<span class="min-w-0 flex-1">
					<span class="aa-kicker">Next best action</span>
					<span class="mt-1 block text-sm font-bold text-navy-800 dark:text-white">{{ nextBestAction.title }}</span>
					<span class="mt-0.5 block text-xs text-gray-400">{{ nextBestAction.detail }}</span>
				</span>
				<ChevronRight class="h-5 w-5 text-gray-300" />
			</router-link>

			<div class="grid grid-cols-3 gap-2">
				<router-link
					:to="{ name: 'NewVisit', query: { ptype: 'Customer', id: name, label: c.customer_name } }"
					class="aa-hero-action text-center"
				>{{ $t("Start visit") }}</router-link>
				<router-link
					:to="{ name: 'StockCheck', query: { customer: name, label: c.customer_name } }"
					class="aa-quiet-action !px-2 text-center"
				><Boxes class="h-4 w-4" /> {{ $t("Stock") }}</router-link>
				<router-link
					:to="{ name: 'Collect', query: { customer: name, label: c.customer_name, phone: c.mobile_no || '' } }"
					class="aa-quiet-action !border-green-200 !px-2 !text-green-700"
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

			<!-- Order ledger: which order is the money against -->
			<div v-if="d.order_ledger?.orders?.length">
				<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Order ledger") }}</h2>
				<div class="aa-card space-y-3">
					<div v-for="o in d.order_ledger.orders" :key="o.order_no" class="border-b border-gray-100 pb-2 last:border-0 last:pb-0 dark:border-navy-700">
						<div class="flex items-center justify-between text-sm">
							<span class="font-medium text-navy-700 dark:text-white">{{ o.order_no }}</span>
							<span
								class="shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold"
								:class="{
									'bg-green-50 text-green-700': o.status === 'paid',
									'bg-amber-50 text-amber-700': o.status === 'part',
									'bg-red-50 text-red-600': o.status === 'due',
									'bg-gray-100 text-gray-500': o.status === 'unknown',
								}"
							>{{ $t(statusLabel(o.status)) }}</span>
						</div>
						<p class="text-xs text-gray-400">
							{{ formatDate(o.ordered_on) }} · {{ inrShort(o.invoiced) }}
							<template v-if="o.paid > 0"> · {{ $t("paid") }} {{ inrShort(o.paid) }}</template>
						</p>
						<p v-if="o.balance > 0" class="text-xs font-semibold text-red-600">{{ inrShort(o.balance) }} {{ $t("due") }}</p>
					</div>
				</div>
				<!-- Never let a rep read 'unknown' as 'unpaid'. -->
				<p v-if="d.order_ledger.counts?.unknown" class="px-1 pt-1 text-xs leading-relaxed text-gray-400">
					{{ $t("Older orders show no payment because the payment feed starts") }}
					{{ formatDate(d.order_ledger.feed_start) }}. {{ $t("They are not necessarily unpaid.") }}
				</p>
			</div>

			<!-- Payments: what a rep needs when a dealer says "I already paid" -->
			<div v-if="d.payments?.length">
				<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Recent payments") }}</h2>
				<div class="aa-card space-y-2">
					<div v-for="p in d.payments" :key="p.document" class="flex items-center justify-between text-sm">
						<div class="min-w-0">
							<p class="truncate text-navy-700 dark:text-white">{{ formatDate(p.date) }}</p>
							<p class="text-xs text-gray-400">{{ p.document }}</p>
						</div>
						<span class="shrink-0 font-medium text-green-600">{{ inrShort(p.amount) }}</span>
					</div>
				</div>
			</div>

			<!-- Dispatch: "where is my truck" — the question asked at every counter -->
			<div v-if="d.dispatches?.length">
				<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Recent dispatches") }}</h2>
				<div class="aa-card space-y-3">
					<div v-for="dp in d.dispatches" :key="dp.invoice_number" class="border-b border-gray-100 pb-2 last:border-0 last:pb-0 dark:border-navy-700">
						<div class="flex items-center justify-between text-sm">
							<span class="font-medium text-navy-700 dark:text-white">{{ dp.invoice_number }}</span>
							<span class="text-gray-500">{{ inrShort(dp.amount) }} · {{ num(dp.qty) }} MT</span>
						</div>
						<p class="text-xs text-gray-400">
							{{ formatDate(dp.invoice_date) }}
							<template v-if="dp.truck_no"> · 🚚 {{ dp.truck_no }}</template>
							<template v-if="dp.lr_number"> · LR {{ dp.lr_number }}</template>
						</p>
						<p v-if="dp.transporter" class="truncate text-xs text-gray-400">{{ dp.transporter }}</p>
					</div>
				</div>
			</div>

			<!-- Recent orders -->
			<div v-if="d.recent_orders?.length && !d.dispatches?.length">
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
import { ChevronLeft, ChevronRight, Phone, MessageCircle, Navigation, MapPinOff, MapPin, IndianRupee, Boxes, CalendarClock } from "lucide-vue-next"
import dayjs from "dayjs"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { session } from "../data/session"
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
const initials = computed(() => (c.value?.customer_name || props.name || "?").split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase())
const nextBestAction = computed(() => {
	const visitTo = (purpose) => ({ name: "NewVisit", query: { ptype: "Customer", id: props.name, label: c.value?.customer_name || props.name, purpose } })
	if (Number(d.value.overdue || 0) > 0) return {
		title: `Collect ${inrShort(d.value.overdue)} overdue`,
		detail: "Resolve the oldest risk before discussing new credit.",
		to: { name: "Collect", query: { customer: props.name, label: c.value?.customer_name || props.name, phone: c.value?.mobile_no || "" } },
	}
	if (d.value.at_risk) return { title: "Re-engage this dealer", detail: "The account is going quiet. Capture the blocker and next commitment.", to: visitTo("Relationship") }
	if (Number(d.value.days_since_visit || 0) >= 14) return { title: "Schedule a follow-up visit", detail: `Last field visit was ${ago(d.value.days_since_visit)}.`, to: visitTo("Follow-up") }
	return { title: "Grow the next order", detail: "Account health is stable. Review stock and identify the next requirement.", to: visitTo("Order Booking") }
})

function formatDate(x) { return x ? dayjs(x).format("DD MMM YYYY") : "" }

// "unknown" reads as "No payment data", never as "unpaid": those orders predate the
// payment feed, so we cannot see their payments — most are settled.
const STATUS_LABEL = { paid: "Paid", part: "Part paid", due: "Due", unknown: "No payment data" }
function statusLabel(s) { return STATUS_LABEL[s] || s }
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
		// Manager flag is already loaded into the session at boot (refreshMe) — no need for a
		// per-dealer whoami round-trip on weak signal.
		isManager.value = !!session.isSalesManager
	} catch (e) {
		c.value = null
	} finally {
		loading.value = false
	}
})
</script>

<style scoped>
.chip {
	@apply inline-flex min-h-10 items-center gap-1.5 rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-xs font-semibold text-white;
}
.chip-primary {
	@apply border-saffron bg-saffron;
	color: #2d3952; /* navy on amber — 5.04:1; white would be 2.29:1 */
}
</style>
