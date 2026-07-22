<template>
	<div class="aa-workspace">
		<header class="aa-topbar !items-end">
			<div><p class="aa-kicker">Manager workspace</p><h1 class="aa-display mt-1">Business control</h1><p class="aa-subtitle">Exceptions first. Performance second.</p></div>
			<router-link :to="{ name: 'TeamMap' }" class="aa-back" aria-label="Team map"><MapPinned class="h-5 w-5" /></router-link>
		</header>

		<main class="aa-content space-y-6 pt-3">
			<div class="flex gap-2 overflow-x-auto pb-1">
				<button v-for="p in periods" :key="p.k" class="min-h-10 shrink-0 rounded-full border px-4 text-xs font-semibold" :class="period === p.k ? 'border-navy-700 bg-navy-700 text-white' : 'border-[#e7e5df] bg-white text-gray-500 dark:border-navy-700 dark:bg-navy-800'" @click="period = p.k; load()">{{ $t(p.label) }}</button>
			</div>

			<Skeleton v-if="loading" :count="5" />
			<EmptyState v-else-if="d.error" :title='$t("Managers only")' :subtitle='$t("This view is for sales managers.")' />

			<template v-else>
				<section v-if="d.sales?.available" class="aa-hero">
					<div class="flex items-start justify-between gap-4"><div><p class="text-xs font-semibold uppercase tracking-[0.14em] text-amber-200">Sales · {{ periodLabel }}</p><p class="mt-2 text-3xl font-bold tracking-tight">{{ inrShort(d.sales.amount) }}</p><p class="mt-1 text-sm text-white/60">{{ num(d.sales.qty_mt) }} MT · {{ d.sales.invoices }} invoices</p></div><TrendingUp class="h-7 w-7 text-amber-200" /></div>
					<div v-if="d.target?.amount" class="mt-5"><div class="flex justify-between text-xs text-white/60"><span>Target progress</span><span>{{ d.target.amount_pct }}%</span></div><div class="mt-2 h-2 overflow-hidden rounded-full bg-white/15"><div class="h-full rounded-full bg-saffron" :style="{ width: Math.min(d.target.amount_pct, 100) + '%' }" /></div></div>
				</section>

				<section v-if="attentionCount">
					<div class="aa-section-head"><div><p class="aa-kicker">Act now</p><h2 class="aa-section-heading mt-0.5">Needs attention</h2></div><span class="aa-pill aa-pill-red">{{ attentionCount }}</span></div>
					<div class="aa-panel overflow-hidden">
						<div v-if="staleFeed" class="aa-data-row bg-amber-50/60 dark:bg-amber-900/10"><span class="aa-icon-surface"><DatabaseZap class="h-5 w-5" /></span><span class="min-w-0 flex-1"><span class="block text-sm font-semibold text-amber-900 dark:text-amber-200">Data feed may be behind</span><span class="block text-xs text-amber-700 dark:text-amber-300">Sales {{ fmtDate(d.feeds?.sales?.last_invoice_date) }} · payments {{ fmtDate(d.feeds?.payments?.last_posting_date) }}</span></span></div>
						<router-link v-if="d.pending_approvals" :to="{ name: 'Approvals' }" class="aa-data-row"><span class="aa-icon-surface"><ClipboardCheck class="h-5 w-5" /></span><span class="min-w-0 flex-1"><span class="block text-sm font-semibold text-navy-800 dark:text-white">{{ d.pending_approvals }} approvals waiting</span><span class="block text-xs text-gray-400">Clear the team’s blocked requests</span></span><ChevronRight class="h-4 w-4 text-gray-300" /></router-link>
						<router-link v-for="r in topReceivables" :key="'due-' + r.customer" :to="{ name: 'CustomerDetail', params: { name: r.customer } }" class="aa-data-row"><span class="aa-icon-surface"><IndianRupee class="h-5 w-5" /></span><span class="min-w-0 flex-1"><span class="block truncate text-sm font-semibold text-navy-800 dark:text-white">{{ r.customer_name }}</span><span class="block text-xs text-gray-400">Priority collection</span></span><span class="text-sm font-bold text-red-600">{{ inrShort(r.outstanding) }}</span><ChevronRight class="h-4 w-4 text-gray-300" /></router-link>
						<router-link v-for="r in topAtRisk" :key="'risk-' + r.customer" :to="{ name: 'CustomerDetail', params: { name: r.customer } }" class="aa-data-row"><span class="aa-icon-surface"><UserRoundX class="h-5 w-5" /></span><span class="min-w-0 flex-1"><span class="block truncate text-sm font-semibold text-navy-800 dark:text-white">{{ r.customer_name }}</span><span class="block text-xs text-gray-400">No purchase since {{ fmtDate(r.last_invoice) }}</span></span><span class="aa-pill aa-pill-red">{{ r.days_quiet }}d</span><ChevronRight class="h-4 w-4 text-gray-300" /></router-link>
					</div>
				</section>

				<section>
					<div class="aa-section-head"><h2 class="aa-section-heading">Field pulse</h2><router-link :to="{ name: 'Team' }" class="aa-section-link">Team detail →</router-link></div>
					<div class="aa-panel grid grid-cols-3 divide-x divide-[#e7e5df] p-4 dark:divide-navy-700"><div class="text-center"><p class="aa-metric-number">{{ d.coverage?.visits || 0 }}</p><p class="aa-metric-caption">Visits</p></div><div class="text-center"><p class="aa-metric-number">{{ d.coverage?.dealers_visited || 0 }}</p><p class="aa-metric-caption">Covered</p></div><div class="text-center"><p class="aa-metric-number">{{ d.coverage?.active_reps || 0 }}</p><p class="aa-metric-caption">Active reps</p></div></div>
				</section>

				<section v-if="d.leaderboard?.length">
					<div class="aa-section-head"><h2 class="aa-section-heading">Rep performance</h2><span class="text-xs text-gray-400">{{ periodLabel }}</span></div>
					<div class="aa-panel overflow-hidden"><div v-for="(r, i) in d.leaderboard.slice(0, 8)" :key="r.employee" class="aa-data-row"><span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-xs font-bold" :class="i === 0 ? 'bg-saffron text-navy-800' : 'bg-gray-100 text-gray-500 dark:bg-navy-700'">{{ i + 1 }}</span><span class="min-w-0 flex-1 truncate text-sm font-semibold text-navy-800 dark:text-white">{{ r.employee_name }}</span><span class="text-right"><span class="block text-sm font-bold text-navy-800 dark:text-white">{{ inrShort(r.amount) }}</span><span class="block text-xs text-gray-400">{{ num(r.qty_mt) }} MT</span></span></div></div>
					<p v-if="d.sales?.unattributed > 0" class="mt-2 px-1 text-xs leading-5 text-gray-400">{{ inrShort(d.sales.unattributed) }} is not attributed to a linked employee ({{ d.sales.attributed_pct }}% attributed).</p>
				</section>

				<section class="grid grid-cols-2 gap-3">
					<div v-if="d.receivables?.available" class="aa-panel p-4"><p class="aa-kicker">Receivables</p><p class="mt-2 text-xl font-bold text-red-600">{{ inrShort(d.receivables.total) }}</p><p class="mt-1 text-xs text-gray-400">{{ d.receivables.dealers }} dealers owe money</p></div>
					<div v-if="d.shelf?.available" class="aa-panel p-4"><p class="aa-kicker">Shelf share</p><p class="mt-2 text-xl font-bold text-navy-800 dark:text-white">{{ d.shelf.our_share_pct }}%</p><p class="mt-1 text-xs text-gray-400">{{ d.shelf.checks }} stock checks</p></div>
				</section>
			</template>
		</main>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import dayjs from "dayjs"
import { MapPinned, TrendingUp, DatabaseZap, ClipboardCheck, IndianRupee, UserRoundX, ChevronRight } from "lucide-vue-next"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { inrShort, num } from "../utils/money"
import { t } from "../data/i18n"

const periods = [{ k: "mtd", label: "This month" }, { k: "30d", label: "30 days" }, { k: "90d", label: "90 days" }]
const period = ref("mtd")
const d = ref({})
const atRisk = ref([])
const loading = ref(true)
const periodLabel = computed(() => t(periods.find((p) => p.k === period.value)?.label || ""))
const staleFeed = computed(() => d.value.feeds?.sales?.stale || d.value.feeds?.payments?.stale)
const topReceivables = computed(() => (d.value.receivables?.top || []).slice(0, 3))
const topAtRisk = computed(() => atRisk.value.slice(0, 3))
const attentionCount = computed(() => Number(!!staleFeed.value) + Number(d.value.pending_approvals || 0) + topReceivables.value.length + topAtRisk.value.length)

function fmtDate(value) { return value ? dayjs(value).format("DD MMM") : "Not available" }
async function load() {
	loading.value = true
	try {
		d.value = await call("crm_app.manager.get_manager_dashboard", { period: period.value })
		try { atRisk.value = await call("crm_app.manager.get_at_risk_dealers") || [] } catch (e) { atRisk.value = [] }
	} catch (e) { d.value = { error: true } }
	finally { loading.value = false }
}
onMounted(load)
</script>
