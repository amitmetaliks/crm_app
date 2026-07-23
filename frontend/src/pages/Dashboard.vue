<template>
	<div class="aa-workspace">
		<header class="aa-topbar">
			<div>
				<p class="aa-kicker">{{ dayLabel }}</p>
				<h1 class="mt-1 text-xl font-bold tracking-tight text-navy-800 dark:text-white">{{ greeting }}, {{ firstName }}</h1>
			</div>
			<div class="flex items-center gap-2">
				<div class="aa-logo-pill !px-2.5 !py-1"><img :src="wordmark" alt="TRIAM A+" class="h-5" /></div>
				<router-link :to="{ name: 'Notifications' }" class="aa-back relative" aria-label="Notifications">
					<Bell class="h-5 w-5" />
					<span class="absolute right-2.5 top-2.5 h-2 w-2 rounded-full border-2 border-white bg-saffron" />
				</router-link>
			</div>
		</header>

		<main class="aa-content space-y-6 pt-2">
			<p v-if="session.gateLoaded && !session.hasEmployee" class="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
				Your login is not linked to an Employee record. Ask your administrator to link it before recording field activity.
			</p>

			<section class="aa-hero">
				<div class="relative z-10">
					<div class="flex items-center justify-between">
						<span class="inline-flex items-center gap-2 text-xs font-semibold text-white/70">
							<span class="h-2 w-2 rounded-full" :class="home.attendance?.checked_in ? 'bg-green-400' : 'bg-white/40'" />
							{{ home.attendance?.checked_in ? "On duty" : "Not checked in" }}
						</span>
						<span class="text-xs font-medium text-white/60">Beat {{ home.beat?.visited || 0 }}/{{ home.beat?.planned || 0 }}</span>
					</div>
					<h2 class="mt-5 max-w-[17rem] text-[1.7rem] font-bold leading-[1.08] tracking-[-0.04em]">Make the next visit count.</h2>
					<p class="mt-2 max-w-[18rem] text-sm leading-5 text-white/65">Capture the conversation, order and next action while you are still at the counter.</p>
					<div class="mt-5 flex gap-2">
						<router-link :to="{ name: 'NewVisit' }" class="aa-hero-action flex-1"><MapPin class="h-4 w-4" /> Start visit</router-link>
						<router-link :to="{ name: 'Route' }" class="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-white/15 px-4 text-sm font-semibold text-white"><Navigation class="h-4 w-4" /> Route</router-link>
					</div>
					<router-link :to="{ name: 'Attendance' }" class="mt-5 flex items-center justify-between border-t border-white/10 pt-4">
						<span class="flex items-center gap-2 text-sm text-white/80"><CalendarCheck class="h-4 w-4" /> In {{ fmtTime(home.attendance?.first_in) || "--:--" }}</span>
						<span class="text-xs font-semibold text-amber-200">{{ home.attendance?.checked_in ? "Manage duty" : "Check in" }} →</span>
					</router-link>
				</div>
			</section>

			<section v-if="priorities.length">
				<div class="aa-section-head">
					<div><p class="aa-kicker">Needs you</p><h2 class="aa-section-heading mt-0.5">Today's priorities</h2></div>
				</div>
				<div class="aa-panel overflow-hidden">
					<router-link v-for="(p, i) in priorities" :key="i" :to="p.route" class="aa-data-row">
						<span class="aa-icon-surface"><component :is="prioIcon(p.type)" class="h-5 w-5" /></span>
						<span class="min-w-0 flex-1">
							<span class="block truncate text-sm font-semibold text-navy-800 dark:text-white">{{ p.title }}</span>
							<span class="block truncate text-xs text-gray-400">{{ p.reason }}</span>
						</span>
						<span class="aa-pill shrink-0" :class="p.severity === 'high' ? 'aa-pill-red' : 'aa-pill-amber'">{{ p.cta }}</span>
						<ChevronRight class="h-4 w-4 shrink-0 text-gray-300" />
					</router-link>
				</div>
			</section>
			<router-link v-else-if="prioLoaded" :to="{ name: 'Beat' }" class="aa-panel flex items-center gap-3 p-4">
				<span class="aa-icon-surface !bg-green-50 !text-green-600"><CheckCircle2 class="h-5 w-5" /></span>
				<span class="min-w-0 flex-1"><span class="block text-sm font-semibold text-navy-800 dark:text-white">You're on top of things</span><span class="block text-xs text-gray-400">No overdue collections or follow-ups right now</span></span>
				<ChevronRight class="h-4 w-4 text-gray-300" />
			</router-link>

			<section>
				<div class="aa-section-head">
					<div><p class="aa-kicker">Today</p><h2 class="aa-section-heading mt-0.5">Field progress</h2></div>
					<router-link :to="{ name: 'Beat' }" class="aa-section-link">Open beat →</router-link>
				</div>
				<div class="aa-panel overflow-hidden">
					<div class="grid grid-cols-4 divide-x divide-[#e7e5df] p-4 dark:divide-navy-700">
						<div class="text-center"><p class="aa-metric-number">{{ v.total || 0 }}</p><p class="aa-metric-caption">Visits</p></div>
						<div class="text-center"><p class="aa-metric-number text-green-600">{{ v.productive || 0 }}</p><p class="aa-metric-caption">Productive</p></div>
						<div class="text-center"><p class="aa-metric-number">{{ v.zero_order || 0 }}</p><p class="aa-metric-caption">No order</p></div>
						<div class="text-center"><p class="aa-metric-number">{{ v.strike_rate || 0 }}%</p><p class="aa-metric-caption">Strike</p></div>
					</div>
					<div class="border-t border-[#e7e5df] px-4 py-3 dark:border-navy-700">
						<div class="flex justify-between text-xs font-medium text-gray-500"><span>Beat completion</span><span>{{ beatPct }}%</span></div>
						<div class="mt-2 h-1.5 overflow-hidden rounded-full bg-gray-100 dark:bg-navy-700"><div class="h-full rounded-full bg-saffron" :style="{ width: beatPct + '%' }" /></div>
					</div>
				</div>
			</section>

			<section>
				<div class="aa-section-head"><h2 class="aa-section-heading">Business pulse</h2><router-link :to="{ name: 'Analytics' }" class="aa-section-link">View insights</router-link></div>
				<div class="aa-panel grid grid-cols-2 overflow-hidden">
					<div class="border-b border-r border-[#e7e5df] p-4 dark:border-navy-700"><p class="aa-metric-number">{{ inrShort(o.value) }}</p><p class="aa-metric-caption">Order value today</p></div>
					<div class="border-b border-[#e7e5df] p-4 dark:border-navy-700"><p class="aa-metric-number">{{ o.orders || 0 }}</p><p class="aa-metric-caption">Orders booked</p></div>
					<div class="border-r border-[#e7e5df] p-4 dark:border-navy-700"><p class="aa-metric-number">{{ fmt(o.qty) }}</p><p class="aa-metric-caption">Metric tonnes</p></div>
					<div class="p-4"><p class="aa-metric-number">{{ home.new_retailers || 0 }}</p><p class="aa-metric-caption">New retailers</p></div>
				</div>
			</section>

			<router-link :to="{ name: 'Targets' }" class="aa-panel block p-4">
				<div class="flex items-start justify-between gap-4">
					<div><p class="aa-kicker">Monthly target</p><p class="mt-1 text-lg font-bold text-navy-800 dark:text-white">{{ inrShort(home.sales_target?.achieved) }}</p><p class="text-xs text-gray-400">of {{ inrShort(home.sales_target?.target) }}</p></div>
					<div class="flex h-14 w-14 items-center justify-center rounded-full bg-saffron/15 text-sm font-bold text-saffron">{{ home.sales_target?.pct || 0 }}%</div>
				</div>
				<div class="mt-3 h-2 overflow-hidden rounded-full bg-gray-100 dark:bg-navy-700"><div class="h-full rounded-full bg-saffron" :style="{ width: Math.min(100, home.sales_target?.pct || 0) + '%' }" /></div>
			</router-link>

			<section>
				<div class="aa-section-head"><h2 class="aa-section-heading">Keep moving</h2><span class="text-xs text-gray-400">Frequent actions</span></div>
				<div class="aa-panel overflow-hidden">
					<router-link :to="{ name: 'Collections' }" class="aa-data-row"><span class="aa-icon-surface"><IndianRupee class="h-5 w-5" /></span><span class="min-w-0 flex-1"><span class="block text-sm font-semibold text-navy-800 dark:text-white">Record a collection</span><span class="block text-xs text-gray-400">Receipts and outstanding balances</span></span><ChevronRight class="h-4 w-4 text-gray-300" /></router-link>
					<router-link :to="{ name: 'Expense' }" class="aa-data-row"><span class="aa-icon-surface"><ReceiptText class="h-5 w-5" /></span><span class="min-w-0 flex-1"><span class="block text-sm font-semibold text-navy-800 dark:text-white">Add an expense</span><span class="block text-xs text-gray-400">Today {{ inrShort(home.expense?.today) }} · month {{ inrShort(home.expense?.month) }}</span></span><ChevronRight class="h-4 w-4 text-gray-300" /></router-link>
					<router-link :to="{ name: 'Customers' }" class="aa-data-row"><span class="aa-icon-surface"><Store class="h-5 w-5" /></span><span class="min-w-0 flex-1"><span class="block text-sm font-semibold text-navy-800 dark:text-white">Find a dealer</span><span class="block text-xs text-gray-400">Customer history, credit and actions</span></span><ChevronRight class="h-4 w-4 text-gray-300" /></router-link>
				</div>
			</section>
		</main>

		<BottomNav />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { Bell, MapPin, CalendarCheck, CalendarClock, CheckCircle2, IndianRupee, Store, Navigation, ReceiptText, ChevronRight } from "lucide-vue-next"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import { session } from "../data/session"
import { callCached } from "../data/cache"
import { inrShort } from "../utils/money"
import wordmark from "../assets/logo-wordmark.png"

const home = ref({})
const priorities = ref([])
const prioLoaded = ref(false)
const v = computed(() => home.value.visits || {})
const o = computed(() => home.value.order_summary || {})
const firstName = computed(() => (home.value.employee_name || session.employeeName || "Field Sales").split(" ")[0])
const dayLabel = computed(() => dayjs().format("dddd · D MMM"))
const beatPct = computed(() => {
	const planned = Number(home.value.beat?.planned || 0)
	return planned ? Math.min(100, Math.round((Number(home.value.beat?.visited || 0) / planned) * 100)) : 0
})
const greeting = computed(() => {
	const h = new Date().getHours()
	return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening"
})

function fmtTime(t) { return t ? dayjs(t).format("h:mm A") : "" }
function fmt(n) { return Number(n || 0).toLocaleString("en-IN") }

const PRIO_ICONS = { collection: IndianRupee, followup: CalendarClock, beat: MapPin }
function prioIcon(type) { return PRIO_ICONS[type] || MapPin }

onMounted(async () => {
	try { home.value = await callCached("crm_app.sfa.get_home_summary") } catch (e) { /* last-known state remains visible */ }
	try {
		const res = await callCached("crm_app.priorities.get_priorities")
		priorities.value = (res && res.items) || []
	} catch (e) {
		/* offline with nothing cached — leave the section hidden */
	} finally {
		prioLoaded.value = true
	}
})
</script>
