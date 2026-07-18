<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="aa-page-header">
			<div class="flex items-center justify-between">
				<h1 class="text-xl font-bold">{{ $t("Business") }}</h1>
				<div class="flex gap-1 rounded-full bg-white/10 p-0.5">
					<button
						v-for="p in periods"
						:key="p.k"
						class="rounded-full px-3 py-1 text-xs font-semibold transition"
						:class="period === p.k ? 'bg-white text-navy-700' : 'text-white/80'"
						@click="period = p.k; load()"
					>{{ $t(p.label) }}</button>
				</div>
			</div>

			<!-- The headline: money, not activity -->
			<div v-if="!loading && d.sales?.available" class="mt-4">
				<p class="text-xs text-navy-200">{{ $t("Sales") }} · {{ periodLabel }}</p>
				<p class="text-3xl font-bold">{{ inrShort(d.sales.amount) }}</p>
				<p class="text-sm text-navy-200">
					{{ num(d.sales.qty_mt) }} MT · {{ d.sales.invoices }} {{ $t("invoices") }}
					<template v-if="d.target?.amount">
						· {{ d.target.amount_pct }}% {{ $t("of target") }}
					</template>
				</p>
				<div v-if="d.target?.amount" class="mt-2 h-2 overflow-hidden rounded-full bg-white/20">
					<div class="h-full rounded-full bg-saffron" :style="{ width: Math.min(d.target.amount_pct, 100) + '%' }" />
				</div>
			</div>
		</header>

		<div class="mx-auto max-w-xl space-y-4 p-4">
			<Skeleton v-if="loading" :count="5" />

			<EmptyState
				v-else-if="d.error"
				:title='$t("Managers only")'
				:subtitle='$t("This view is for sales managers.")'
			/>

			<template v-else>
				<!-- Feed health first: if a sync stalled, every number below is wrong low -->
				<div v-if="staleFeed" class="rounded-xl bg-amber-50 p-3 text-xs text-amber-900">
					<strong>{{ $t("Data may be behind.") }}</strong>
					{{ $t("Sales feed last updated") }} {{ fmtDate(d.feeds?.sales?.last_invoice_date) }}<template v-if="d.feeds?.payments?.last_posting_date">, {{ $t("payments") }} {{ fmtDate(d.feeds.payments.last_posting_date) }}</template>.
				</div>

				<!-- Money owed -->
				<div v-if="d.receivables?.available" class="aa-card">
					<div class="flex items-start justify-between">
						<div>
							<p class="aa-stat-label">{{ $t("Outstanding") }}</p>
							<p class="aa-stat text-red-600">{{ inrShort(d.receivables.total) }}</p>
							<p class="text-xs text-gray-400">{{ d.receivables.dealers }} {{ $t("dealers owe money") }}</p>
						</div>
						<router-link :to="{ name: 'Collections' }" class="aa-pill-btn !px-3 !py-1.5 !text-xs">{{ $t("Collect") }}</router-link>
					</div>
					<div v-if="d.receivables.top?.length" class="mt-3 space-y-1.5 border-t border-gray-100 pt-3 dark:border-navy-700">
						<router-link
							v-for="r in d.receivables.top.slice(0, 5)"
							:key="r.customer"
							:to="{ name: 'CustomerDetail', params: { name: r.customer } }"
							class="flex items-center justify-between text-sm"
						>
							<span class="min-w-0 truncate text-navy-700 dark:text-white">{{ r.customer_name }}</span>
							<span class="shrink-0 font-semibold text-red-600">{{ inrShort(r.outstanding) }}</span>
						</router-link>
					</div>
				</div>

				<!-- Rep leaderboard, on real invoicing -->
				<div v-if="d.leaderboard?.length">
					<h2 class="aa-section-title">{{ $t("Top reps") }} · {{ periodLabel }}</h2>
					<div class="aa-card space-y-2">
						<div v-for="(r, i) in d.leaderboard.slice(0, 8)" :key="r.employee" class="flex items-center gap-3">
							<span
								class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold"
								:class="i === 0 ? 'bg-saffron text-navy-700' : 'bg-gray-100 text-gray-500 dark:bg-navy-700 dark:text-white'"
							>{{ i + 1 }}</span>
							<span class="min-w-0 flex-1 truncate text-sm text-navy-700 dark:text-white">{{ r.employee_name }}</span>
							<span class="shrink-0 text-right">
								<span class="block text-sm font-semibold text-navy-700 dark:text-white">{{ inrShort(r.amount) }}</span>
								<span class="block text-[11px] text-gray-400">{{ num(r.qty_mt) }} MT</span>
							</span>
						</div>
					</div>
					<!-- Never let a leaderboard imply it covers everything. -->
					<p v-if="d.sales?.unattributed > 0" class="px-1 pt-1 text-xs leading-relaxed text-gray-400">
						{{ inrShort(d.sales.unattributed) }} {{ $t("invoiced under rep codes not linked to an employee, so it is not in this list.") }}
						({{ d.sales.attributed_pct }}% {{ $t("attributed") }})
					</p>
				</div>

				<!-- Field activity: secondary to the money, not the headline -->
				<div class="grid grid-cols-3 gap-3">
					<div class="aa-stat-tile">
						<p class="aa-stat-tile-value">{{ d.coverage?.visits || 0 }}</p>
						<p class="aa-stat-tile-label">{{ $t("Visits") }}</p>
					</div>
					<div class="aa-stat-tile">
						<p class="aa-stat-tile-value">{{ d.coverage?.dealers_visited || 0 }}</p>
						<p class="aa-stat-tile-label">{{ $t("Dealers covered") }}</p>
					</div>
					<div class="aa-stat-tile">
						<p class="aa-stat-tile-value">{{ d.coverage?.active_reps || 0 }}</p>
						<p class="aa-stat-tile-label">{{ $t("Active reps") }}</p>
					</div>
				</div>

				<!-- Shelf share -->
				<div v-if="d.shelf?.available" class="aa-card">
					<p class="aa-stat-label">{{ $t("Our shelf share") }}</p>
					<p class="aa-stat">{{ d.shelf.our_share_pct }}%</p>
					<p class="text-xs text-gray-400">
						{{ num(d.shelf.our_mt) }} MT {{ $t("ours") }} · {{ num(d.shelf.competitor_mt) }} MT {{ $t("competitor") }}
						· {{ d.shelf.checks }} {{ $t("checks") }}
					</p>
				</div>

				<!-- Dealers going quiet -->
				<div v-if="atRisk.length">
					<h2 class="aa-section-title">{{ $t("Dealers going quiet") }}</h2>
					<div class="aa-card space-y-2">
						<router-link
							v-for="r in atRisk.slice(0, 8)"
							:key="r.customer"
							:to="{ name: 'CustomerDetail', params: { name: r.customer } }"
							class="flex items-center justify-between text-sm"
						>
							<div class="min-w-0">
								<p class="truncate text-navy-700 dark:text-white">{{ r.customer_name }}</p>
								<p class="text-xs text-gray-400">{{ $t("last bought") }} {{ fmtDate(r.last_invoice) }}</p>
							</div>
							<div class="shrink-0 text-right">
								<span class="block text-xs font-semibold text-red-600">{{ r.days_quiet }}d</span>
								<span class="block text-[11px] text-gray-400">{{ inrShort(r.lifetime_value) }}</span>
							</div>
						</router-link>
					</div>
				</div>

				<!-- The manager's own queue -->
				<router-link v-if="d.pending_approvals" :to="{ name: 'Approvals' }" class="aa-card aa-card-button flex items-center justify-between">
					<span class="text-sm font-medium text-navy-700 dark:text-white">{{ $t("Pending approvals") }}</span>
					<span class="aa-pill aa-pill-amber">{{ d.pending_approvals }}</span>
				</router-link>

				<div class="grid grid-cols-2 gap-3">
					<router-link :to="{ name: 'Team' }" class="aa-card aa-card-button text-center text-sm font-medium text-navy-700 dark:text-white">{{ $t("Team activity") }}</router-link>
					<router-link :to="{ name: 'TeamMap' }" class="aa-card aa-card-button text-center text-sm font-medium text-navy-700 dark:text-white">{{ $t("Team live map") }}</router-link>
				</div>
			</template>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { inrShort, num } from "../utils/money"
import { t } from "../data/i18n"

const periods = [
	{ k: "mtd", label: "This month" },
	{ k: "30d", label: "30 days" },
	{ k: "90d", label: "90 days" },
]
const period = ref("mtd")
const d = ref({})
const atRisk = ref([])
const loading = ref(true)

const periodLabel = computed(() => t(periods.find((p) => p.k === period.value)?.label || ""))
// A stalled feed makes every number here read low; say so rather than let a manager
// conclude the month was bad.
const staleFeed = computed(() => d.value.feeds?.sales?.stale || d.value.feeds?.payments?.stale)

function fmtDate(x) { return x ? dayjs(x).format("DD MMM") : "—" }

async function load() {
	loading.value = true
	try {
		d.value = await call("crm_app.manager.get_manager_dashboard", { period: period.value })
		try {
			atRisk.value = await call("crm_app.manager.get_at_risk_dealers")
		} catch (e) {
			atRisk.value = []
		}
	} catch (e) {
		d.value = { error: true }
	} finally {
		loading.value = false
	}
}

onMounted(load)
</script>
